from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, Response

from src.compliance_assistant.validate import validate_text
from src.compliance_assistant.validate import _load_rules as _load_rules_cfg  # type: ignore
import os
from src.compliance_assistant.parsers.factory import ParserFactory
from src.compliance_assistant.kb import load_guidelines
from src.compliance_assistant.sectionizer import split_into_sections
from src.frontend import get_frontend_html

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024  # 128 MB

# Paths of guideline files used for KB (defaults). Users can upload new ones at /guidelines
GUIDELINE_DIR = Path("kb_uploads")
GUIDELINE_DIR.mkdir(exist_ok=True)
GUIDELINE_PATHS = [
	str(Path("21.txt")),
	str(Path("general.txt")),
]

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parser-app")


@app.get("/health")
def health():
	return {"status": "ok"}


@app.get("/")
def index() -> Response:
	"""Serve the main frontend interface."""
	return Response(get_frontend_html(), mimetype="text/html")


@app.get("/llm_status")
def llm_status():
	try:
		rules = _load_rules_cfg(None)
		llm = rules.get("llm", {}) if isinstance(rules, dict) else {}
		enabled = bool(llm.get("enabled", False))
		provider = (llm.get("provider") or "").lower()
		if provider == "azure":
			env_ok = bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))
			details = {
				"deployment": llm.get("deployment"),
				"api_version": llm.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION"),
			}
		else:
			env_ok = bool(os.getenv("OPENAI_API_KEY"))
			details = {
				"model": llm.get("model") or os.getenv("OPENAI_MODEL"),
			}
		return jsonify({
			"enabled": enabled,
			"provider": provider or ("azure" if os.getenv("AZURE_OPENAI_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else "")),
			"env_ok": env_ok,
			"active": enabled and env_ok,
			"details": details,
		})
	except Exception as e:
		logger.exception("Error checking LLM status")
		return jsonify({"error": str(e)}), 500


@app.get("/guidelines")
def get_guidelines():
	# Return list of current guideline files
	return jsonify({"files": GUIDELINE_PATHS})


@app.post("/guidelines")
def post_guidelines():
	# Accept multiple .txt files and add to KB list
	files = request.files.getlist("files")
	added: list[str] = []
	for f in files:
		name = (f.filename or "guideline.txt").strip()
		if not name:
			continue
		path = GUIDELINE_DIR / Path(name).name
		data = f.read()
		if not data:
			continue
		path.write_bytes(data)
		GUIDELINE_PATHS.append(str(path))
	return jsonify({"ok": True, "files": GUIDELINE_PATHS})


@app.post("/parse")
def parse_upload():
	try:
		if "file" not in request.files:
			return jsonify({"error": "No file provided"}), 400
		file = request.files["file"]
		filename = (file.filename or "uploaded").strip()
		data = file.read()
		if not data:
			return jsonify({"error": "Empty file"}), 400
		ext = Path(filename).suffix.lower() or ".txt"
		logger.info("Received file '%s' (%d bytes) ext=%s", filename, len(data), ext)
		with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
			tmp.write(data)
			tmp_path = Path(tmp.name)
		logger.info("Saved temp file at %s", tmp_path)
		parser = ParserFactory.for_file(tmp_path)
		parsed = parser.parse(tmp_path)
		logger.info("Parsed using %s, length=%d", parsed.meta.get("parser"), len(parsed.text))
		sections = split_into_sections(parsed.text)
		if request.headers.get("X-Requested-With") == "fetch" or request.accept_mimetypes.best != "text/html":
			return jsonify({"meta": parsed.meta, "text": parsed.text, "sections": sections})
		# HTML fallback remains same but now with section blocks
		blocks = "\n".join(
			f"<div class='section'><h4>{s['heading']}</h4><div>{s['body'].replace('\n','<br/>')}</div></div>" for s in sections
		)
		result_html = f"""
		<!doctype html>
		<html><head><meta charset=\"utf-8\" /><title>Parsed result</title>
		<style>
		.section {{ border:1px solid #e5e5e5; padding:8px; margin:8px 0; }}
		.section h4 {{ margin:0 0 6px 0; }}
		</style>
		</head>
		<body style=\"font-family: Arial, sans-serif; margin: 24px;\">
		<h3>Meta</h3>
		<pre>{parsed.meta}</pre>
		<h3>Sections</h3>
		{blocks}
		<p><a href=\"/\">Back</a></p>
		</body></n		</html>
		"""
		return Response(result_html, mimetype="text/html")
	except Exception as e:
		logger.exception("Error while parsing upload")
		return jsonify({"error": str(e)}), 500
	finally:
		try:
			if 'tmp_path' in locals():
				logger.info("Cleaning up temp file %s", tmp_path)
				tmp_path.unlink(missing_ok=True)
		except Exception:
			pass


@app.post("/validate")
def validate_upload():
	# JSON API for programmatic clients (kept for completeness)
	try:
		if "file" not in request.files:
			return jsonify({"error": "No file provided"}), 400
		file = request.files["file"]
		data = file.read()
		if not data:
			return jsonify({"error": "Empty file"}), 400
		with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or 'file').suffix or '.txt') as tmp:
			tmp.write(data)
			tmp_path = Path(tmp.name)
		parser = ParserFactory.for_file(tmp_path)
		parsed = parser.parse(tmp_path)
		kb = load_guidelines([p for p in GUIDELINE_PATHS if Path(p).exists()])
		result = validate_text(parsed.text, meta=parsed.meta, kb=kb)
		return jsonify({"score": result.score, "findings": [f.__dict__ for f in result.findings], "meta": result.meta})
	except Exception as e:
		logger.exception("Error while validating upload (JSON endpoint)")
		return jsonify({"error": str(e)}), 500
	finally:
		try:
			if 'tmp_path' in locals():
				tmp_path.unlink(missing_ok=True)
		except Exception:
			pass


