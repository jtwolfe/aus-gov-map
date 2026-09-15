from __future__ import annotations

from aus_gov_ingest.config import settings
from aus_gov_ingest.embeddings.base import Embedder
from aus_gov_ingest.embeddings.hash import HashEmbedder


def get_embedder(name: str | None = None) -> Embedder:
    provider = (name or settings.embedding_provider or "hash").lower()
    dim = settings.embedding_dim
    if provider in {"hash", "dummy", "fixture"}:
        return HashEmbedder(dim=dim)
    if provider == "openai":
        from aus_gov_ingest.embeddings.openai import OpenAIEmbedder

        return OpenAIEmbedder(dim=dim)
    if provider in {"sentence-transformers", "st", "minilm"}:
        from aus_gov_ingest.embeddings.sentence_transformers import (
            SentenceTransformerEmbedder,
        )

        return SentenceTransformerEmbedder(dim=dim)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER={provider!r}")


__all__ = ["Embedder", "HashEmbedder", "get_embedder"]
