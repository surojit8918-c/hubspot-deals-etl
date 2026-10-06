# Checkpoint / Pause / Resume Test (real run)

Date: 2026-10-05. Service: hubspot_deals_service_dev with docker-compose.checkpoint.yml override
(HUBSPOT_PAGE_SIZE=1, HUBSPOT_TEST_DELAY_SECONDS=6, CHECKPOINT_EVERY_N_PAGES=2). Scan id: deals-test-003, org: test-portal.

## 1. Start
POST /api/scan/start -> success: true (accepted, runs in background).

## 2. Pause (after ~28s)
POST /api/scan/deals-test-003/pause -> previousStatus running, currentStatus paused,
progress: recordsProcessed 2, currentPage 2.

Status right after pause: status = paused, config keys = filters, type (no auth field).
Checkpoint: cursor 352125385453, pageNumber 2, recordsProcessed 2, batchSize 1.

The in-flight page finished and was checkpointed, then the job stopped (pause works at page boundaries).
Re-checked 20s and 35s later: status still paused, endTime empty, checkpoint stable at
cursor 352125385457, pageNumber 3, recordsProcessed 3.
(Previous bug: pause ended as "completed" with pageNumber 0 and cursor null. Fixed.)

## 3. Service restart
docker compose restart hubspot_deals_service_dev -> health ok.
After restart: status still paused, checkpoint unchanged (cursor 352125385457, page 3, 3 records),
so the checkpoint is persisted in the database, not in memory.

## 4. Resume
POST /api/scan/deals-test-003/resume -> previousStatus paused, currentStatus resuming,
resumePoint: page 3, recordsProcessed 3, cursor 352125385457.

Log evidence (resume part):
- 17:12:16 Job resumed successfully (resume_page 3, records_processed 3)
- 17:12:16 Resuming from checkpoint (resume_page 3)
- 17:12:24 Resuming data extraction (page_number 4, total_processed 3, cursor 352125385457)
- 17:12:24 Fetching deals page 4 (cursor 352125385457)
- 17:12:31 Checkpoint saved (page 4)
- 17:12:31 Fetching deals page 5 (cursor 352552945366)
- 17:12:38 Checkpoint saved (page 5)
- 17:12:38 Data extraction completed (total_records 5, total_pages 5)

Only pages 4 and 5 were fetched after resume; pages 1-3 were not fetched again.
Final job status: completed, recordsExtracted 5.

## 5. Database check
SELECT count(*) AS total, count(DISTINCT id) AS uniq FROM hubspot_deals_test_portal.hubspot_deals;
total = 5, uniq = 5

## Known note
While a job is paused, recordsExtracted in /status shows 0 and the real progress is in
checkpointInfo.latestCheckpoint.recordsProcessed. After completion recordsExtracted is correct (5).

## Result
PASS: pause keeps status paused, checkpoint survives a service restart, resume continues from the saved cursor, final data 5 unique deals.
