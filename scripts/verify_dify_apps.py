import subprocess
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

BSK_PATH = os.getenv("BSK_PATH", "bsk")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "http://localhost:3000").rstrip("/")

def run_bsk(*args):
    res = subprocess.run([BSK_PATH] + list(args), capture_output=True, text=True, check=True)
    return res.stdout.strip()

def main():
    created_session = False
    session_id = None
    
    # Check existing sessions
    try:
        sess_out = run_bsk("session", "list", "--json")
        sessions = json.loads(sess_out)
        for s in sessions:
            if DIFY_BASE_URL in s.get("url", ""):
                session_id = s.get("id")
                break
    except Exception:
        sessions = []

    if not session_id:
        # Start a new session on browser profile
        try:
            browsers_out = run_bsk("browsers", "--json")
            browsers = json.loads(browsers_out)
            browser_id = browsers[0]["id"] if browsers else None
        except Exception:
            browser_id = None
        
        args = ["session", "start", "--json"]
        if browser_id:
            args.extend(["--browser", browser_id])
        
        start_out = run_bsk(*args)
        sess_info = json.loads(start_out)
        session_id = sess_info.get("session_id") or sess_info.get("id")
        created_session = True
        run_bsk("navigate", f"{DIFY_BASE_URL}/apps", "--session", session_id)

    code = """
(async () => {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  const csrf = match ? match[1] : '';
  const res = await fetch('/console/api/apps?page=1&limit=30', {
    credentials: 'include',
    headers: {
      'X-CSRF-Token': csrf
    }
  });
  const data = await res.json();
  return (data.data || []).map(a => ({
    id: a.id,
    name: a.name,
    mode: a.mode,
    created_at: a.created_at,
    updated_at: a.updated_at
  }));
})()
"""

    try:
        out = run_bsk("evaluate", code, "--session", session_id)
        apps = json.loads(out)
        print(f"Total Dify Applications in Workspace: {len(apps)}\n")
        
        output_data = {}
        for a in apps:
            print(f"  - [{a.get('mode', 'app').upper()}] {a.get('name')} (ID: {a.get('id')})")
            output_data[a.get('name')] = {
                "id": a.get("id"),
                "mode": a.get("mode"),
                "console_url": f"{DIFY_BASE_URL}/app/{a.get('id')}/workflow"
            }
        
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dify_endpoints.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nSaved {len(output_data)} verified Dify applications to {json_path}")
    finally:
        if created_session and session_id:
            try:
                run_bsk("session", "stop", session_id)
            except Exception:
                pass

if __name__ == "__main__":
    main()
