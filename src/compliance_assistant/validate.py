


















































































































from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import yaml

try:
	from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
	AzureOpenAI = None  # type: ignore

try:
	from openai import OpenAI as StdOpenAI  # type: ignore
except Exception:  # pragma: no cover
	StdOpenAI = None  # type: ignore

try:
	from .kb import KB, load_guidelines  # type: ignore
except Exception:
	KB = None  # type: ignore
	def load_guidelines(paths):
		return None

try:
	from .sectionizer import split_into_sections  # type: ignore
except Exception:
	def split_into_sections(text: str):
		return [{"heading": "Document", "body": text}]


@dataclass
class Finding:
	id: str
	severity: str  # critical | major | minor
	message: str
	location: Optional[str] = None
	citation: Optional[str] = None
	section: Optional[str] = None
	pos: Optional[Tuple[int, int]] = None  # (start, end) of match if available


@dataclass
class ValidationResult:
	findings: List[Finding]
	score: int
	meta: Dict[str, str]


def _excerpt(text: str, start: int, end: int, radius: int = 80) -> str:
	"""Return a clean, human-readable excerpt around [start:end].
	- Expands by radius, trims to nearest word boundary, collapses whitespace,
	  and adds ellipses as needed.
	"""
	lo = max(0, start - radius)
	hi = min(len(text), end + radius)
	snip = text[lo:hi]
	# Collapse newlines and multiple spaces
	snip = re.sub(r"\s+", " ", snip).strip()
	# Trim to word boundaries
	m = re.search(r"\S.*\S", snip)
	if m:
		snip = snip[m.start(): m.end()+1]
	prefix = "… " if lo > 0 else ""
	suffix = " …" if hi < len(text) else ""
	return f"{prefix}{snip}{suffix}"


def _resolve_rules_path(path: Optional[str]) -> Path:
	"""Resolve the rules.yml path robustly.
	Priority:
	1) Provided absolute or CWD-relative path if it exists
	2) Project root (two levels up from this file) + config/rules.yml
	3) CWD config/rules.yml
	"""
	if path:
		candidate = Path(path)
		if not candidate.is_absolute():
			# First try relative to current working directory
			if Path(path).exists():
				candidate = Path(path)
			else:
				# Then relative to project root (repo root is two levels up: .../src/compliance_assistant/validate.py)
				project_root = Path(__file__).resolve().parents[2]
				candidate = (project_root / path).resolve()
		if candidate.exists():
			return candidate
	# Fallback to project root config path
	project_root = Path(__file__).resolve().parents[2]
	default_path = project_root / "config" / "rules.yml"
	if default_path.exists():
		return default_path
	# Last resort: try CWD config
	cwd_fallback = Path("config") / "rules.yml"
	if cwd_fallback.exists():
		return cwd_fallback
	raise FileNotFoundError(f"rules.yml not found. Tried: {path or ''}, {default_path}, {cwd_fallback}")


def _load_rules(path: Optional[str] = None) -> dict:
	rules_path = _resolve_rules_path(path or "config/rules.yml")
	with open(rules_path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f)


def _detect_required_sections(text: str, sections: List[str]) -> List[Finding]:
	findings: List[Finding] = []
	lower_text = text.lower()
	for sec in sections:
		if sec.lower() not in lower_text:
			# Treat missing core sections as critical
			findings.append(Finding(id="missing_section", severity="critical", message=f"Missing section: {sec}"))
	return findings


def _detect_approvals(text: str, approvals: List[str]) -> List[Finding]:
	findings: List[Finding] = []
	lower_text = text.lower()
	for label in approvals:
		if label.lower() not in lower_text:
			findings.append(Finding(id="missing_approval", severity="critical", message=f"Missing approval line: {label}"))
	return findings


def _detect_placeholders(text: str, patterns: List[str]) -> List[Finding]:
	findings: List[Finding] = []
	for pat in patterns:
		# Avoid penalizing common, legitimate "N/A"
		if pat.strip() == r"\bN/?A\b":
			continue
		for m in re.finditer(pat, text, flags=re.IGNORECASE):
			# Do not treat signature lines (e.g., __________) adjacent to approval labels as placeholders
			matched_text = m.group(0)
			if re.fullmatch(r"_+", matched_text):
				window_lo = max(0, m.start() - 80)
				window_hi = min(len(text), m.end() + 80)
				window = text[window_lo:window_hi].lower()
				if re.search(r"\b(prepared by|reviewed by|approved by|signature)\b", window):
					continue
			context = _excerpt(text, m.start(), m.end())
			findings.append(Finding(id="placeholder", severity="major", message=f"Placeholder detected: '{matched_text}'", location=context, pos=(m.start(), m.end())))
	return findings


