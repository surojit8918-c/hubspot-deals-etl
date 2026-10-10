# 📖 HubSpot Deals ETL Service - REST API Documentation

This document provides complete documentation for the `hubspot_deals` extraction service REST API, including endpoint specifications, request/response schemas, status code mappings, lifecycle states, authentication rules, and example `curl` commands.

---

## 📋 Overview

The `hubspot_deals` service exposes a RESTful API built with Flask and Flask-RESTX to manage asynchronous HubSpot deal extraction jobs.

### Key Features
- **Asynchronous Extraction**: Triggers background DLT pipelines to extract, transform, and load HubSpot CRM deals into tenant-isolated PostgreSQL schemas.
- **Job Control**: Supports pausing, resuming, cancelling, listing, and removing extraction jobs.
- **Checkpointing**: Automatically saves state cursors during extraction so jobs can resume seamlessly after interruption.
- **Interactive OpenAPI/Swagger UI**: Available at `/docs/`.

### Base URLs & Environment Ports
- **Development**: `http://localhost:5200` (API prefix: `/api`)
- **Staging**: `http://localhost:5201` (API prefix: `/api`)
- **Production**: `http://localhost:5202` (API prefix: `/api`)
- **Interactive Swagger Docs**: `http://localhost:5200/docs/`

---

## 🔐 Authentication & Security

- **Coordinator HMAC Authentication**: All protected API endpoints (`/api/*`) require Coordinator authentication via HTTP headers:
  - **`X-Coordinator-Signature`**: HMAC-SHA256 hex digest of the raw HTTP request body payload computed using `COORDINATOR_KEY` (e.g., `X-Coordinator-Signature: sha256=<hex_digest>`).
  - **`X-Coordinator-Key`**: Direct secret key matching `COORDINATOR_KEY` verified via constant-time comparison (`hmac.compare_digest`).
- **Whitelisted Endpoints** (No authentication required):
  - `GET /health` and `GET /api/health` (Health Checks)
  - `GET /docs/` & OpenAPI specs (Swagger Documentation)
  - `GET /` (Service Index)
  - `OPTIONS` requests (CORS Preflight)
- **Error Response (`401 Unauthorized`)**:
  If missing or invalid signature/key headers are provided:
  ```json
  {
    "success": false,
    "message": "Unauthorized: Invalid or missing coordinator signature"
  }
  ```
- **Curl Examples**:
  ```bash
  # Using X-Coordinator-Key
  curl -X POST http://localhost:5200/api/scan/start \
    -H "Content-Type: application/json" \
    -H "X-Coordinator-Key: dev-coordinator-secret-key" \
    -d '{"scanId": "scan-100", "organizationId": "org-1", "config": {"auth": {"accessToken": "pat-na1-12345"}}}'

  # Using X-Coordinator-Signature (HMAC-SHA256)
  # Signature = HMAC-SHA256(COORDINATOR_KEY, request_body)
  curl -X GET http://localhost:5200/api/results/scan-100/result?tableName=hubspot_deals \
    -H "X-Coordinator-Signature: sha256=a1b2c3d4e5f6..."
  ```

- **HubSpot Access Token**: Passed inside the start scan request body under `config.auth.accessToken`.
- **Token Masking**: Access tokens are masked in logs (e.g. `pat-na1-****abcd`) and encrypted at rest in the internal database. Plaintext tokens are **never** logged, printed, or returned in API responses.

---

## 🔄 Job Status Lifecycle

Extraction jobs transition through the following standard status lifecycle:

```
                  ┌──────────┐
                  │ pending  │
                  └────┬─────┘
                       │
                       ▼
                  ┌──────────┐
                  │ running  │◄────────────┐
                  └─┬──┬──┬──┘             │
                    │  │  │                │
         ┌──────────┘  │  └──────────┐     │
         ▼             ▼             ▼     │
   ┌───────────┐ ┌───────────┐ ┌───────────┴─┐
   │ completed │ │  failed   │ │   paused    │
   └───────────┘ └───────────┘ └─────┬───────┘
         ▲             ▲             │
         │             │             ▼
         │             │       ┌───────────┐
         └─────────────┴───────┤ resuming  │
                               └───────────┘
```

