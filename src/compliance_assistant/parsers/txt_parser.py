from __future__ import annotations

from pathlib import Path

from .base import DocumentParser, ParsedDocument


class TxtParser(DocumentParser):
	def parse(self, file_path: str | Path) -> ParsedDocument:
		path = Path(file_path)
		with path.open("r", encoding="utf-8", errors="ignore") as f:
			raw_text = f.read()
		text = self._normalize_text(raw_text)
		return ParsedDocument(
			text=text,
			meta={
				"filename": path.name,
				"suffix": path.suffix.lower(),
				"parser": "txt",
			},
		)
