#!/usr/bin/env python3
"""Fetch a sub-node via curl.exe to check if it returns image data."""
import json, os, re, subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "http://127.0.0.1:3845/mcp"
REQ_FILE = os.path.join(SCRIPT_DIR, "_req.json")

def curl_post(url, json_file, sid=None, timeout=120):
    cmd = ["curl.exe", "-s", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream"]
    if sid:
        cmd += ["-H", f"mcp-session-id: {sid}"]
    cmd += ["--data-binary", f"@{json_file}", "--max-time", str(timeout)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout+10)
    return result.stdout.decode("utf-8", errors="replace")

def curl_post_headers(url, json_file, timeout=15):
    cmd = ["curl.exe", "-s", "-D", "-", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream",
           "--data-binary", f"@{json_file}", "--max-time", str(timeout)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout+10)
    output = result.stdout.decode("utf-8", errors="replace")
    parts = output.split("\r\n\r\n", 1)
    return (parts[0] if parts else ""), (parts[1] if len(parts) > 1 else "")

# Init
init = {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codebuddy","version":"1.0"}},"id":1}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(init, f)
headers, body = curl_post_headers(BASE_URL, REQ_FILE)
sid = None
for line in headers.split("\n"):
    if "mcp-session-id" in line.lower():
        sid = line.split(":",1)[1].strip()
print(f"Session: {sid}")

# Notif
notif = {"jsonrpc":"2.0","method":"notifications/initialized"}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(notif, f)
curl_post(BASE_URL, REQ_FILE, sid=sid, timeout=10)
print("Notif sent")

# Fetch sub-node 1:2066 (01 登录, 360x780)
call = {"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_design_context","arguments":{"nodeId":"1:2066","clientLanguages":"html,css,typescript","clientFrameworks":"react","disableCodeConnect":True}},"id":2}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(call, f)

print("Fetching sub-node 1:2066...")
resp = curl_post(BASE_URL, REQ_FILE, sid=sid, timeout=120)
print(f"Response length: {len(resp)}")

# Save response
with open(os.path.join(SCRIPT_DIR, "_sub_resp.txt"), "w", encoding="utf-8") as f:
    f.write(resp)

# Check for image data
has_image_type = '"type":"image"' in resp or '"type": "image"' in resp
has_base64 = bool(re.search(r'"data"\s*:\s*"[A-Za-z0-9+/=]{1000,}"', resp))
print(f"Has image type: {has_image_type}")
print(f"Has large base64: {has_base64}")

# Show first 3000 chars
print("\n--- First 3000 chars ---")
print(resp[:3000])
