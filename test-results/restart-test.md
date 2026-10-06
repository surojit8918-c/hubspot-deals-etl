# Restart Test (real run)

Date: 2026-10-06. Default setup only (docker compose up -d, WITHOUT the checkpoint override file).

## 1. Full stop and start
docker compose -f docker-compose.yml -f docker-compose.checkpoint.yml down   (containers and network removed, volumes kept)
docker compose up -d
After 25s: hubspot_deals_service_dev, hubspot_deals_postgres_dev, hubspot_deals_redis all "Up (healthy)".
GET /health -> ok. No CONFIG_PASSWORD warning during startup.

## 2. Data survived the restart
SELECT count(*) AS total, count(DISTINCT id) AS uniq FROM hubspot_deals_test_portal.hubspot_deals;
total = 5, uniq = 5 (Postgres volume kept the data).

## 3. Fresh scan after restart
POST /api/scan/start (scanId deals-test-005, organizationId test-portal) -> accepted.
Poll: 3s running, 6s completed, recordsExtracted = 5.
/status config keys = filters, type (no auth field).

## 4. Data after the new scan
total = 5, uniq = 5 (DLT merge on id, no duplicates after a second full load).

## Result
PASS: services come back healthy after down/up, data persists in the Postgres volume, a fresh scan works and still gives exactly 5 unique deals.
