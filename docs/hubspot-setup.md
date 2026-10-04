# 📝 HubSpot Account & Private App Setup Record

This document records the HubSpot developer test account and private app setup details for the `hubspot_deals` extraction service.

> **Security Note**: This file contains NO access tokens or sensitive credentials. The Private App access token is stored strictly in the git-ignored local `.env` file as `HUBSPOT_ACCESS_TOKEN=...`.

---

## 👤 Account & Private App Details

- **Test Account Name**: `sarkarsurojit725@gmail.com`
- **HubSpot Portal (Hub) ID**: `247598766`
- **Private App Name**: `DLT Deals Extractor`
- **Required Scopes**: `crm.objects.deals.read`
- **Creation Date**: `2026-10-04`
- **Token Storage**: Stored in local `.env` as `HUBSPOT_ACCESS_TOKEN`, protected by `.gitignore` (not committed).

---

## 🎯 Setup Verification Checklist

- [ ] Developer Test Account created at https://developers.hubspot.com/
- [ ] Test Portal created inside the developer portal
- [ ] Private App created with scope `crm.objects.deals.read`
- [ ] Access Token generated and copied to `.env` file
- [ ] 5 Test Deals created in Sales Pipeline with specified values
