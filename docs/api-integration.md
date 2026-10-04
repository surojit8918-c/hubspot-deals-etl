# 📋 HubSpot Deals ETL Service - Integration with HubSpot CRM API

This document details the HubSpot CRM REST API v3 integration used by the `hubspot_deals` extraction service to retrieve Deals object data from HubSpot instances.

---

## 📋 Overview

The `hubspot_deals` ETL service integrates with the HubSpot CRM API v3 to extract deal records. The primary object type processed is **Deals**.

### ✅ Required Endpoint (Essential)
| **API Endpoint** | **Purpose** | **Version** | **Required Scope** | **Usage** |
|------------------|-------------|-------------|--------------------|-----------|
| `/crm/v3/objects/deals` | Search and list deals records with pagination and property filtering | v3 | `crm.objects.deals.read` | **Required** |

### 🔧 Optional Endpoint (Metadata & Properties)
| **API Endpoint** | **Purpose** | **Version** | **Required Scope** | **Usage** |
|------------------|-------------|-------------|--------------------|-----------|
| `/crm/v3/properties/deals` | Retrieve metadata definition for standard and custom deal properties | v3 | `crm.objects.deals.read` | Optional / Verification |

---

## 🔐 Authentication Requirements

### **Bearer Token Authentication**
HubSpot CRM API v3 uses Private App access tokens for authentication. Each HTTP request sent to HubSpot includes the token in the `Authorization` header:

```http
Authorization: Bearer pat-na1-xxxx-xxxx-xxxx
Content-Type: application/json
```

### **Required Permissions / Scopes**
- **`crm.objects.deals.read`**: Provides read-only access to CRM deals data.

### **Private App Setup Guide**
1. Log into your HubSpot account (or Developer Test Account).
2. Go to **Settings (gear icon) → Integrations → Private Apps**.
3. Click **Create a private app**.
4. Set the app name (e.g., `DLT Deals Extractor`).
5. Under **Scopes**, grant `crm.objects.deals.read`.
6. Click **Create app** and copy the generated Access Token (`pat-...`).
7. Store the token strictly in local `.env` as `HUBSPOT_ACCESS_TOKEN=...`. **Never commit or log the raw token.**

---

## 🌐 HubSpot API Endpoints & Request Structure

### 1. **Get Deals** - `/crm/v3/objects/deals` ✅ **REQUIRED**

**Purpose**: Get paginated deals records from HubSpot CRM.

**Method**: `GET`  
**URL**: `https://api.hubapi.com/crm/v3/objects/deals`

**Query Parameters**:
- `limit` (integer, 1..100): Number of records per page (default: 100).
- `after` (string, optional): Paging cursor token for fetching the next page.
- `properties` (string, optional): Comma-separated list of deal property names to return.
- `archived` (boolean, optional): Whether to return archived deals (`true` / `false`, default: `false`).

**Request Example**:
```http
GET https://api.hubapi.com/crm/v3/objects/deals?limit=100&properties=dealname,amount,dealstage,pipeline,closedate,createdate,hs_lastmodifieddate&archived=false
Authorization: Bearer pat-na1-xxxx-xxxx-xxxx
Content-Type: application/json
```

**Response Structure** (Realistic Sample JSON based on extraction data):
```json
{
  "results": [
    {
      "id": "123456789",
      "properties": {
        "amount": "25000",
        "closedate": "2026-11-15T00:00:00.000Z",
        "createdate": "2026-10-04T09:30:00.000Z",
        "dealname": "Globex Onboarding Project",
        "dealstage": "presentationscheduled",
        "hs_lastmodifieddate": "2026-10-04T09:35:00.000Z",
        "hs_object_id": "123456789",
        "pipeline": "default"
      },
      "createdAt": "2026-10-04T09:30:00.000Z",
      "updatedAt": "2026-10-04T09:35:00.000Z",
      "archived": false
    },
    {
      "id": "987654321",
      "properties": {
        "amount": "50000",
        "closedate": "2026-09-24T00:00:00.000Z",
        "createdate": "2026-09-01T12:00:00.000Z",
        "dealname": "Initech Annual License",
        "dealstage": "closedwon",
        "hs_lastmodifieddate": "2026-09-24T14:20:00.000Z",
        "hs_object_id": "987654321",
        "pipeline": "default"
      },
      "createdAt": "2026-09-01T12:00:00.000Z",
      "updatedAt": "2026-09-24T14:20:00.000Z",
      "archived": false
    }
  ],
  "paging": {
    "next": {
      "after": "NTI1Cg%3D%3D",
      "link": "https://api.hubapi.com/crm/v3/objects/deals?after=NTI1Cg%3D%3D"
    }
  }
}
```

> **Note**: In HubSpot API responses, all property values are returned as **strings** (including numeric amounts, dates, and booleans). The final page of results omits the `paging` dictionary.

---

## ⚡ Rate Limits & Resiliency Strategy

### **HubSpot Rate Limits**
- **Burst Limit**: 150 requests per 10 seconds per Private App / API key.
- **Daily Limit**: 250,000 requests per 24-hour period (varies by tier).
- **Rate Limit Response**: HTTP Status `429 Too Many Requests` with a `Retry-After` header indicating seconds to wait.

### **Service Resiliency Strategy**
1. **Thread-Safe Sliding-Window Limiter**: Pre-emptively throttles requests client-side to keep frequency <= 150 requests per 10 seconds.
2. **`Retry-After` Respect**: If HTTP `429` is returned, the client parses the `Retry-After` header (defaulting to 10s if missing) and sleeps before retrying.
3. **Exponential Backoff with Jitter**: Handles transient network glitches and HTTP `5xx` server errors up to `max_retries` (default: 3).

