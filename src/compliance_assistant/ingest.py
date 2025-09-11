from __future__ import annotations

from pathlib import Path

from .parsers import ParserFactory, ParsedDocument


def ingest_file(file_path: str | Path) -> ParsedDocument:
	parser = ParserFactory.for_file(file_path)
	return parser.parse(file_path)
