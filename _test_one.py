#!/usr/bin/env python3
"""Fetch root node via curl.exe (known to work) and parse all images."""
import json, os, re, base64, io, sys, subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "design_screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

def curl_post(url, json_file, sid=None, timeout=120):
    """Use curl.exe to POST and capture full response."""
    cmd = ["curl.exe", "-s", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream"]
    if sid:
        cmd += ["-H", f"mcp-session-id: {sid}"]
    cmd += ["--data-binary", f"@{json_file}", "--max-time", str(timeout)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout+10)
    return result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace")

def curl_post_with_headers(url, json_file, timeout=15):
    """POST and return headers + body."""
    cmd = ["curl.exe", "-s", "-D", "-", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream",
           "--data-binary", f"@{json_file}", "--max-time", str(timeout)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout+10)
    output = result.stdout.decode("utf-8", errors="replace")
    # Split headers and body
    parts = output.split("\r\n\r\n", 1)
    headers = parts[0] if len(parts) > 0 else ""
    body = parts[1] if len(parts) > 1 else ""
    return headers, body

BASE_URL = "http://127.0.0.1:3845/mcp"
REQ_FILE = os.path.join(SCRIPT_DIR, "_req.json")

# Step 1: Initialize
init = {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codebuddy","version":"1.0"}},"id":1}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(init, f)

headers, init_body = curl_post_with_headers(BASE_URL, REQ_FILE)
# Extract session ID
sid = None
for line in headers.split("\n"):
    if "mcp-session-id" in line.lower():
        sid = line.split(":",1)[1].strip()
print(f"Session: {sid}")
print(f"Init body length: {len(init_body)}")

if not sid:
    print("ERROR: No session ID")
    sys.exit(1)

# Step 2: Send initialized notification
notif = {"jsonrpc":"2.0","method":"notifications/initialized"}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(notif, f)
curl_post(BASE_URL, REQ_FILE, sid=sid, timeout=10)
print("Notif sent")

# Step 3: Fetch root node 2:1306
call = {"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_design_context","arguments":{"nodeId":"2:1306","clientLanguages":"unknown","clientFrameworks":"unknown","disableCodeConnect":True}},"id":2}
with open(REQ_FILE, "w", encoding="utf-8") as f:
    json.dump(call, f)

print("Fetching root node 2:1306...")
resp, err = curl_post(BASE_URL, REQ_FILE, sid=sid, timeout=120)
print(f"Response length: {len(resp)}")
if err:
    print(f"Stderr: {err[:500]}")

# Save response
resp_file = os.path.join(SCRIPT_DIR, "_root_resp.txt")
with open(resp_file, "w", encoding="utf-8") as f:
    f.write(resp)
print(f"Saved to {resp_file}")

# Check for image data
has_image = "image" in resp.lower()
print(f"Has 'image': {has_image}")

if has_image:
    # Find all image content items
    # Pattern: {"type":"image","data":"base64...","mimeType":"image/png"}
    pattern = r'"type"\s*:\s*"image"\s*,\s*"data"\s*:\s*"([A-Za-z0-9+/=]+)"\s*,\s*"mimeType"\s*:\s*"(image/\w+)"'
    matches = re.findall(pattern, resp)
    print(f"Found {len(matches)} image items")
    
    # Also try reversed order: data first, then type
    if not matches:
        pattern2 = r'"data"\s*:\s*"([A-Za-z0-9+/=]{100,})"\s*,\s*"mimeType"\s*:\s*"(image/\w+)"'
        matches = re.findall(pattern2, resp)
        print(f"Found {len(matches)} images (alt pattern)")
    
    # Save each image
    from PIL import Image
    for idx, (b64, mime) in enumerate(matches):
        try:
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw))
            # Resize to max 540px width
            if img.width > 540:
                ratio = 540 / img.width
                img = img.resize((540, int(img.height * ratio)), Image.LANCZOS)
            if img.mode in ("RGBA", "P", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            out_path = os.path.join(OUT_DIR, f"screen_{idx+1:02d}.jpg")
            img.save(out_path, "JPEG", quality=75, optimize=True)
            size_kb = os.path.getsize(out_path) / 1024
            print(f"  Saved: screen_{idx+1:02d}.jpg ({img.width}x{img.height}, {size_kb:.0f} KB)")
        except Exception as e:
            print(f"  Image {idx+1}: ERROR - {e}")
else:
    # Show first 2000 chars
    print("No image data found. First 2000 chars:")
    print(resp[:2000])