---

## 🚨 Error Handling & Job Status Mapping

| HTTP Status | Error Type | Service Handling | Job Status Result | Saved Error Message |
|-------------|------------|------------------|-------------------|----------------------|
| `400 Bad Request` | Malformed parameters / invalid properties | Fail fast, no retry | `failed` | `HubSpot API 400 Bad Request: <details>` |
| `401 Unauthorized` | Missing, invalid, or expired access token | Fail fast, no retry | `failed` | `HubSpot Auth Error (401): Invalid or expired access token` |
| `403 Forbidden` | Missing required scope `crm.objects.deals.read` | Fail fast, no retry | `failed` | `HubSpot Auth Error (403): Missing required scope crm.objects.deals.read` |
| `404 Not Found` | Requested deal or endpoint does not exist | Fail fast, no retry | `failed` | `HubSpot API 404 Not Found` |
| `429 Too Many Requests` | Rate limit exceeded | Wait `Retry-After` seconds, retry up to N times | `failed` (if retries exhausted) | `HubSpot Rate Limit Exceeded (429) after N retries` |
| `5xx / Timeout` | HubSpot server error or network issue | Exponential backoff retry | `failed` (if retries exhausted) | `HubSpot Server Error (5xx/Timeout): <details>` |

---

## 📋 Available Deal Properties

The following standard deal properties were verified against the live HubSpot CRM API `GET /crm/v3/properties/deals` endpoint (recorded in `test-results/deal-properties.json`, total 207 available properties). Stage IDs correspond to internal IDs in the default Sales Pipeline:

| Internal Property Name | Display Label | Type | Description |
|------------------------|---------------|------|-------------|
| `amount` | Amount | number | Total value of the deal |
| `amount_in_home_currency` | Amount in Home Currency | number | Converted total value |
| `closed_lost_reason` | Closed Lost Reason | string | Reason why deal was lost |
| `closed_won_reason` | Closed Won Reason | string | Reason why deal was won |
| `closedate` | Close Date | datetime | Expected or actual close date |
| `createdate` | Create Date | datetime | Date the deal was created |
| `days_to_close` | Days to Close | number | Calculated days between creation and close |
| `dealname` | Deal Name | string | Name of the deal record |
| `dealstage` | Deal Stage | enumeration | Stage internal ID (e.g. `qualifiedtobuy`, `presentationscheduled`, `contractsent`, `closedwon`, `closedlost`) |
| `dealtype` | Deal Type | enumeration | Type of deal (`newbusiness` or `existingbusiness`) |
| `description` | Description | string | Detailed deal description |
| `hs_acv` | Annual Contract Value | number | Annual contract value |
| `hs_arr` | Annual Recurring Revenue | number | Annual recurring revenue |
| `hs_closed_amount` | Closed Amount | number | Amount when deal was closed |
| `hs_deal_stage_probability` | Stage Probability | number | Probability percentage associated with stage |
| `hs_forecast_amount` | Forecast Amount | number | Revenue forecast amount |
| `hs_forecast_probability` | Forecast Probability | number | Forecast probability percentage |
| `hs_is_closed` | Is Closed | bool | `true` if deal stage is closed won or closed lost |
| `hs_is_closed_won` | Is Closed Won | bool | `true` if deal stage is closed won |
| `hs_lastmodifieddate` | Last Modified Date | datetime | Timestamp when deal was last modified |
| `hs_mrr` | Monthly Recurring Revenue | number | Monthly recurring revenue |
| `hs_next_step` | Next Step | string | Next planned sales activity |
| `hs_object_id` | Object ID | string | Unique record ID in HubSpot |
| `hs_priority` | Priority | enumeration | Deal priority level |
| `hs_tcv` | Total Contract Value | number | Total contract value |
| `hubspot_owner_id` | Owner ID | string | ID of assigned HubSpot owner |
| `hubspot_team_id` | Team ID | string | ID of assigned HubSpot team |
| `notes_last_contacted` | Last Contacted Date | datetime | Timestamp of last contact |
| `notes_last_updated` | Last Updated Notes Date | datetime | Timestamp when notes were last updated |
| `notes_next_activity_date` | Next Activity Date | datetime | Scheduled next activity date |
| `num_associated_contacts` | Number of Associated Contacts | number | Count of linked contact records |
| `num_contacted_notes` | Number of Contacted Notes | number | Count of contact notes |
| `num_notes` | Number of Notes | number | Total note count |
| `pipeline` | Pipeline | string | ID of sales pipeline (default: `default`) |

### Standard Sales Pipeline Stage IDs
- `appointmentscheduled`: Appointment Scheduled
- `qualifiedtobuy`: Qualified To Buy
- `presentationscheduled`: Presentation Scheduled
- `decisionmakerboughtin`: Decision Maker Bought-In
- `contractsent`: Contract Sent
- `closedwon`: Closed Won
- `closedlost`: Closed Lost

---

## 📥 Default Extracted Deal Properties

By default, the service requests and extracts the following core set of 14 deal properties if no specific `properties` filter is provided:

1. `dealname`
2. `amount`
3. `dealstage`
4. `pipeline`
5. `closedate`
6. `createdate`
7. `hs_lastmodifieddate`
8. `description`
9. `dealtype`
10. `hubspot_owner_id`
11. `hs_priority`
12. `hs_is_closed`
13. `hs_is_closed_won`
14. `hs_object_id`