@app.post("/validate_html")
def validate_upload_html():
	# Always returns a human-friendly HTML page
	try:
		if "file" not in request.files:
			return Response("<p>No file provided</p>", mimetype="text/html", status=400)
		file = request.files["file"]
		filename = (file.filename or "uploaded").strip()
		data = file.read()
		if not data:
			return Response("<p>Empty file</p>", mimetype="text/html", status=400)
		ext = Path(filename).suffix.lower() or ".txt"
		with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
			tmp.write(data)
			tmp_path = Path(tmp.name)
		parser = ParserFactory.for_file(tmp_path)
		parsed = parser.parse(tmp_path)
		kb = load_guidelines([p for p in GUIDELINE_PATHS if Path(p).exists()])
		result = validate_text(parsed.text, meta=parsed.meta, kb=kb)

		rows = []
		for f in result.findings:
			sev = f.severity.upper()
			msg = f.message
			ctx = f.location or ""
			sec = f.section or "—"
			cit_full = (f.citation or "").replace("<", "&lt;").replace(">", "&gt;")
			cit_short = cit_full[:160] + ("..." if len(cit_full) > 160 else "")
			if f.id == "missing_section":
				sugg = "Add the missing section and define ownership, storage, retention, and signatures."
			elif f.id == "stale_reference":
				sugg = "Review/update dates; add 'last reviewed' if the standard edition is still current."
			elif f.id == "placeholder":
				sugg = "Replace placeholders (TBD/XXX) with final values."
			elif f.id == "steps_numbering":
				sugg = "Use numbered steps under the Procedure section."
			else:
				sugg = "Review and remediate."
			row = (
				f"<tr>"
				f"<td>{sev}</td>"
				f"<td>{msg}<div style='color:#666;font-size:12px;margin-top:4px'>{sugg}</div></td>"
				f"<td>{sec}</td>"
				f"<td>{ctx}</td>"
				f"<td style='max-width:520px;white-space:pre-wrap'>"
				f"{cit_short}"
				f"<details><summary style='cursor:pointer;color:#0366d6;margin-top:4px'>Show full</summary>"
				f"<pre style='white-space:pre-wrap'>{cit_full}</pre>"
				f"</details>"
				f"</td>"
				f"</tr>"
			)
			rows.append(row)
		rows_html = "\n".join(rows) or "<tr><td colspan='6'>No findings</td></tr>"
		html = f"""
		<!doctype html>
		<html><head><meta charset=\"utf-8\" /><title>Validation result</title>
		<style>
		body {{ font-family: Arial, sans-serif; margin: 24px; }}
		table {{ border-collapse: collapse; width: 100%; }}
		th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }}
		th {{ background: #f7f7f7; }}
		</style></head>
		<body>
		<h2>Compliance score: {result.score}</h2>
		<table>
			<thead><tr><th>Severity</th><th>Finding</th><th>Section</th><th>Context</th><th>Guideline citation</th></tr></thead>
			<tbody>
			{rows_html}
			</tbody>
		</table>
		<p style=\"margin-top:16px;\"><a href=\"/\">Back</a></p>
		</body></n		</html>
		"""
		return Response(html, mimetype="text/html")
	except Exception as e:
		logger.exception("Error while validating upload (HTML endpoint)")
		return Response(f"<pre>{str(e)}</pre>", mimetype="text/html", status=500)
	finally:
		try:
			if 'tmp_path' in locals():
				tmp_path.unlink(missing_ok=True)
		except Exception:
			pass


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8000, debug=True)
