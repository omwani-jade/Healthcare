from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class ParsedDocument:
	text: str
	meta: Dict[str, str]


class DocumentParser(ABC):
	@abstractmethod
	def parse(self, file_path: str | Path) -> ParsedDocument:
		raise NotImplementedError

	@staticmethod
	def _normalize_text(text: str) -> str:
		# Collapse excessive whitespace while preserving newlines
		# Replace Windows newlines, normalize spaces around newlines
		normalized = text.replace("\r\n", "\n").replace("\r", "\n")
		# Strip trailing spaces on each line
		normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
		# Ensure no more than two consecutive newlines
		while "\n\n\n" in normalized:
			normalized = normalized.replace("\n\n\n", "\n\n")
		return normalized.strip()
