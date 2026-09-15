from __future__ import annotations

from aus_gov_ingest.config import settings


class SentenceTransformerEmbedder:
    name = "sentence-transformers"

    def __init__(self, model_name: str | None = None, dim: int | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install extras: pip install 'aus-gov-ingest[sentence-transformers]'"
            ) from exc
        self.model_name = model_name or settings.st_embedding_model
        self.dim = dim or settings.embedding_dim
        self._model = SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self._model.encode(texts, normalize_embeddings=True)
        out: list[list[float]] = []
        for row in matrix:
            vec = [float(x) for x in row]
            if len(vec) > self.dim:
                vec = vec[: self.dim]
            elif len(vec) < self.dim:
                vec = vec + [0.0] * (self.dim - len(vec))
            out.append(vec)
        return out
