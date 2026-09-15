from aus_gov_ingest.chunking import chunk_text


def test_chunk_text_splits_and_tags_speaker() -> None:
    text = (
        "CHAIR: The committee will now examine Finance.\n\n"
        "Senator PATERSON: How many SES roles are vacant?\n\n"
        "Prof. DAVIS: We publish workforce metrics in the annual report."
    )
    chunks = chunk_text(text, max_chars=80, overlap=0)
    assert len(chunks) >= 2
    assert chunks[0].speaker_name
    assert "committee" in chunks[0].content.lower()


def test_empty_text() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []
