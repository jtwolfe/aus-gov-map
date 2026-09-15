from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from aus_gov_ingest.pipeline import run_ingest


def main(limit: int = 0) -> int:
    """Entrypoint stub for cron / systemd timers.

    Incremental Estimates schedule: only upsert hearings with a new source_key.
    Exit 0 on success (including “nothing new”). Exit 1 on pipeline failure.
    """
    started = datetime.now(timezone.utc).isoformat()
    print(f"[aus-gov-ingest] cron start {started}", flush=True)
    try:
        result = run_ingest(
            "estimates",
            limit=limit,
            incremental=True,
            write_graph=True,
        )
    except Exception as exc:
        print(f"[aus-gov-ingest] cron failed: {exc}", file=sys.stderr, flush=True)
        return 1
    print(json.dumps(result.__dict__, default=str), flush=True)
    print("[aus-gov-ingest] cron done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