def _detect_stale_references(text: str, years_threshold: int) -> List[Finding]:
	findings: List[Finding] = []
	now = _dt.datetime.now().date()
	date_patterns = [
		r"\b(19|20)\d{2}\b",
		r"\b\d{1,2}[\-/](\d{1,2}|[A-Za-z]{3})[\-/](19|20)\d{2}\b",
		r"\b(19|20)\d{2}-\d{2}-\d{2}\b",
	]
	seen_labels: set[str] = set()
	for pat in date_patterns:
		for m in re.finditer(pat, text):
			val = m.group(0)
			try:
				matched = False
				for fmt in ("%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d/%b/%Y"):
					try:
						d = _dt.datetime.strptime(val, fmt).date()
						age_years = (now - d).days / 365.25
						if age_years > years_threshold:
							# Only flag if near update/version keywords to avoid penalizing citations
							window_lo = max(0, m.start() - 80)
							window_hi = min(len(text), m.end() + 80)
							window = text[window_lo:window_hi].lower()
							if re.search(r"\b(effective|last\s*(reviewed|updated)|version|rev(ision)?)\b", window):
								# Deduplicate by label so repeated versions table rows don't stack
								label = "version" if "version" in window else ("effective" if "effective" in window else ("last" if "last" in window else "rev"))
								if label in seen_labels:
									matched = True
									break
								seen_labels.add(label)
								ctx = _excerpt(text, m.start(), m.end())
								findings.append(Finding(id="stale_reference", severity="minor", message=f"Stale date/reference: {val} (~{age_years:.1f}y)", location=ctx, pos=(m.start(), m.end())))
							matched = True
							break
					except Exception:
						continue
				if matched:
					continue
			except Exception:
				continue
	return findings


def _detect_numbered_steps(text: str, require_numbering: bool) -> List[Finding]:
	findings: List[Finding] = []
	if not require_numbering:
		return findings
	lower = text.lower()
	idx = lower.find("procedure")
	if idx == -1:
		return findings
	snippet = text[idx: idx + 4000]
	lines = [l.strip() for l in snippet.splitlines() if l.strip()]
	step_like = sum(1 for l in lines if re.match(r"^(\d+\.|\d+\)|step\s*\d+\b)", l, flags=re.IGNORECASE))
	# Require at least 2 steps or 5% of lines, whichever is higher
	if step_like < max(2, int(len(lines) * 0.05)):
		findings.append(Finding(id="steps_numbering", severity="major", message="Procedure lacks sufficient numbered steps"))
	return findings


def _score(findings: List[Finding], weights: Dict[str, int], id_penalties: Optional[Dict[str, int]] = None) -> int:
	penalty = 0
	severity_multipliers = {"critical": 8, "major": 4, "minor": 1}
	id_penalties = id_penalties or {}
	for f in findings:
		sev = f.severity.lower()
		penalty += weights.get(sev, 1) * severity_multipliers.get(sev, 1)
		penalty += int(id_penalties.get(f.id, 0))
	# Bound penalty and compute score
	score = max(0, 100 - min(100, penalty))
	return score


