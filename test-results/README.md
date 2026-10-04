# 📊 E2E Test Results Summary

| Test Name | Status | Details |
|---|---|---|
| Health Check Endpoint | **FAIL** | Connection failed to http://localhost:5200: HTTPConnectionPool(host='localhost', port=5200): Max retries exceeded with url: /health (Caused by NewConnectionError("HTTPConnection(host='localhost', port=5200): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
| Swagger API Docs UI | **FAIL** | Failed to reach /docs/: HTTPConnectionPool(host='localhost', port=5200): Max retries exceeded with url: /docs/ (Caused by NewConnectionError("HTTPConnection(host='localhost', port=5200): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
