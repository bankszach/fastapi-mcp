import os, sys, time, json, urllib.request
url = os.environ.get("MCP_URL", "http://localhost:3000/healthz")
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        assert data.get("status") == "ok", f"unexpected body: {data}"
        print("[health] OK", data)
except Exception as e:
    print("[health] FAIL", e)
    sys.exit(1)
