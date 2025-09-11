from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

try:
	from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
	AzureOpenAI = None  # type: ignore


def _chunk(text: str, max_len: int = 800) -> List[str]:
	parts: List[str] = []
	buf: List[str] = []
	count = 0
	for line in text.splitlines():
		line = line.strip()
		if not line:
			if count > max_len * 0.7:
				parts.append(" ".join(buf))
				buf, count = [], 0
			continue
		buf.append(line)
		count += len(line)
		if count >= max_len:
			parts.append(" ".join(buf))
			buf, count = [], 0
	if buf:
		parts.append(" ".join(buf))
	return parts


@dataclass
class KB:
	chunks: List[str]
	embed: List[List[float]]
	paths: List[str]

	def similar(self, query: str, k: int = 3) -> List[Tuple[float, str]]:
		if not self.embed:
			return []
		qv = _embed_texts([query])[0]
		# cosine similarity
		def cos(a: List[float], b: List[float]) -> float:
			import math
			n = min(len(a), len(b))
			dot = sum(a[i] * b[i] for i in range(n))
			norm = (math.sqrt(sum(x*x for x in a[:n])) * math.sqrt(sum(x*x for x in b[:n])) + 1e-8)
			return dot / norm
		scores = [(cos(qv, v), self.chunks[i]) for i, v in enumerate(self.embed)]
		scores.sort(key=lambda x: x[0], reverse=True)
		return scores[:k]


def _client():
	if AzureOpenAI is None:
		return None
	api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
	endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
	if not (api_key and endpoint):
		return None
	try:
		return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
	except Exception:
		# If client cannot be created (e.g., SDK mismatch), disable embeddings gracefully
		return None


def _embed_texts(texts: List[str]) -> List[List[float]]:
	client = _client()
	if client is None:
		return [[0.0] * 10 for _ in texts]
	try:
		deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", os.getenv("AZURE_OPENAI_EMBEDDINGS", "hackathon-em-group3"))
		resp = client.embeddings.create(input=texts, model=deployment)
		return [d.embedding for d in resp.data]
	except Exception:
		return [[0.0] * 10 for _ in texts]


def load_guidelines(paths: List[str]) -> KB:
	all_chunks: List[str] = []
	for p in paths:
		path = Path(p)
		if not path.exists():
			continue
		text = path.read_text(encoding="utf-8", errors="ignore")
		all_chunks.extend(_chunk(text))
	embeds = _embed_texts(all_chunks) if all_chunks else []
	return KB(chunks=all_chunks, embed=embeds, paths=[str(p) for p in paths])
