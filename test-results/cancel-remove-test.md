# Cancel / Remove Test (real run)

Date: 2026-10-05. Service: hubspot_deals_service_dev with docker-compose.checkpoint.yml override
(HUBSPOT_PAGE_SIZE=1, HUBSPOT_TEST_DELAY_SECONDS=6, so the scan is slow enough to cancel).
Scan id: deals-test-004, organizationId: cancel-test (separate org so test-portal data is untouched).

## 1. Start
POST /api/scan/start -> success: true (accepted, runs in background).

## 2. Cancel (after ~10s)
POST /api/scan/deals-test-004/cancel -> success: true, status: cancelled, message "Job cancelled successfully".

## 3. Status 10s after cancel
status = cancelled, endTime = 2026-10-05T17:19:09Z (job stayed cancelled, did not turn into completed).

## 4. Remove
DELETE /api/scan/deals-test-004/remove -> success: true, tablesRemoved: 0, metadataRemoved: true.
tablesRemoved is 0 because the scan was cancelled before any data table was loaded.

## 5. After remove
GET /api/scan/deals-test-004/status -> HTTP 404
GET /api/results/deals-test-004/tables -> HTTP 404

## Result
PASS: cancel stops the job and keeps status cancelled, remove deletes the job metadata, removed scan returns 404.
