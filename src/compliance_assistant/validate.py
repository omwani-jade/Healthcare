from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yaml

try:
	from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
	AzureOpenAI = None  # type: ignore

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


def _load_rules(path: str = "config/rules.yml") -> dict:
	with open(path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f)


def _detect_required_sections(text: str, sections: List[str]) -> List[Finding]:
	findings: List[Finding] = []
	lower_text = text.lower()
	for sec in sections:
		if sec.lower() not in lower_text:
			findings.append(Finding(id="missing_section", severity="major", message=f"Missing section: {sec}"))
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
		for m in re.finditer(pat, text, flags=re.IGNORECASE):
			context = _excerpt(text, m.start(), m.end())
			findings.append(Finding(id="placeholder", severity="major", message=f"Placeholder detected: '{m.group(0)}'", location=context, pos=(m.start(), m.end())))
	return findings


def _detect_stale_references(text: str, years_threshold: int) -> List[Finding]:
	findings: List[Finding] = []
	now = _dt.datetime.now().date()
	date_patterns = [
		r"\b(19|20)\d{2}\b",
		r"\b\d{1,2}[\-/](\d{1,2}|[A-Za-z]{3})[\-/](19|20)\d{2}\b",
		r"\b(19|20)\d{2}-\d{2}-\d{2}\b",
	]
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
	step_like = sum(1 for l in lines if re.match(r"^\d+\.", l))
	if step_like < max(3, int(len(lines) * 0.1)):
		findings.append(Finding(id="steps_numbering", severity="major", message="Procedure lacks sufficient numbered steps"))
	return findings


def _score(findings: List[Finding], weights: Dict[str, int]) -> int:
	penalty = 0
	for f in findings:
		penalty += weights.get(f.severity.lower(), 1)
	score = max(0, 100 - min(100, penalty * 5))
	return score


def _maybe_llm_findings(text: str) -> List[Finding]:
	if AzureOpenAI is None:
		return []
	api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
	endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "hackathon-group3")
	api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
	if not (api_key and endpoint):
		return []
	try:
		client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
		prompt = (
			"You are a GxP compliance assistant. Analyze the following document text and list any compliance gaps "
			"such as missing approvals/signatures, missing or weak sections, placeholders, stale references, and procedure steps issues. "
			"Return JSON with an array 'findings' where each item has fields: severity in [critical, major, minor], message.\n\n"
			f"Document:\n{text[:12000]}"
		)
		resp = client.chat.completions.create(
			model=deployment,
			messages=[
				{"role": "system", "content": "You are a strict GxP auditor."},
				{"role": "user", "content": prompt},
			],
			temperature=0.1,
			max_tokens=800,
		)
		content = resp.choices[0].message.content or ""
		# Try to extract JSON object at the end if any
		m = re.search(r"\{[\s\S]*\}\s*$", content)
		if not m:
			return []
		import json
		obj = json.loads(m.group(0))
		llm_findings: List[Finding] = []
		for it in obj.get("findings", []):
			sev = (it.get("severity") or "minor").lower()
			msg = it.get("message") or "LLM finding"
			llm_findings.append(Finding(id="llm", severity=sev, message=msg))
		return llm_findings
	except Exception:
		return []


def validate_text(text: str, meta: Optional[Dict[str, str]] = None, rules_path: str = "config/rules.yml", kb: Optional[KB] = None) -> ValidationResult:
	rules = _load_rules(rules_path)
	findings: List[Finding] = []
	findings += _detect_required_sections(text, rules.get("required_sections", []))
	findings += _detect_approvals(text, rules.get("approvals_lines", []))
	findings += _detect_placeholders(text, rules.get("placeholder_patterns", []))
	findings += _detect_stale_references(text, int(rules.get("stale_reference", {}).get("years_threshold", 3)))
	findings += _detect_numbered_steps(text, bool(rules.get("numbered_steps", {}).get("require_numbering", True)))
	# Optional AI
	findings += _maybe_llm_findings(text)
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
	score = _score(findings, weights)
	return ValidationResult(findings=findings, score=score, meta=meta or {})
