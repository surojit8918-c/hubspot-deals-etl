# 🗄️ HubSpot Deals ETL Service - Database Schema Documentation

This document describes the PostgreSQL storage architecture, schema layout, type mapping, and multi-tenant isolation strategy for the `hubspot_deals` extraction service powered by DLT (Data Load Tool).

---

## 📋 Storage Model & Overview

The service utilizes PostgreSQL as the target data warehouse. Multi-tenant isolation is enforced using **PostgreSQL Schemas (DLT Datasets)** combined with row-level tenant markers.

### Storage Architecture
1. **Tenant Datasets (Schemas)**: Each organization/tenant gets an isolated PostgreSQL schema named `hubspot_deals_<organizationId_sanitized>` (hyphens replaced by underscores).
2. **Extraction Table**: Extracted deal records are loaded into `hubspot_deals_<tenant>.hubspot_deals`.
3. **DLT System Tables**: Created automatically by DLT inside each tenant schema:
   - `_dlt_loads`: Records load package statuses, completion times, and execution IDs.
   - `_dlt_version`: Manages schema migration history and version tracking.
   - `_dlt_pipeline_state`: Persists pipeline execution states across incremental runs.
4. **Service System Tables**: Reside in the default schema (e.g. `public` or `hubspot_deals_dev`):
   - `scan_jobs`: Tracks extraction job status, progress counters, configuration parameters, and errors.
   - `checkpoints`: Stores cursor tokens, page indices, and state checkpoints for job pause/resume capability.

---

## 🏗️ Table Schemas & Definitions

### 1. Service Internal Tables (`models/models.py`)

#### `scan_jobs` Table
Tracks extraction request lifecycle and progress counters.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | String(36) | PRIMARY KEY | Internal UUID for the job |
| `scan_id` | String(255) | UNIQUE, NOT NULL, INDEX | External scan identifier provided by caller |
| `status` | String(50) | NOT NULL, INDEX | Current state (`pending`, `running`, `completed`, `paused`, `failed`, `cancelled`, `crashed`, `resuming`) |
| `scan_type` | String(50) | NOT NULL | Service type (e.g., `hubspot_deals`) |
| `config` | JSON | NOT NULL | Complete scan configuration (request body JSON) |
| `organization_id` | String(255) | NOT NULL, INDEX | Tenant organization identifier |
| `error_message` | Text | NULLABLE | Exception traceback or failure details |
| `started_at` | DateTime | NULLABLE | Execution start timestamp |
| `completed_at` | DateTime | NULLABLE | Completion or termination timestamp |
| `total_items` | Integer | DEFAULT 0 | Estimated total items |
| `processed_items` | Integer | DEFAULT 0 | Records loaded into PostgreSQL |
| `failed_items` | Integer | DEFAULT 0 | Failed record count |
| `batch_size` | Integer | DEFAULT 100 | Page batch limit |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |
| `updated_at` | DateTime | NOT NULL | Record last update timestamp |

#### `checkpoints` Table
Stores paginated state checkpoints for resume support.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | String(36) | PRIMARY KEY | Internal UUID for the checkpoint |
| `scan_id` | String(255) | NOT NULL, INDEX | Foreign reference to `scan_jobs.scan_id` |
| `cursor` | Text | NULLABLE | HubSpot pagination token (`paging.next.after`) |
| `page_number` | Integer | NOT NULL | Page number for resume point |
| `processed_items` | Integer | NOT NULL | Cumulative item count at checkpoint |
| `created_at` | DateTime | NOT NULL | Checkpoint saved timestamp |

---

### 2. Tenant Extraction Table: `hubspot_deals`

The target schema for extracted HubSpot deals data in PostgreSQL.

#### Type Mapping (HubSpot CRM → PostgreSQL)
| HubSpot Type | Target PostgreSQL Type | Rationale |
|--------------|------------------------|-----------|
| String / ID | `TEXT` | Flexible text storage |
| Enumeration | `TEXT` | Stage/pipeline codes stored as string IDs |
| Number (Currency/Amount) | `NUMERIC(38,9)` | DLT default PostgreSQL decimal mapping ensuring precision |
| Datetime | `TIMESTAMPTZ` | Timezone-aware UTC timestamp parsing ISO 8601 (`Z`) |
| Date | `DATE` | Calendar dates |
| Boolean | `BOOLEAN` | Native boolean flags |
| Record ID | `TEXT` | HubSpot object record ID (Logical Primary Key for DLT `merge`) |
| System ID | `TEXT UNIQUE` | DLT internal record hash (`_dlt_id`) with UNIQUE constraint |

#### Target DDL Statement (`hubspot_deals_<tenant>.hubspot_deals`)

```sql
CREATE SCHEMA IF NOT EXISTS hubspot_deals_<tenant>;

CREATE TABLE hubspot_deals_<tenant>.hubspot_deals (
    id                    TEXT,                       -- HubSpot record object ID (Logical Primary Key for DLT merge)
    dealname              TEXT,                       -- Deal Name
    amount                NUMERIC(38,9),              -- Total deal value (DLT default numeric format)
    dealstage             TEXT,                       -- Stage internal code
    pipeline              TEXT,                       -- Pipeline ID (e.g. 'default')
    closedate             TIMESTAMPTZ,                -- Close date
    createdate            TIMESTAMPTZ,                -- HubSpot deal creation date
    hs_lastmodifieddate   TIMESTAMPTZ,                -- HubSpot last modified date
    description           TEXT,                       -- Deal description text
    dealtype              TEXT,                       -- 'newbusiness' or 'existingbusiness'
    hubspot_owner_id      TEXT,                       -- Assigned owner ID
    hs_priority           TEXT,                       -- Priority level
    hs_is_closed          BOOLEAN,                    -- Closed status flag
    hs_is_closed_won      BOOLEAN,                    -- Closed won flag
    created_at            TIMESTAMPTZ,                -- Top-level HubSpot createdAt
    updated_at            TIMESTAMPTZ,                -- Top-level HubSpot updatedAt
    archived              BOOLEAN DEFAULT FALSE,      -- Archived status flag
    _extracted_at         TIMESTAMPTZ NOT NULL,       -- ETL extraction timestamp (UTC)
    _scan_id              TEXT NOT NULL,              -- Extraction job scanId
    _tenant_id            TEXT NOT NULL,              -- Tenant organization ID
    _page_number          INTEGER,                    -- Page index during fetch
    _source_service       TEXT,                       -- Service tag ('hubspot_deals')
    _dlt_load_id          TEXT NOT NULL,              -- System load ID added by DLT
    _dlt_id               TEXT NOT NULL UNIQUE        -- Internal record hash added by DLT with UNIQUE constraint
);
```

