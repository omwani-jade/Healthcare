from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, Response

from src.compliance_assistant.parsers.factory import ParserFactory
from src.compliance_assistant.validate import validate_text
from src.compliance_assistant.kb import load_guidelines
from src.compliance_assistant.sectionizer import split_into_sections

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
	html = (
		"""
		<!doctype html>
		<html>
		<head>
			<meta charset=\"utf-8\" />
			<title>Compliance Assistant - Parser</title>
			<style>
				body { font-family: Arial, sans-serif; margin: 32px; }
				#out { white-space: pre-wrap; border: 1px solid #ccc; padding: 12px; margin-top: 12px; max-height: 50vh; overflow: auto; }
				label { display: block; margin-bottom: 8px; }
				button { padding: 8px 12px; margin-right: 8px; }
				#meta { margin-top: 12px; }
				#error { color: #b00020; margin-top: 12px; }
				#fileinfo { margin: 6px 0 4px; color: #333; }
				#reason { font-size: 12px; color: #b00020; margin-bottom: 12px; }
				#kb { margin-top: 24px; padding: 10px; border: 1px dashed #aaa; }
				.section { border:1px solid #e5e5e5; padding:8px; margin:8px 0; }
				.section h4 { margin:0 0 6px 0; }
			</style>
		</head>
		<body>
			<h2>Upload a document (.txt, .docx, .pdf)</h2>
			<form id=\"f\" method=\"post\" action=\"/parse\" enctype=\"multipart/form-data\">
				<label>Choose file: <input id=\"file\" type=\"file\" name=\"file\" accept=\".txt,.docx,.pdf\" required /></label>
				<div id=\"fileinfo\">No file chosen</div>
				<div id=\"reason\"></div>
				<button id=\"parseBtn\" type=\"submit\">Parse</button>
				<button id=\"validateBtn\" type=\"submit\" formaction=\"/validate_html\" formmethod=\"post\">Validate</button>
			</form>
			<div id=\"kb\">
				<strong>Guidelines KB</strong> — current files: <span id=\"kbList\"></span>
				<form id=\"kbForm\" method=\"post\" action=\"/guidelines\" enctype=\"multipart/form-data\" style=\"margin-top:8px\;\">
					<input type=\"file\" name=\"files\" multiple accept=\".txt\" />
					<button type=\"submit\">Upload guidelines (.txt)</button>
				</form>
			</div>
			<div id=\"meta\"></div>
			<div id=\"error\"></div>
			<h3>Text preview</h3>
			<div id=\"out\"></div>
			<script>
			window.addEventListener('DOMContentLoaded', () => {
				const form = document.getElementById('f');
				const out = document.getElementById('out');
				const meta = document.getElementById('meta');
				const errEl = document.getElementById('error');
				const fileInput = document.getElementById('file');
				const fileInfo = document.getElementById('fileinfo');
				const reason = document.getElementById('reason');
				const MAX_MB = 128; // match server limit

				fetch('/guidelines').then(r => r.json()).then(j => {
					document.getElementById('kbList').textContent = j.files.join(', ');
				}).catch(() => {});

				function updateInfo() {
					const f = fileInput.files && fileInput.files[0];
					if (!f) { fileInfo.textContent = 'No file chosen'; reason.textContent = ''; return; }
					const sizeKB = Math.round(f.size / 1024);
					fileInfo.textContent = `${f.name} (${sizeKB} KB)`;
					if (f.size > MAX_MB * 1024 * 1024) { reason.textContent = `File too large. Please upload ≤ ${MAX_MB} MB.`; } else { reason.textContent = ''; }
				}

				fileInput.addEventListener('change', updateInfo);

				form.addEventListener('submit', async (e) => {
					if (e.submitter && e.submitter.id === 'parseBtn') {
						e.preventDefault();
						const f = fileInput.files && fileInput.files[0];
						if (!f) { errEl.textContent = 'Please choose a file before parsing.'; return; }
						if (f.size > MAX_MB * 1024 * 1024) { errEl.textContent = `File too large. Please upload ≤ ${MAX_MB} MB.`; return; }
						const fd = new FormData(); fd.append('file', f, f.name);
						out.textContent = 'Parsing...'; meta.textContent = ''; errEl.textContent = '';
						const res = await fetch('/parse', { method: 'POST', body: fd, headers: { 'X-Requested-With': 'fetch' } });
						let data; try { data = await res.json(); } catch (ex) { data = { raw: await res.text() } }
						if (!res.ok) { errEl.textContent = (data.error || data.raw || res.statusText); out.textContent = ''; return; }
						meta.textContent = 'Meta: ' + JSON.stringify(data.meta);
						if (data.sections) {
							out.innerHTML = data.sections.map(s => `<div class=\"section\"><h4>${s.heading}</h4><div>${s.body.replace(/\n/g,'<br/>')}</div></div>`).join('');
						} else {
							const text = data.text || '';
							out.textContent = text ? (text.length > 4000 ? text.slice(0, 4000) + '\n... (truncated) ...' : text) : '(No extractable text found)';
						}
					}
				});
			});
			</script>
			</body>
			</html>
		"""
	)
	return Response(html, mimetype="text/html")


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
