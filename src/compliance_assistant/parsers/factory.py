from __future__ import annotations

from pathlib import Path
from typing import Dict, Type

from .base import DocumentParser
from .docx_parser import DocxParser
from .pdf_parser import PdfParser
from .txt_parser import TxtParser


_EXTENSION_TO_PARSER: Dict[str, Type[DocumentParser]] = {
	".txt": TxtParser,
	".docx": DocxParser,
	".pdf": PdfParser,
}


class ParserFactory:
	@staticmethod
	def for_file(file_path: str | Path) -> DocumentParser:
		path = Path(file_path)
		parser_cls = _EXTENSION_TO_PARSER.get(path.suffix.lower())
		if not parser_cls:
			raise ValueError(f"Unsupported file type: {path.suffix}")
		return parser_cls()
