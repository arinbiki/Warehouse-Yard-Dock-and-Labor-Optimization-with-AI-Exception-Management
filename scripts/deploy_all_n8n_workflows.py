import os
import json
import glob
import requests
from dotenv import load_dotenv

load_dotenv()
n8n_url = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
n8n_key = os.getenv("N8N_PUBLIC_API_KEY", "")

headers = {
    "X-N8N-API-KEY": n8n_key,
    "Content-Type": "application/json"
}

workflow_files = sorted(glob.glob("workflows/*.json"))
print(f"Deploying {len(workflow_files)} n8n workflows to {n8n_url}...")

# Check existing workflows
r = requests.get(f"{n8n_url}/api/v1/workflows", headers=headers)
existing = {}
if r.status_code == 200:
    for wf in r.json().get("data", []):
        existing[wf.get("name")] = wf.get("id")

deployed = {}

for fpath in workflow_files:
    fname = os.path.basename(fpath)
    with open(fpath, "r", encoding="utf-8") as f:
        wf_data = json.load(f)
    
    raw_name = wf_data.get("name", fname.replace(".json", ""))
    wf_name = f"Warehouse: {raw_name}"
    
    # Extract webhook path if present
    webhook_path = None
    for node in wf_data.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            webhook_path = node.get("parameters", {}).get("path")
            break

    payload = {
        "name": wf_name,
        "nodes": wf_data.get("nodes", []),
        "connections": wf_data.get("connections", {}),
        "settings": wf_data.get("settings", {})
    }

    wf_id = existing.get(wf_name)
    if wf_id:
        print(f"  [EXISTS] Updating '{wf_name}' (ID: {wf_id})...")
        up_r = requests.put(f"{n8n_url}/api/v1/workflows/{wf_id}", headers=headers, json=payload)
    else:
        print(f"  [NEW] Creating '{wf_name}'...")
        up_r = requests.post(f"{n8n_url}/api/v1/workflows", headers=headers, json=payload)
        if up_r.status_code in [200, 201]:
            wf_id = up_r.json().get("id") or up_r.json().get("data", {}).get("id")

    if wf_id:
        # Activate workflow
        act_r = requests.post(f"{n8n_url}/api/v1/workflows/{wf_id}/activate", headers=headers)
        active = act_r.status_code == 200
        webhook_url = f"{n8n_url}/webhook/{webhook_path}" if webhook_path else None
        print(f"    -> Deployed ID: {wf_id} | Active: {active} | Webhook: {webhook_url}")
        deployed[raw_name] = {
            "id": wf_id,
            "name": wf_name,
            "webhook_path": webhook_path,
            "webhook_url": webhook_url,
            "active": active
        }

with open("n8n_endpoints.json", "w", encoding="utf-8") as f:
    json.dump(deployed, f, indent=2)

print("\nDeployment Complete! Saved configuration to n8n_endpoints.json")
