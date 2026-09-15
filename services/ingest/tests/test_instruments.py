from aus_gov_ingest.chunking import chunk_text
from aus_gov_ingest.instruments import propose_instruments
from aus_gov_ingest.pipeline import run_ingest
from pathlib import Path

EXCERPT = Path(__file__).resolve().parents[1] / "fixtures" / "transcript_fpa_28778_excerpt.json"


def test_propose_bill_program_contract_grant() -> None:
    text = (
        "Senator EXAMPLE: The Fair Work Amendment (Secure Jobs) Bill 2026 is before the House.\n\n"
        "Ms Official: The National Reconstruction Program funds that work.\n\n"
        "We signed a contract with Acme Holdings for the desktop refresh.\n\n"
        "A grant to Regional Landcare Network was paid in March."
    )
    chunks = chunk_text(text, max_chars=200, overlap=0)
    items = propose_instruments(
        chunks,
        hearing_source_key="hansard:committees/estimate/28778",
        document_source_key="hansard:committees/estimate/28778/0000",
    )
    kinds = {i.kind for i in items}
    assert "bill" in kinds
    assert "program" in kinds
    assert "contract" in kinds
    assert "grant" in kinds
    assert all(i.status == "proposed" for i in items)
    assert all(i.confidence < 0.6 for i in items)
    assert all(i.source_chunk_key for i in items)


def test_instrument_propose_source_dry_run() -> None:
    result = run_ingest(
        "instrument_propose",
        dry_run=True,
        source_path=str(EXCERPT),
    )
    assert result.status == "dry_run"
    assert result.meta["status"] == "proposed_only"
    # Excerpt is short; may or may not match bill regex — still a valid empty proposed set.
    assert result.meta["hearings_scanned"] == 1
    assert "proposed" in result.meta
