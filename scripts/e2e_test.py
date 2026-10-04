import os
import sys
import time
import json
import argparse
import requests
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def load_env_file(env_path: str = ".env"):
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

def main():
    parser = argparse.ArgumentParser(description="End-to-End ETL Service Verification Script")
    parser.add_argument("--base-url", default="http://localhost:5200", help="Base URL for service")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker/PostgreSQL execution steps")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_env_file(os.path.join(project_root, ".env"))

    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    results_dir = os.path.join(project_root, "test-results")
    os.makedirs(results_dir, exist_ok=True)

    print(f"=== HubSpot Deals ETL E2E Verification ===")
    print(f"Base URL: {args.base_url}")
    print(f"Docker Mode: {'Disabled (--no-docker)' if args.no_docker else 'Enabled'}")

    summary = []
    def log_result(name: str, passed: bool, details: str):
        status = "PASS" if passed else "FAIL"
        line = f"[{status}] {name}: {details}"
        print(line)
        summary.append({"name": name, "status": status, "details": details})

    # Test 1: Health checks
    try:
        r_root_health = requests.get(f"{args.base_url}/health", timeout=5)
        r_api_health = requests.get(f"{args.base_url}/api/health", timeout=5)
        
        health_ok = (r_root_health.status_code == 200 and r_api_health.status_code == 200)
        log_result("Health Check Endpoint", health_ok, f"GET /health: {r_root_health.status_code}, GET /api/health: {r_api_health.status_code}")

        with open(os.path.join(results_dir, "health-check.txt"), "w", encoding="utf-8") as f:
            f.write(f"/health status: {r_root_health.status_code}\nPayload: {r_root_health.text}\n\n")
            f.write(f"/api/health status: {r_api_health.status_code}\nPayload: {r_api_health.text}\n")
    except Exception as e:
        log_result("Health Check Endpoint", False, f"Connection failed to {args.base_url}: {str(e)}")

    # Test 2: Swagger Docs UI
    try:
        r_docs = requests.get(f"{args.base_url}/docs/", timeout=5)
        docs_ok = (r_docs.status_code == 200 and "<html" in r_docs.text.lower())
        log_result("Swagger API Docs UI", docs_ok, f"GET /docs/ HTTP {r_docs.status_code}")
        
        with open(os.path.join(results_dir, "api-docs.md"), "w", encoding="utf-8") as f:
            f.write(f"# API Documentation Verification\n\nSwagger UI endpoint `GET /docs/` returned HTTP status `{r_docs.status_code}` with interactive HTML documentation.\n")
    except Exception as e:
        log_result("Swagger API Docs UI", False, f"Failed to reach /docs/: {str(e)}")

    if args.no_docker:
        print("\nNote: Live HTTP scan execution & Postgres verification steps skipped due to --no-docker flag.")
    else:
        # Full live scan flow if service is running
        if not access_token:
            print("ERROR: HUBSPOT_ACCESS_TOKEN not set in environment or .env")
            sys.exit(1)

        scan_payload = {
            "config": {
                "scanId": "deals-test-001",
                "organizationId": "test-portal",
                "type": ["deal"],
                "auth": {"accessToken": access_token},
                "filters": {"includeArchived": False}
            }
        }

        try:
            r_start = requests.post(f"{args.base_url}/api/scan/start", json=scan_payload, timeout=10)
            start_ok = (r_start.status_code == 202)
            log_result("Start Scan Request", start_ok, f"POST /api/scan/start HTTP {r_start.status_code}")

            status_history = []
            if start_ok:
                scan_completed = False
                for _ in range(60):
                    time.sleep(2)
                    r_status = requests.get(f"{args.base_url}/api/scan/deals-test-001/status", timeout=5)
                    if r_status.status_code == 200:
                        st_data = r_status.json().get("data", {})
                        status_history.append(st_data)
                        curr_status = st_data.get("status")
                        if curr_status in ("completed", "failed", "cancelled"):
                            scan_completed = (curr_status == "completed")
                            break
                
                log_result("Scan Execution & Polling", scan_completed, f"Final status: {status_history[-1].get('status') if status_history else 'unknown'}")

                with open(os.path.join(results_dir, "scan-status.json"), "w", encoding="utf-8") as f:
                    json.dump(status_history, f, indent=2)

                # Fetch Results
                r_results = requests.get(f"{args.base_url}/api/results/deals-test-001/result?tableName=hubspot_deals", timeout=5)
                results_ok = (r_results.status_code == 200)
                log_result("Scan Results API", results_ok, f"GET /api/results/deals-test-001/result HTTP {r_results.status_code}")
                
                if results_ok:
                    with open(os.path.join(results_dir, "results.json"), "w", encoding="utf-8") as f:
                        json.dump(r_results.json(), f, indent=2)
        except Exception as e:
            log_result("Live Scan Flow", False, f"Execution failed: {str(e)}")

    # Write summary README in test-results
    with open(os.path.join(results_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("# 📊 E2E Test Results Summary\n\n")
        f.write("| Test Name | Status | Details |\n|---|---|---|\n")
        for item in summary:
            f.write(f"| {item['name']} | **{item['status']}** | {item['details']} |\n")

    print(f"\nWrote E2E test summary to {os.path.join(results_dir, 'README.md')}")

if __name__ == "__main__":
    main()