> **Schema Evolution Note**: DLT automatically manages table creation and schema evolution. If custom properties are requested via `filters.properties`, DLT dynamically adds corresponding nullable columns to the PostgreSQL table without dropping existing data. Unrequested properties are not stored.

---

## 🛠️ ETL Metadata Fields

Every record loaded into PostgreSQL includes five standard ETL lineage fields:

| Field Name | Type | Description | Example Value |
|------------|------|-------------|---------------|
| `_extracted_at` | `TIMESTAMPTZ` | Timestamp when record was extracted | `2026-10-04 18:40:00+00` |
| `_scan_id` | `TEXT` | External scan identifier | `deals-test-001` |
| `_tenant_id` | `TEXT` | Tenant organization ID | `test-portal` |
| `_page_number` | `INTEGER` | Page number during extraction batch | `1` |
| `_source_service` | `TEXT` | Identifier of extracting service | `hubspot_deals` |

---

## ⚡ Write Disposition: `merge`

The service uses **DLT `merge` disposition** configured with `primary_key="id"` (HubSpot record ID).

### How DLT `merge` operates in PostgreSQL:
- DLT uses `id` as a **logical primary key** during staging and upsert execution.
- DLT automatically generates a `UNIQUE` constraint index on `_dlt_id` (`hubspot_deals__dlt_id_key`).
- **`replace`**: Overwrites the entire table on every run. If a job pauses halfway, resuming with `replace` would wipe previously extracted pages, resulting in total data loss.
- **`append`**: Inserts duplicate rows if a scan is restarted or resumed after a crash.
- **`merge`**: Performs an atomic **UPSERT** (`INSERT ... ON CONFLICT / DELETE+INSERT` using staging tables). If a job is resumed or re-run, existing deals are updated in place while new deals are inserted cleanly.

---

## 🔒 Multi-Tenant Isolation Strategy

1. **Schema Separation**: Each tenant's data lives in an isolated PostgreSQL schema: `hubspot_deals_<organizationId_sanitized>`.
2. **Row-Level Tenant Marker**: Defense-in-depth marker `_tenant_id` populated on every record from `organizationId`.
3. **Dataset Sanitization**: `organizationId` is sanitized (hyphens replaced with underscores) and validated against `^[a-zA-Z0-9_-]+$` to prevent SQL injection or cross-schema data leaks.
4. **Isolated Pipeline Working Directories**: DLT state directory is segmented per tenant pipeline run.

---

## ⚡ Performance Indexes & Rationale

DLT automatically creates a UNIQUE index on `_dlt_id`. Following a successful load, the service executes post-load `CREATE INDEX IF NOT EXISTS` statements to build performance indexes on top of the dataset table:

```sql
-- Single column index on tenant marker (defense in depth queries)
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_tenant ON hubspot_deals_<tenant>.hubspot_deals (_tenant_id);

-- Filter index for filtering deals by sales pipeline stage
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_stage ON hubspot_deals_<tenant>.hubspot_deals (dealstage);

-- Date range filtering indexes
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_closedate ON hubspot_deals_<tenant>.hubspot_deals (closedate);
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_createdate ON hubspot_deals_<tenant>.hubspot_deals (createdate);

-- Composite index for pipeline reporting (stage + close date)
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_stage_close ON hubspot_deals_<tenant>.hubspot_deals (dealstage, closedate);

-- Lineage index for scan level auditing
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_scan_id ON hubspot_deals_<tenant>.hubspot_deals (_scan_id);

-- Incremental load index for future delta extractions
CREATE INDEX IF NOT EXISTS idx_hubspot_deals_lastmodified ON hubspot_deals_<tenant>.hubspot_deals (hs_lastmodifieddate);
```

---

## 📊 Example Verification SQL Queries

### 1. Count deals by sales stage and calculate total revenue
```sql
SELECT 
    dealstage, 
    COUNT(*) AS total_deals, 
    SUM(amount) AS total_amount
FROM hubspot_deals_test_portal.hubspot_deals
GROUP BY dealstage
ORDER BY total_amount DESC;
```

### 2. Verify tenant isolation and scan lineage
```sql
SELECT 
    _scan_id, 
    _tenant_id, 
    COUNT(*) AS records_extracted, 
    MIN(_extracted_at) AS extraction_start, 
    MAX(_extracted_at) AS extraction_end
FROM hubspot_deals_test_portal.hubspot_deals
GROUP BY _scan_id, _tenant_id;
```

### 3. Retrieve all deals sorted by value
```sql
SELECT id, dealname, amount, dealstage, closedate, _tenant_id, _scan_id
FROM hubspot_deals_test_portal.hubspot_deals
ORDER BY amount DESC;
```