Possible Status Values:
- `pending`: Scan request accepted and queued.
- `running`: Active extraction in progress.
- `completed`: All deal records successfully extracted and loaded into PostgreSQL.
- `paused`: Scan paused by user request; checkpoint cursor saved.
- `resuming`: Resume requested; restoring checkpoint state.
- `failed`: Extraction encountered an error (e.g. invalid credentials or max retries exhausted).
- `cancelled`: Extraction terminated by user request.
- `crashed`: Service process restarted unexpectedly while scan was running.

---

## 📊 Endpoints Reference

---

### 1. Health Checks

#### `GET /health` & `GET /api/health`
Checks service and database connectivity.

- **Auth Required**: None
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "timestamp": "2026-10-04T18:45:00.000000Z",
  "service": "hubspot_deals",
  "checks": {
    "database": "healthy"
  }
}
```

**Curl Example**:
```bash
curl -X GET http://localhost:5200/health
```

---

### 2. Extraction Management

#### `POST /api/scan/start`
Starts a background extraction job for HubSpot deals.

- **Request Schema**:
```json
{
  "config": {
    "scanId": "deals-test-001",
    "organizationId": "test-portal",
    "type": ["deal"],
    "auth": {
      "accessToken": "pat-na1-xxxx-xxxx-xxxx"
    },
    "filters": {
      "properties": ["dealname", "amount", "dealstage", "pipeline", "closedate"],
      "includeArchived": false,
      "dateRange": {
        "startDate": "2026-01-01",
        "endDate": "2026-12-31"
      }
    }
  }
}
```

- **Validation Rules**:
  - `config.scanId`: Regex `^[a-zA-Z0-9_-]+$`, 1..255 characters.
  - `config.organizationId`: 1..255 characters.
  - `config.type`: Must contain `"deal"`.
  - `config.auth.accessToken`: String, min length 10.

- **Response `202 Accepted`**:
```json
{
  "success": true,
  "message": "Scan started successfully",
  "scanId": "deals-test-001"
}
```

- **Status Codes**:
  - `202`: Job accepted and background processing initiated.
  - `400`: Validation error (invalid scanId format, missing token, invalid date format).
  - `409`: Conflict (scanId already exists).
  - `500`: Internal server error.

**Curl Example**:
```bash
curl -X POST http://localhost:5200/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "scanId": "deals-test-001",
      "organizationId": "test-portal",
      "type": ["deal"],
      "auth": { "accessToken": "pat-na1-xxxx-xxxx-xxxx" },
      "filters": { "includeArchived": false }
    }
  }'
```

---

#### `GET /api/scan/{scan_id}/status`
Retrieves current job execution status and progress metrics.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "scanId": "deals-test-001",
  "organizationId": "test-portal",
  "status": "completed",
  "totalItems": 5,
  "processedItems": 5,
  "failedItems": 0,
  "errorMessage": null,
  "startedAt": "2026-10-04T18:45:00Z",
  "completedAt": "2026-10-04T18:45:05Z"
}
```

- **Status Codes**:
  - `200`: Status retrieved successfully.
  - `404`: Scan ID not found.

**Curl Example**:
```bash
curl -X GET http://localhost:5200/api/scan/deals-test-001/status
```

---

#### `POST /api/scan/{scan_id}/pause`
Pauses an active extraction job and saves the current pagination cursor.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Scan pause requested successfully",
  "scanId": "deals-test-001"
}
```

- **Status Codes**:
  - `200`: Pause request issued.
  - `404`: Scan ID not found.
  - `409`: Job is not in a pausable state (`running`).

**Curl Example**:
```bash
curl -X POST http://localhost:5200/api/scan/deals-test-001/pause
```

---

#### `POST /api/scan/{scan_id}/resume`
Resumes a previously paused extraction job from its saved checkpoint cursor.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Scan resumed successfully",
  "scanId": "deals-test-001"
}
```

- **Status Codes**:
  - `200`: Resume request accepted.
  - `404`: Scan ID not found.
  - `409`: Job is not in `paused` state.

**Curl Example**:
```bash
curl -X POST http://localhost:5200/api/scan/deals-test-001/resume
```

---

#### `POST /api/scan/{scan_id}/cancel`
Cancels a running or paused extraction job.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Scan cancelled successfully",
  "scanId": "deals-test-001"
}
```

- **Status Codes**:
  - `200`: Job cancelled.
  - `404`: Scan ID not found.

**Curl Example**:
```bash
curl -X POST http://localhost:5200/api/scan/deals-test-001/cancel
```

---

#### `DELETE /api/scan/{scan_id}/remove`
Removes scan record and drops/cleans associated tenant data.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Scan deleted successfully",
  "scanId": "deals-test-001"
}
```

