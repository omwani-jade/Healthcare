from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader  # type: ignore

from .base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
	def parse(self, file_path: str | Path) -> ParsedDocument:
		path = Path(file_path)
		reader = PdfReader(str(path))
		pages_text = []
		for page in reader.pages:
			try:
				pages_text.append(page.extract_text() or "")
			except Exception:
				# Some pages may fail text extraction; skip but keep alignment
				pages_text.append("")
		raw_text = "\n".join(pages_text)
		text = self._normalize_text(raw_text)
		return ParsedDocument(
			text=text,
			meta={
				"filename": path.name,
				"suffix": path.suffix.lower(),
				"parser": "pdf",
				"num_pages": str(len(reader.pages)),
			},
		)
