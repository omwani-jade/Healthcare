from __future__ import annotations

import re
from typing import List, Dict

COMMON_HEADINGS = [
	"title",
	"document id",
	"version",
	"effective date",
	"next review date",
	"revision history",
	"introduction",
	"purpose",
	"scope",
	"responsibilities",
	"definitions",
	"procedure",
	"procedures",
	"acceptance criteria",
	"documentation",
	"deviations",
	"references",
	"records",
	"approvals",
]

_HEADING_RE = re.compile(
	# placeholder for future use; main logic in _is_heading
	r"^(?:\s*(?:\d+(?:\.\d+)*[\)\.]\s+)?.{1,80})$",
	re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
	l = line.strip()
	if not l:
		return False
	if l.lower() in COMMON_HEADINGS:
		return True
	if l.endswith(":") and l[:-1].strip().lower() in COMMON_HEADINGS:
		return True
	if re.match(r"^\d+(?:\.\d+)*[\)\.]?\s+\S", l):
		return True
	words = l.split()
	if 0 < len(words) <= 6 and all(w.isupper() or not any(c.isalpha() for c in w) for w in words):
		return True
	return False


def split_into_sections(text: str) -> List[Dict[str, str]]:
	lines = text.split("\n")
	sections: List[Dict[str, str]] = []
	heading = "Document"
	buf: List[str] = []
	# Track character offsets while iterating lines
	cursor = 0
	section_start = 0  # start of current section body
	for line in lines:
		stripped = line.strip()
		line_len_with_nl = len(line) + 1  # account for the split '\n'
		if _is_heading(stripped):
			# flush previous body
			if buf:
				body = "\n".join(buf)
				sections.append({
					"heading": heading.rstrip(":"),
					"body": body.strip(),
					"start": section_start,
					"end": cursor,  # end is just before this heading line
				})
				buf = []
			# new section; body starts after this heading line
			heading = stripped.rstrip(":")
			section_start = cursor + line_len_with_nl
		else:
			buf.append(line)
		# advance cursor after processing this line
		cursor += line_len_with_nl
	# flush last
	if buf:
		body = "\n".join(buf)
		sections.append({
			"heading": heading.rstrip(":"),
			"body": body.strip(),
			"start": section_start,
			"end": cursor,
		})
	sections = [s for s in sections if s["body"]]
	if not sections:
		return [{"heading": "Document", "body": text.strip(), "start": 0, "end": len(text)}]
	return sections
