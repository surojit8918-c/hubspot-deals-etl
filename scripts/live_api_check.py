import os
import sys
import re
import logging
from decimal import Decimal

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.hubspot_api_service import HubSpotAPIService, mask_token
from services.data_source import transform_deal, get_logger

# Helper to load .env file manually without printing token
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
    output_lines = []
    def print_log(msg: str):
        print(msg)
        output_lines.append(msg)

    print_log("=== HubSpot Live API Check ===")
    
    # Load .env from project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_file = os.path.join(project_root, ".env")
    load_env_file(env_file)

    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print_log("FAIL: HUBSPOT_ACCESS_TOKEN not set in environment or .env")
        sys.exit(1)

    masked_tok = mask_token(access_token)
    print_log(f"Token loaded: {masked_tok}")

    api_service = HubSpotAPIService()

    # Step 1a: Validate credentials
    print_log("\n--- Step 1a: Validate Credentials ---")
    val_res = api_service.validate_credentials(access_token)
    if val_res.get("valid"):
        print_log(f"PASS: Credentials valid (HTTP {val_res.get('status_code')})")
    else:
        print_log(f"FAIL: Credentials invalid: {val_res.get('error')}")
        sys.exit(1)

    default_props = [
        "dealname", "amount", "dealstage", "pipeline", "closedate",
        "createdate", "hs_lastmodifieddate", "description", "dealtype",
        "hubspot_owner_id", "hs_priority", "hs_is_closed", "hs_is_closed_won"
    ]

    # Step 1b & 1c: Fetch all deals and transform
    print_log("\n--- Step 1b & 1c: Fetch All Deals & Transform ---")
    logger = get_logger("live_api_check")
    fetched_records = []
    
    for page in api_service.iter_deals(access_token, limit=100, properties=default_props):
        for raw_record in page.get("results", []):
            transformed = transform_deal(raw_record, default_props, logger)
            fetched_records.append(transformed)

    print_log(f"Fetched {len(fetched_records)} deals in total.")

    # Step 1d: Compare with expected deals from deal-ids.md
    print_log("\n--- Step 1d: Verification Against Expected Test Deals ---")
    expected_deals = {
        "352118192850": {"name": "Acme Starter Package", "amount": Decimal("5000"), "stage": "qualifiedtobuy"},
        "352552945365": {"name": "Globex Onboarding Project", "amount": Decimal("25000"), "stage": "presentationscheduled"},
        "352552945389": {"name": "Initech Annual License", "amount": Decimal("50000"), "stage": "closedwon"},
        "352125385452": {"name": "Umbrella Pilot Program", "amount": Decimal("75000"), "stage": "closedlost"},
        "352125385456": {"name": "Hooli Enterprise Suite", "amount": Decimal("100000"), "stage": "contractsent"},
    }

    records_by_id = {r["id"]: r for r in fetched_records}

    all_passed = True
    for expected_id, exp in expected_deals.items():
        if expected_id not in records_by_id:
            print_log(f"FAIL: Deal ID {expected_id} ('{exp['name']}') missing from fetched records")
            all_passed = False
            continue

        rec = records_by_id[expected_id]
        name_match = (rec.get("dealname") == exp["name"])
        amt_match = (rec.get("amount") == exp["amount"])
        stage_match = (rec.get("dealstage") == exp["stage"])

        if name_match and amt_match and stage_match:
            print_log(f"PASS: Deal ID {expected_id} | Name: '{rec.get('dealname')}' | Amount: ${rec.get('amount')} | Stage: '{rec.get('dealstage')}'")
        else:
            print_log(f"FAIL: Deal ID {expected_id} mismatch! Got Name: '{rec.get('dealname')}', Amount: ${rec.get('amount')}, Stage: '{rec.get('dealstage')}'")
            all_passed = False

    # Step 1e: Pagination verification with page size 2
    print_log("\n--- Step 1e: Pagination Verification (page_size=2) ---")
    page_count = 0
    paged_deal_ids = []
    
    for page in api_service.iter_deals(access_token, limit=2, properties=default_props):
        page_count += 1
        page_ids = [r["id"] for r in page.get("results", [])]
        paged_deal_ids.extend(page_ids)
        next_after = page.get("paging", {}).get("next", {}).get("after", "None")
        print_log(f"Page {page_count}: count={len(page_ids)}, deal_ids={page_ids}, next_after='{next_after}'")

    if page_count > 1 and len(paged_deal_ids) == len(fetched_records):
        print_log(f"PASS: Multi-page cursor pagination successful ({page_count} pages fetched for {len(paged_deal_ids)} records)")
    else:
        print_log(f"FAIL: Pagination issue! Page count: {page_count}, total paged IDs: {len(paged_deal_ids)}")
        all_passed = False

    print_log("\n=== Final Status ===")
    if all_passed:
        print_log("ALL CHECKS PASSED")
    else:
        print_log("SOME CHECKS FAILED")
        sys.exit(1)

    # Save token-free output to test-results/live-api-check.txt
    test_results_dir = os.path.join(project_root, "test-results")
    os.makedirs(test_results_dir, exist_ok=True)
    output_path = os.path.join(test_results_dir, "live-api-check.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"\nSaved live API check output to {output_path}")

if __name__ == "__main__":
    main()
