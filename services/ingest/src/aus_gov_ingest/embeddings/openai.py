from __future__ import annotations

import httpx

from aus_gov_ingest.config import settings


class OpenAIEmbedder:
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dim: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model
        self.dim = dim or settings.embedding_dim
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self.model, "input": texts}
        with httpx.Client(timeout=60) as client:
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()["data"]
        vectors = [row["embedding"] for row in sorted(data, key=lambda r: r["index"])]
        return [_fit_dim(vec, self.dim) for vec in vectors]


def _fit_dim(vec: list[float], dim: int) -> list[float]:
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))