- **Status Codes**:
  - `200`: Scan deleted.
  - `404`: Scan ID not found.

**Curl Example**:
```bash
curl -X DELETE http://localhost:5200/api/scan/deals-test-001/remove
```

---

#### `GET /api/scan/list`
Lists extraction jobs with optional status and pagination filters.

- **Query Parameters**:
  - `organization_id` (string, optional)
  - `status` (string, optional)
  - `page` (int, default 1)
  - `limit` (int, default 50)
- **Response `200 OK`**:
```json
{
  "jobs": [
    {
      "scanId": "deals-test-001",
      "organizationId": "test-portal",
      "status": "completed",
      "processedItems": 5,
      "createdAt": "2026-10-04T18:45:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 50
}
```

**Curl Example**:
```bash
curl -X GET "http://localhost:5200/api/scan/list?limit=10"
```

---

#### `GET /api/scan/statistics` & `GET /api/stats`
Retrieves aggregated execution metrics.

- **Response `200 OK`**:
```json
{
  "totalScans": 10,
  "completedScans": 8,
  "failedScans": 1,
  "activeScans": 1,
  "totalRecordsExtracted": 500
}
```

**Curl Example**:
```bash
curl -X GET http://localhost:5200/api/stats
```

---

### 3. Results Querying Endpoints

#### `GET /api/results/{scan_id}/tables`
Lists available tables extracted for the given scan ID.

- **Path Parameters**: `scan_id` (string)
- **Response `200 OK`**:
```json
{
  "scanId": "deals-test-001",
  "organizationId": "test-portal",
  "schema": "hubspot_deals_test_portal",
  "tables": ["hubspot_deals", "_dlt_loads", "_dlt_version", "_dlt_pipeline_state"]
}
```

**Curl Example**:
```bash
curl -X GET http://localhost:5200/api/results/deals-test-001/tables
```

---

#### `GET /api/results/{scan_id}/result`
Fetches paginated deal records loaded into PostgreSQL for a scan.

- **Path Parameters**: `scan_id` (string)
- **Query Parameters**:
  - `table_name` (string, default: `hubspot_deals`)
  - `page` (int, default: 1)
  - `limit` (int, default: 100, max: 1000)
- **Response `200 OK`**:
```json
{
  "scanId": "deals-test-001",
  "tableName": "hubspot_deals",
  "page": 1,
  "limit": 100,
  "totalRecords": 5,
  "data": [
    {
      "id": "123456789",
      "dealname": "Globex Onboarding Project",
      "amount": 25000.0,
      "dealstage": "presentationscheduled",
      "pipeline": "default",
      "closedate": "2026-11-15T00:00:00Z",
      "_tenant_id": "test-portal",
      "_scan_id": "deals-test-001"
    }
  ]
}
```

**Curl Example**:
```bash
curl -X GET "http://localhost:5200/api/results/deals-test-001/result?limit=50"
```

---

### 4. Maintenance & Pipeline Info Endpoints

#### `GET /api/pipeline/info`
Returns DLT pipeline info.

- **Response `200 OK`**:
```json
{
  "pipelineName": "hubspot_deals_pipeline_dev",
  "workingDirectory": ".dlt",
  "datasetPrefix": "hubspot_deals"
}
```

---

#### `POST /api/maintenance/cleanup`
Cleans up expired scans and temporary DLT directories older than retention threshold (`CLEANUP_DAYS`).

- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Cleanup completed",
  "cleanedScansCount": 2
}
```

---

#### `POST /api/maintenance/detect-crashed`
Identifies jobs stuck in `running` or `resuming` state after service restart and marks them `crashed`.

- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Crashed scan detection completed",
  "crashedScansCount": 0
}
```

---

## ⚠️ Error Response Format & Codes

All API errors return standard JSON payloads:

```json
{
  "success": false,
  "message": "Detailed error message",
  "error": "ERROR_CODE"
}
```

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| `400` | `BAD_REQUEST` | Validation error in parameters or payload |
| `404` | `NOT_FOUND` | Scan ID or table not found |
| `409` | `CONFLICT` | Scan ID already exists or job not in valid state for action |
| `500` | `INTERNAL_ERROR` | Server exception |