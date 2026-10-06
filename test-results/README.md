# Test Results

All files here come from real runs on the local Docker setup (dev service, port 5200). No token or encrypted auth value is stored in these files (checked with a search for the encrypted-blob prefix, token prefixes and `accessToken`: 0 matches).

| Check | File | Result |
|---|---|---|
| 5 test deals created in HubSpot | `deal-ids.md` | PASS (5 IDs recorded) |
| Live API check, 5/5 deals match, 3-page cursor pagination | scripts/live_api_check.py | PASS |
| Health endpoints `/health`, `/api/health` | `health-check.txt` | PASS (HTTP 200) |
| Swagger UI `/docs/` and OpenAPI JSON `/api/swagger.json` | `api-docs.md` | PASS (HTTP 200, 15 endpoints) |
| Start scan, run to completion, 5 deals | `scan-status.json`, `results.json` | PASS (completed, recordsExtracted 5) |
| Results API returns the deals (default table `hubspot_deals`) | `results.json` | PASS (total 5, records 5) |
| Database check: 5 rows, correct values, 7 indexes | `db-verification.txt` | PASS |
| Pause, service restart, resume from checkpoint | `checkpoint-test.md` | PASS (resumed at page 4 from saved cursor, 5 unique deals) |
| Cancel and remove | `cancel-remove-test.md` | PASS (cancelled stays cancelled, removed scan returns 404) |
| docker compose down/up, data persists, fresh scan works | `restart-test.md` | PASS |
| Unit and mocked tests (`pytest -q`) | n/a | 14 passed |
| Service log excerpt | `service.log` | see notes below |

## Security checks (real runs)
- `GET /api/scan/{id}/status` returns `config` with only `filters` and `type`; no `auth` field.
- Service log has no encrypted-blob prefix and no SQL parameter dump; the HubSpot token is logged masked.

## Notes
- Checkpoint tests used `docker-compose.checkpoint.yml` (page size 1, 6 s delay per page) so a scan lasts long enough to pause. It is a test-only override, not part of the default setup.
- While a job is paused, `recordsExtracted` in `/status` shows 0; real progress is in `checkpointInfo.latestCheckpoint.recordsProcessed`.
- Pause takes effect at a page boundary: the page being fetched finishes and is checkpointed, then the job stops.
- Known log messages: `werkzeug: Debugger is active!` appears only in the dev container (`FLASK_DEBUG=true`; staging and production use `false`). `Job not found` (WARNING) is the duplicate scanId lookup at the start of every scan, before `Job created`.
- Bug found and fixed during testing: the results endpoint defaulted to table `users` (template leftover) and returned no records; the default is now `hubspot_deals`.
