# EQON fixtures

Offline fallback for `--source qon` when the Senate Estimates Questions on
Notice API is unreachable from a datacentre IP (Azure Front Door 403, empty
JSON, or JS challenge on ParlInfo).

## Fetch path

1. Live: browser-like UA, session warm-up GET on the EQON hub, then
   `POST /api/qon/getestimatesdata` with a portfolio sweep.
2. If live throws **or returns no rows**, ingest reads every `*.json` in this
   folder (`fixture_fallback:…` in the batch meta).
3. Bulk ZIP downloads require My Parliament sign-in — not used.
4. OpenAustralia has **no** Estimates QoN feed.

Committed files are real EQON question JSON (© Commonwealth of Australia,
typically CC BY-NC-ND). Do not invent answers. See `../NOTES.md` for the
wider APH WAF matrix.
