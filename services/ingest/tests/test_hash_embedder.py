from aus_gov_ingest.embeddings.hash import HashEmbedder


def test_hash_embedder_is_deterministic_and_normalized() -> None:
    embedder = HashEmbedder(dim=32)
    a = embedder.embed(["APS capability and procurement"])[0]
    b = embedder.embed(["APS capability and procurement"])[0]
    assert a == b
    assert len(a) == 32
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_different_texts_differ() -> None:
    embedder = HashEmbedder(dim=32)
    a = embedder.embed(["freedom of information delays"])[0]
    b = embedder.embed(["regional aviation access"])[0]
    assert a != b
