import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.hubspot_api_service import HubSpotAPIService

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
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_env_file(os.path.join(project_root, ".env"))

    access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print("FAIL: HUBSPOT_ACCESS_TOKEN not found")
        sys.exit(1)

    api_service = HubSpotAPIService()
    props = api_service.get_deal_properties(access_token)

    output_path = os.path.join(project_root, "test-results", "deal-properties.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2)

    print(f"Successfully saved {len(props)} deal properties to {output_path}")

if __name__ == "__main__":
    main()
