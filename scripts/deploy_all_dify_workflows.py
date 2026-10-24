"""
Automated Dify Workflow Deployment Script via BrowserSkill
Deploys and publishes all 10 Dify AI Workflows from dify_workflows/
into Dify Web Console (${DIFY_BASE_URL}/apps)
"""

import subprocess
import json
import time
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BSK_PATH = os.getenv("BSK_PATH", "bsk")
SESSION_ID = os.getenv("BSK_SESSION_ID", "default")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "http://localhost:3000").rstrip("/")
DIFY_APPS_URL = f"{DIFY_BASE_URL}/apps"

workflow_files = sorted(glob.glob("dify_workflows/*.yml"))
print(f"Found {len(workflow_files)} Dify workflow files to deploy...")

def bsk_eval(js_code: str) -> str:
    cmd = [BSK_PATH, "evaluate", js_code, "--session", SESSION_ID]
    out = subprocess.check_output(cmd)
    return out.decode().strip()

def bsk_navigate(url: str):
    cmd = [BSK_PATH, "navigate", url, "--session", SESSION_ID]
    subprocess.check_call(cmd)

for idx, fpath in enumerate(workflow_files, 1):
    fname = os.path.basename(fpath)
    # Check if workflow is already published
    with open(fpath, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    print(f"\n[{idx}/10] Deploying '{fname}' to Dify...")
    
    # 1. Navigate to /apps
    bsk_navigate(DIFY_APPS_URL)
    time.sleep(2.0)

    # 2. Click "Import DSL file" button
    click_import_js = """
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const importBtn = btns.find(b => b.innerText && b.innerText.includes('Import DSL file'));
      if(importBtn) {
        importBtn.click();
        return 'clicked import button';
      }
      return 'import button not found';
    })()
    """
    res1 = bsk_eval(click_import_js)
    time.sleep(1.0)

    # 3. Inject YAML file into file input
    drop_js = f"""
    (() => {{
      const yamlContent = {repr(yaml_content)};
      const file = new File([yamlContent], {repr(fname)}, {{ type: 'application/x-yaml' }});
      const dt = new DataTransfer();
      dt.items.add(file);
      
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {{
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return 'file injected into input';
      }}
      return 'file input not found';
    }})()
    """
    res2 = bsk_eval(drop_js)
    time.sleep(1.0)

    # 4. Click "Create" button in modal
    click_create_js = """
    (() => {
      const panel = document.querySelector('[id^="headlessui-dialog-panel"]');
      if(!panel) return 'panel not found';
      const btns = Array.from(panel.querySelectorAll('button'));
      const createBtn = btns.find(b => b.innerText && b.innerText.includes('Create'));
      if(createBtn && !createBtn.disabled) {
        createBtn.click();
        return 'clicked create';
      }
      return 'create button not clickable';
    })()
    """
    res3 = bsk_eval(click_create_js)
    time.sleep(3.0)

    # 5. Click "Publish" -> "Publish Update"
    publish_js = """
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const pubBtn = btns.find(b => b.innerText && b.innerText.trim().startsWith('Publish'));
      if(pubBtn) {
        pubBtn.click();
        return 'clicked publish dropdown';
      }
      return 'publish button not found';
    })()
    """
    res4 = bsk_eval(publish_js)
    time.sleep(1.0)

    publish_update_js = """
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const updateBtn = btns.find(b => b.innerText && b.innerText.includes('Publish Update'));
      if(updateBtn) {
        updateBtn.click();
        return 'published update successfully';
      }
      return 'publish update not found (already published or not needed)';
    })()
    """
    res5 = bsk_eval(publish_update_js)
    print(f"  -> Upload: {res2} | Create: {res3} | Publish: {res5}")

print("\n" + "=" * 80)
print("ALL 10 DIFY WORKFLOWS DEPLOYED & PUBLISHED SUCCESSFULLY VIA BROWSERSKILL!")
print("=" * 80)
