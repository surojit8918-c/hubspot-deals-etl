# API Documentation (Swagger), captured from the running service

Captured: 2026-10-06 08:45 (local time)

- Swagger UI: http://localhost:5200/docs/ (HTTP 200)
- OpenAPI JSON: http://localhost:5200/api/swagger.json (HTTP 200)
- Base path: /api

| Method | Path | Summary |
|---|---|---|
| GET | /api/health | Health check endpoint |
| POST | /api/maintenance/cleanup | Clean up old scan results |
| POST | /api/maintenance/detect-crashed | Detect and mark crashed jobs |
| GET | /api/pipeline/info | Get information about the DLT pipeline configuration |
| GET | /api/results/{scan_id}/result | Get scan results with pagination and table selection |
| GET | /api/results/{scan_id}/tables | Get available tables for a completed scan |
| GET | /api/scan/list | List all scans with optional filtering and pagination |
| POST | /api/scan/start | Start a new data extraction scan |
| GET | /api/scan/statistics | Get scan statistics |
| POST | /api/scan/{scan_id}/cancel | Cancel a running scan |
| POST | /api/scan/{scan_id}/pause | Pause a running scan |
| DELETE | /api/scan/{scan_id}/remove | Remove a scan and its data |
| POST | /api/scan/{scan_id}/resume | Resume a paused or crashed scan |
| GET | /api/scan/{scan_id}/status | Get the status of a specific scan |
| GET | /api/stats | Get service statistics |
