"""
Configures, optimizes, and publishes all 10 Dify Warehouse Workflows in Dify
Ensures:
- LLM nodes use active provider (OpenRouter / google/gemini-2.5-flash)
- LLM context is set to { enabled: false }
- End node value_selector correctly points to LLM text output
- Draft is saved with valid hash
- Workflows are published and API keys verified
"""

import subprocess
import json
import httpx
import asyncio
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

BSK_PATH = r"C:\Users\Arindam RoY\.local\bin\bsk.exe"

# The 10 Warehouse Apps
with open("dify_endpoints.json", "r", encoding="utf-8") as f:
    ALL_ENDPOINTS = json.load(f)

WAREHOUSE_APPS = {
    name: data for name, data in ALL_ENDPOINTS.items()
    if name.startswith(("01", "02", "03", "04", "05", "06", "07", "08", "09", "10"))
}

print(f"Found {len(WAREHOUSE_APPS)} Warehouse apps to configure and publish:")
for name, data in WAREHOUSE_APPS.items():
    print(f"  - {name} ({data['id']})")

def configure_all_apps():
    code = f"""
    (async () => {{
      const match = document.cookie.match(/csrf_token=([^;]+)/);
      const csrf = match ? match[1] : '';
      const apps = {json.dumps(WAREHOUSE_APPS)};
      const results = {{}};
      
      for (const [name, info] of Object.entries(apps)) {{
        const appId = info.id;
        try {{
          // 1. Fetch draft
          const draftRes = await fetch('/console/api/apps/' + appId + '/workflows/draft', {{
            credentials: 'include',
            headers: {{ 'X-CSRF-Token': csrf }}
          }});
          const draft = await draftRes.json();
          if (!draft.graph || !draft.graph.nodes) {{
            results[name] = {{ status: 'failed', error: 'no graph nodes' }};
            continue;
          }}
          
          let llmNodeId = null;
          for (const node of draft.graph.nodes) {{
            if (node.data.type === 'llm') {{
              llmNodeId = node.id;
              node.data.context = {{ enabled: false }};
              node.data.model = {{
                provider: 'langgenius/openrouter/openrouter',
                name: 'google/gemini-2.5-flash',
                mode: 'chat',
                completion_params: {{ temperature: 0.2 }}
              }};
            }}
          }}
          
          // Fix end node if pointing to an llm node
          for (const node of draft.graph.nodes) {{
            if (node.data.type === 'end' && node.data.outputs) {{
              for (const out of node.data.outputs) {{
                if (out.value_selector && (out.value_selector[0] === llmNodeId || out.value_selector[0].startsWith('llm'))) {{
                  out.value_selector[1] = 'text';
                }}
              }}
            }}
          }}
          
          // 2. Save draft
          const saveRes = await fetch('/console/api/apps/' + appId + '/workflows/draft', {{
            method: 'POST',
            credentials: 'include',
            headers: {{ 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              graph: draft.graph,
              features: draft.features || {{}},
              hash: draft.hash,
              environment_variables: draft.environment_variables || [],
              conversation_variables: draft.conversation_variables || []
            }})
          }});
          const saveData = await saveRes.json();
          
          // 3. Publish workflow
          const pubRes = await fetch('/console/api/apps/' + appId + '/workflows/publish', {{
            method: 'POST',
            credentials: 'include',
            headers: {{ 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{}})
          }});
          const pubData = await pubRes.json();
          
          // 4. Verify API key
          const keyRes = await fetch('/console/api/apps/' + appId + '/api-keys', {{
            credentials: 'include',
            headers: {{ 'X-CSRF-Token': csrf }}
          }});
          const keyData = await keyRes.json();
          let token = keyData.data && keyData.data[0] ? keyData.data[0].token : null;
          if (!token) {{
            const createRes = await fetch('/console/api/apps/' + appId + '/api-keys', {{
              method: 'POST',
              credentials: 'include',
              headers: {{ 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{}})
            }});
            const createData = await createRes.json();
            token = createData.token;
          }}
          
          results[name] = {{
            status: pubData.result === 'success' ? 'published' : 'failed',
            token: token,
            save: saveData.result,
            publish: pubData.result
          }};
        }} catch (err) {{
          results[name] = {{ status: 'error', error: String(err) }};
        }}
      }}
      return results;
    }})()
    """
    
    start = subprocess.check_output([BSK_PATH, "session", "start", "--browser", "2148394c", "--json"])
    sess = json.loads(start.decode())["session_id"]
    try:
        subprocess.check_output([BSK_PATH, "navigate", "http://158.69.215.232:3000/apps", "--session", sess])
        out = subprocess.check_output([BSK_PATH, "evaluate", code, "--session", sess])
        return json.loads(out.decode())
    finally:
        subprocess.check_output([BSK_PATH, "session", "stop", sess])

def main():
    print("\nConfiguring and publishing all 10 Dify apps via Browser Skill...")
    res = configure_all_apps()
    print("\nResults:")
    for name, r in res.items():
        print(f"  [{r.get('status', 'unknown').upper()}] {name}: Token={r.get('token')} | Publish={r.get('publish')}")
        if name in ALL_ENDPOINTS and r.get('token'):
            ALL_ENDPOINTS[name]['api_key'] = r['token']
            ALL_ENDPOINTS[name]['status'] = 'published'

    with open("dify_endpoints.json", "w", encoding="utf-8") as f:
        json.dump(ALL_ENDPOINTS, f, indent=2)

    key_map = {name: r.get('token') for name, r in res.items() if r.get('token')}
    with open("dify_workflows/dify_app_keys.json", "w", encoding="utf-8") as f:
        json.dump(key_map, f, indent=2)

    print("\nSaved updated dify_endpoints.json and dify_workflows/dify_app_keys.json")

if __name__ == "__main__":
    main()