def _maybe_llm_findings(text: str, llm_cfg: Optional[Dict[str, object]]) -> List[Finding]:
	# Respect config flag
	if not llm_cfg or not bool(llm_cfg.get("enabled", False)):
		return []

	# Common prompt
	prompt = (
		"You are a GxP compliance assistant. Analyze the following document text and list any compliance gaps "
		"such as missing approvals/signatures, missing or weak sections, placeholders, stale references, and procedure steps issues. "
		"Return JSON with an array 'findings' where each item has fields: severity in [critical, major, minor], message.\n\n"
		f"Document:\n{text[:12000]}"
	)

	# Azure OpenAI path
	use_azure = (str(llm_cfg.get("provider", "")).lower() == "azure") or (
		os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")
	)
	if use_azure and AzureOpenAI is not None:
		api_key = os.getenv("AZURE_OPENAI_API_KEY")
		endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
		deployment = str(llm_cfg.get("deployment", os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")))
		api_version = str(llm_cfg.get("api_version", os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")))
		try:
			client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
			resp = client.chat.completions.create(
				model=deployment,
				messages=[
					{"role": "system", "content": "You are a strict GxP auditor."},
					{"role": "user", "content": prompt},
				],
				temperature=float(llm_cfg.get("temperature", 0.1)),
				max_tokens=int(llm_cfg.get("max_tokens", 800)),
			)
			content = resp.choices[0].message.content or ""
			re_match = re.search(r"\{[\s\S]*\}\s*$", content)
			if not re_match:
				return []
			import json
			obj = json.loads(re_match.group(0))
			llm_findings: List[Finding] = []
			for it in obj.get("findings", []):
				sev = (it.get("severity") or "minor").lower()
				msg = it.get("message") or "LLM finding"
				llm_findings.append(Finding(id="llm", severity=sev, message=msg))
			return llm_findings
		except Exception:
			return []

	# Standard OpenAI path
	if StdOpenAI is not None and os.getenv("OPENAI_API_KEY"):
		try:
			client = StdOpenAI()
			model = str(llm_cfg.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini")))
			resp = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": "You are a strict GxP auditor."},
					{"role": "user", "content": prompt},
				],
				temperature=float(llm_cfg.get("temperature", 0.1)),
				max_tokens=int(llm_cfg.get("max_tokens", 800)),
			)
			content = resp.choices[0].message.content or ""
			re_match = re.search(r"\{[\s\S]*\}\s*$", content)
			if not re_match:
				return []
			import json
			obj = json.loads(re_match.group(0))
			llm_findings = []
			for it in obj.get("findings", []):
				sev = (it.get("severity") or "minor").lower()
				msg = it.get("message") or "LLM finding"
				llm_findings.append(Finding(id="llm", severity=sev, message=msg))
			return llm_findings
		except Exception:
			return []

	return []


def validate_text(text: str, meta: Optional[Dict[str, str]] = None, rules_path: Optional[str] = None, kb: Optional[KB] = None) -> ValidationResult:
	rules = _load_rules(rules_path)
	findings: List[Finding] = []
	findings += _detect_required_sections(text, rules.get("required_sections", []))
	findings += _detect_approvals(text, rules.get("approvals_lines", []))
	findings += _detect_placeholders(text, rules.get("placeholder_patterns", []))
	findings += _detect_stale_references(text, int(rules.get("stale_reference", {}).get("years_threshold", 3)))
	findings += _detect_numbered_steps(text, bool(rules.get("numbered_steps", {}).get("require_numbering", True)))
	# Optional AI (LLM)
	findings += _maybe_llm_findings(text, rules.get("llm"))
	# Attach citations from KB if available
	if kb is None:
		kb = load_guidelines(["21.txt", "general.txt"])  # project root defaults
	try:
		if kb is not None:
			for f in findings:
				sims = kb.similar(f.message, k=1)
				if sims:
					f.citation = sims[0][1]
	except Exception:
		pass
	# Map findings to sections for better context
	sections = split_into_sections(text)
	for f in findings:
		if f.id == "missing_section":
			# encode the missing section name as the section
			missing = f.message.split(":", 1)[-1].strip()
			f.section = f"Missing: {missing}"
			continue
		if f.id == "steps_numbering":
			f.section = "Procedure"
			continue
		# Use precise position if available
		if f.pos:
			start, end = f.pos
			for s in sections:
				if start >= s.get("start", 0) and start < s.get("end", 0):
					f.section = s["heading"]
					break
		# Fallback using token search
		if not f.section:
			token = None
			if f.location:
				token = re.sub(r"\s+", " ", f.location.strip())[:40]
			if token:
				for s in sections:
					if token in re.sub(r"\s+", " ", s["body"]):
						f.section = s["heading"]
						break
		if not f.section and sections:
			f.section = sections[0]["heading"]
	weights = {str(k).lower(): int(v) for k, v in rules.get("severity_weights", {}).items()}
	id_penalties_cfg = rules.get("id_penalties", {}) if isinstance(rules, dict) else {}
	score = _score(findings, weights, id_penalties_cfg)
	return ValidationResult(findings=findings, score=score, meta=meta or {})
