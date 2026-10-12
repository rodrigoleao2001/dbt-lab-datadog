#!/usr/bin/env python3
"""
Replicate the exact API call the Datadog dbt Cloud crawler makes
(metrics_client.py lines 419-425) to verify whether the `environment`
object is returned in the runs response.

Usage:
    export DBT_TOKEN="your-service-token"
    export DBT_ACCOUNT_ID="your-account-id"
    python3 scripts/test_environment_tag.py

Optional:
    export DBT_ACCOUNT_URL="https://cloud.getdbt.com"  (default)
"""
import json
import os
import sys

import requests

ACCOUNT_URL = os.environ.get("DBT_ACCOUNT_URL", "https://cloud.getdbt.com")
ACCOUNT_ID = os.environ.get("DBT_ACCOUNT_ID")
TOKEN = os.environ.get("DBT_TOKEN")

if not ACCOUNT_ID or not TOKEN:
    print("ERROR: Set DBT_ACCOUNT_ID and DBT_TOKEN environment variables")
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Datadog/1.0",
    "X-dbt-partner-source": "Datadog",
    "Authorization": f"Token {TOKEN}",
})

# --- Test 1: Runs endpoint with include_related (same as crawler line 419-425) ---
print("=" * 60)
print("TEST 1: GET /api/v2/accounts/{id}/runs/ with include_related")
print("  This is the exact call the crawler makes.")
print("=" * 60)

url = f"{ACCOUNT_URL}/api/v2/accounts/{ACCOUNT_ID}/runs/"
params = {
    "limit": 3,
    "offset": 0,
    "order_by": "-finished_at",
    "include_related": "trigger,job,environment",
    "status": 10,  # Success
}

resp = session.get(url, params=params)
resp.raise_for_status()
data = resp.json()

runs = data.get("data") or []
if not runs:
    print("\n  No finished runs found. Run a dbt job first.")
    sys.exit(1)

print(f"\n  Found {len(runs)} run(s). Checking environment field:\n")

for run in runs:
    run_id = run.get("id")
    job_name = (run.get("job") or {}).get("name", "unknown")
    env_obj = run.get("environment")
    env_name = (env_obj or {}).get("name") if env_obj else None

    print(f"  Run {run_id} (job: {job_name}):")
    print(f"    run['environment'] present: {env_obj is not None}")
    print(f"    run['environment']['name']: {env_name}")

    if env_name:
        print(f"    -> Tag would be: environment:{env_name}")
    else:
        print(f"    -> TAG WOULD BE MISSING (this is the bug)")
    print()

# --- Test 2: Environments endpoint directly ---
print("=" * 60)
print("TEST 2: GET /api/v3/accounts/{id}/environments/")
print("  This is how the Discovery API gets env names.")
print("=" * 60)

env_url = f"{ACCOUNT_URL}/api/v3/accounts/{ACCOUNT_ID}/environments/"
resp2 = session.get(env_url, params={"limit": 100})
resp2.raise_for_status()
env_data = resp2.json()

envs = env_data.get("data") or []
print(f"\n  Found {len(envs)} environment(s):\n")

for env in envs:
    env_id = env.get("id")
    env_name = env.get("name")
    env_type = env.get("type") or env.get("dbt_version", "unknown")
    print(f"  ID: {env_id}, name: {env_name}, type: {env_type}")

print()

# --- Raw JSON dump for evidence ---
print("=" * 60)
print("RAW EVIDENCE: First run's full environment object")
print("=" * 60)
if runs:
    print(json.dumps(runs[0].get("environment"), indent=2, default=str))
