#!/usr/bin/env python3
"""Fetch Figma design nodes via MCP SSE and save as small JPEG images."""
import json, os, re, base64, io, sys, time
import http.client

BASE_URL_HOST = "127.0.0.1"
BASE_URL_PORT = 3845
BASE_URL_PATH = "/mcp"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "design_screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

NODE_MAP = [
    ("1:2066", "L-01", "01-Login-default"),
    ("1:2075", "L-01b", "01-Login-terms-checked"),
    ("1:2084", "L-04", "01-Login-toast"),
    ("1:2094", "L-05", "01-Login-error-dialog"),
    ("1:2105", "L-06", "01-Login-mijia-auth-1"),
    ("1:2119", "L-06b", "01-Login-mijia-auth-2"),
    ("1:2134", "L-06c", "01-Login-mijia-auth-3"),
    ("1:2150", "L-10", "02-Loading"),
    ("1:2183", "H-01", "03-Home-no-device"),
    ("1:2214", "A-01", "05-AddDevice-select"),
    ("1:2267", "A-01b", "05-AddDevice-select-2"),
    ("1:2158", "A-08", "05-Bluetooth-scanning"),
    ("1:2167", "A-08b", "05-Bluetooth-found"),
    ("1:2207", "A-08c", "05-Bluetooth-success"),
    ("1:2174", "A-12a", "05-Status-1"),
    ("1:2177", "A-12b", "05-Status-2"),
    ("1:2180", "A-12c", "05-Status-3"),
    ("1:2333", "M-01", "04-Mine-default"),
    ("1:2367", "M-04", "04-Mine-review-popup"),
    ("1:2407", "M-06", "04-Mine-profile"),
    ("1:2598", "M-06b", "04-Mine-profile-avatar"),
    ("1:2835", "M-06c", "04-Mine-profile-nickname"),
    ("1:2422", "M-11", "04-Mine-settings"),
    ("1:2438", "M-11b", "04-Mine-settings-2"),
    ("1:2456", "M-11c", "04-Mine-settings-3"),
    ("1:2505", "M-16", "04-Mine-consumables"),
    ("1:2853", "M-10a", "04-Mine-download-1"),
    ("1:2884", "M-10b", "04-Mine-download-2"),
]

def mcp_request(session_id, body, read_timeout=90):
    conn = http.client.HTTPConnection(BASE_URL_HOST, BASE_URL_PORT, timeout=read_timeout)
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if session_id:
        headers["mcp-session-id"] = session_id
    conn.request("POST", BASE_URL_PATH, body=data, headers=headers)
    resp = conn.getresponse()
    full_text = ""
    found_result = False
    while True:
        line = resp.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace")
        full_text += decoded
        if decoded.strip().startswith("data:"):
            json_str = decoded.strip()[5:].strip()
            if json_str:
                try:
                    parsed = json.loads(json_str)
                    if "result" in parsed or "error" in parsed:
                        found_result = True
                        conn.sock.settimeout(3)
                        try:
                            while True:
                                extra = resp.readline()
                                if not extra:
                                    break
                                full_text += extra.decode("utf-8", errors="replace")
                        except:
                            pass
                        break
                except:
                    pass
    conn.close()
    return resp.status, resp.getheader("mcp-session-id"), full_text

def extract_images(resp_text):
    images = []
    lines = resp_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("data:"):
            json_str = line[5:].strip()
            if not json_str:
                continue
            try:
                data = json.loads(json_str)
            except:
                continue
            result = data.get("result", {})
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image":
                        img_data = item.get("data", "")
                        mime = item.get("mimeType", "image/png")
                        if img_data:
                            images.append((img_data, mime))
    if not images:
        try:
            data = json.loads(resp_text)
            result = data.get("result", {})
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image":
                        img_data = item.get("data", "")
                        mime = item.get("mimeType", "image/png")
                        if img_data:
                            images.append((img_data, mime))
        except:
            pass
    if not images:
        pattern = r'"data"\s*:\s*"([A-Za-z0-9+/=]{1000,})"'
        matches = re.findall(pattern, resp_text)
        for b64 in matches:
            images.append((b64, "image/png"))
    return images

def save_as_jpeg(b64_data, mime_type, out_path, max_width=540):
    try:
        raw = base64.b64decode(b64_data)
    except:
        return False
    from PIL import Image
    img = Image.open(io.BytesIO(raw))
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(out_path, "JPEG", quality=75, optimize=True)
    return True

def main():
    print("=== Figma Design Screenshot Exporter ===")
    init_body = {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codebuddy","version":"1.0"}},"id":1}
    status, sid, init_text = mcp_request(None, init_body)
    if not sid:
        print(f"ERROR: No session ID. Status={status}")
        print(init_text[:500])
        sys.exit(1)
    print(f"Session: {sid}")
    notif = {"jsonrpc":"2.0","method":"notifications/initialized"}
    mcp_request(sid, notif, read_timeout=10)
    print("Initialized notification sent")
    success_count = 0
    fail_count = 0
    for i, (node_id, req_code, desc) in enumerate(NODE_MAP):
        print(f"\n[{i+1}/{len(NODE_MAP)}] {req_code} ({desc}) node:{node_id}")
        try:
            call = {"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_design_context","arguments":{"nodeId":node_id,"clientLanguages":"unknown","clientFrameworks":"unknown","disableCodeConnect":True}},"id":i+10}
            status, _, resp_text = mcp_request(sid, call)
            print(f"  Status: {status}, Response length: {len(resp_text)}")
            if not resp_text or len(resp_text) < 50:
                print("  WARNING: Empty response")
                fail_count += 1
                continue
            images = extract_images(resp_text)
            print(f"  Found {len(images)} image(s)")
            if images:
                b64, mime = images[0]
                out_path = os.path.join(OUT_DIR, f"{req_code}.jpg")
                if save_as_jpeg(b64, mime, out_path):
                    size_kb = os.path.getsize(out_path) / 1024
                    print(f"  Saved: {req_code}.jpg ({size_kb:.0f} KB)")
                    success_count += 1
                else:
                    print("  ERROR: Failed to save")
                    fail_count += 1
            else:
                debug_path = os.path.join(OUT_DIR, f"{req_code}_debug.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(resp_text[:5000])
                print(f"  No images. Debug saved to {req_code}_debug.txt")
                fail_count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  ERROR: {e}")
            fail_count += 1
    print(f"\n=== Done! Success: {success_count}, Failed: {fail_count} ===")
    print(f"Output: {OUT_DIR}")

if __name__ == "__main__":
    main()
