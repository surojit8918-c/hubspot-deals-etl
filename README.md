# 🚀 HubSpot Deals Extraction Service (`hubspot_deals`)

A production-ready data extraction and load pipeline built with **Flask**, **DLT (Data Load Tool)**, and **PostgreSQL**. The service extracts deal records from the **HubSpot CRM API v3**, transforms nested property payloads into strongly typed tabular formats, and loads them into PostgreSQL datasets organized per tenant.

---

## 🏗️ Architecture

```
                                  ┌───────────────────────────┐
                                  │   HubSpot CRM API v3      │
                                  │ (/crm/v3/objects/deals)   │
                                  └─────────────▲─────────────┘
                                                │ HTTPS Bearer Token
                                                │ (Rate Limited 150/10s)
 ┌────────────────────────┐       ┌─────────────┴─────────────┐
 │  Client / System API   │       │                           │
 │ (REST API / Swagger UI)├──────►│   Flask REST API Service  │
 └────────────────────────┘       │   (Port 5200 / Port 5201) │
                                  │                           │
                                  └─────────────┬─────────────┘
                                                │ Async DLT Pipeline
                                                │ (Merge Disposition)
                                  ┌─────────────▼─────────────┐
                                  │   PostgreSQL Database     │
                                  │ (Schema: hubspot_deals_*) │
                                  └───────────────────────────┘
```

---

## 📋 Features

- **Multi-Tenant Isolation**: Automatically creates dedicated PostgreSQL schemas per tenant (`hubspot_deals_<organization_id>`) with `_tenant_id` defense-in-depth columns.
- **Resilient API Client**: Thread-safe sliding-window rate limiter (150 requests/10s), exponential backoff with jitter for 5xx/network errors, and `Retry-After` header parsing on HTTP 429.
- **Checkpointing & Interruption Recovery**: Periodically saves cursor progress and page state so paused or interrupted extraction jobs resume seamlessly without duplicating or wiping data (`write_disposition="merge"`).
- **Security & Secret Protection**: Access tokens are masked in logs (e.g. `pat-****`), stored encrypted in local state tables, and never exposed via API outputs or committed files.

---

## 🛠️ Prerequisites

- **Python 3.10+** (Python 3.12 supported)
- **Docker & Docker Compose** (for containerized PostgreSQL and app execution)
- **HubSpot Developer Test Account** with Private App scope `crm.objects.deals.read`

---

## ⚡ Quick Setup Guide

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and add your HubSpot Private App access token:

```bash
cp .env.example .env
```

Edit `.env`:
```env
HUBSPOT_ACCESS_TOKEN=pat-na1-your-actual-private-app-token
CONFIG_PASSWORD=a-long-random-secret-at-least-32-chars
```

> ⚠️ **Security Warning**: Never commit `.env` or share your access token. The `.gitignore` file is configured to exclude `.env`.

`CONFIG_PASSWORD` encrypts the access token stored for each scan. Set it to your own long random value and never commit it. Generate one:

```powershell
# PowerShell
-join ((48..57 + 65..90 + 97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
```
```bash
# Linux / macOS
openssl rand -base64 36
```

If it is empty or left at the default, the service warns in development and refuses to start in staging/production.
### 2. Run with Docker Compose

Start the PostgreSQL database and Flask extraction service:

```bash
docker compose up -d --build
```

Verify container status:
```bash
docker compose ps
```

The service will be accessible at:
- **API Base URL**: `http://localhost:5200`
- **Swagger Documentation**: `http://localhost:5200/docs/`
- **Health Check**: `http://localhost:5200/health` or `http://localhost:5200/api/health`

---

## 🔑 HubSpot Access Token Setup

1. Log into your [HubSpot Developer Account](https://developers.hubspot.com/).
2. Create or navigate to your **Test Account**.
3. Go to **Settings (gear icon) → Integrations → Private Apps**.
4. Click **Create a private app** and name it `DLT Deals Extractor`.
5. Under **Scopes**, enable `crm.objects.deals.read`.
6. Save the app, copy the Access Token, and paste it into `.env` as `HUBSPOT_ACCESS_TOKEN`.

---

## 📖 API Usage & Example Requests

### 1. Check Service Health

```bash
curl -X GET http://localhost:5200/health
```

### 2. Start Extraction Scan

```bash
curl -X POST http://localhost:5200/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "scanId": "deals-scan-001",
      "organizationId": "test-portal",
      "type": ["deal"],
      "auth": {
        "accessToken": "pat-na1-xxxx-xxxx-xxxx"
      },
      "filters": {
        "includeArchived": false,
        "properties": ["dealname", "amount", "dealstage", "pipeline", "closedate"]
      }
    }
  }'
```

### 3. Check Scan Status

```bash
curl -X GET http://localhost:5200/api/scan/deals-scan-001/status
```

### 4. Pause a Running Scan

```bash
curl -X POST http://localhost:5200/api/scan/deals-scan-001/pause
```

### 5. Resume a Paused Scan

```bash
curl -X POST http://localhost:5200/api/scan/deals-scan-001/resume
```

### 6. Get Extracted Results

```bash
curl -X GET "http://localhost:5200/api/results/deals-scan-001/result?tableName=hubspot_deals&limit=10"
```

---

## 🧪 Testing & Verification

### Running Unit Tests (Pytest)

```bash
pytest tests/ -v
```

### Running Live API Check (No Docker required)

Validates token credentials and live pagination directly against HubSpot API:

```bash
python scripts/live_api_check.py
```

### Running Full E2E Verification Script

```bash
# Test local running service
python scripts/e2e_test.py

# Run in static/no-docker mode
python scripts/e2e_test.py --no-docker
```

---

### Checkpoint / pause-resume test (test-only override)
`docker-compose.checkpoint.yml` slows the dev service down (page size 1, 6 s delay per page, checkpoint every 2 pages) so a scan can be paused in the middle. It is not part of the default setup. Use it only for the pause/resume test:

```powershell
docker compose -f docker-compose.yml -f docker-compose.checkpoint.yml up -d --build
```

Switch back to the normal setup with `docker compose up -d --build`. Real results of these tests are in `test-results/README.md`.
## 🔧 Troubleshooting

| Symptom / Error | Cause | Resolution |
|---|---|---|
| `HTTP 401 Unauthorized` | Invalid, expired, or truncated access token | Check `.env` and verify token in HubSpot Private App settings. |
| `HTTP 403 Forbidden` | Missing scope `crm.objects.deals.read` | Add `crm.objects.deals.read` scope in HubSpot Private App scopes. |
| `HTTP 429 Too Many Requests` | Exceeded HubSpot rate limit | Service auto-retries with `Retry-After`. Ensure `HUBSPOT_API_RATE_LIMIT=150`. |
| `PostgreSQL connection error` | Postgres container not ready | Verify `docker compose ps` and wait 10s for healthcheck completion. |
| `Port 5200 already in use` | Another process using port 5200 | Change `PORT` in `.env` or stop conflicting process. |

---

## 📚 Technical Documentation Links

- 📋 [**API Integration Guide**](docs/api-integration.md): Endpoint specifications, rate limits, error mapping, and deal property definitions.
- 🗄️ [**Database Schema Design**](docs/database-schema.md): DLT PostgreSQL architecture, `CREATE TABLE` DDL, indexing strategy, and multi-tenant isolation.
- 📑 [**REST API Documentation**](docs/api-documentation.md): OpenAPI endpoint catalogue, JSON request/response schemas, and example flows.
