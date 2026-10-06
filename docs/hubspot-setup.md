# 📝 HubSpot Account & Private App Setup Record

This document records the HubSpot developer test account and private app setup details for the `hubspot_deals` extraction service.

> **Security Note**: This file contains NO access tokens or sensitive credentials. The Private App access token is stored strictly in the git-ignored local `.env` file as `HUBSPOT_ACCESS_TOKEN=...`.

---

## 👤 Account & Private App Details

- **Test Account Name**: `Developer test account 1`
- **HubSpot Portal (Hub) ID**: `247598766`
- **Private App Name**: `DLT Deals Extractor`
- **Required Scopes**: `crm.objects.deals.read`
- **Creation Date**: `2026-10-04`
- **Token Storage**: Stored in local `.env` as `HUBSPOT_ACCESS_TOKEN`, protected by `.gitignore` (not committed).

---

## 🎯 Setup Verification Checklist

- [x] Developer Test Account created at https://developers.hubspot.com/
- [x] Test Portal created inside the developer portal
- [x] Private App created with scope `crm.objects.deals.read`
- [x] Access Token generated and copied to `.env` file
- [x] 5 Test Deals created in Sales Pipeline with specified values
