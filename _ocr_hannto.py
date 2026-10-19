from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np, os

base = r"c:\Users\Administrator\Documents\GitHub\4mdfiles"
out = r"c:\Users\Administrator\Documents\GitHub\4mdfiles\_hannto_ocr.txt"

ocr = RapidOCR()
all_lines = []

for name in ["hannto01.png", "hannto02.png"]:
    path = os.path.join(base, name)
    img = Image.open(path).convert("RGB")
    w, h = img.size
    print(f"--- {name}: {w}x{h} ---")
    scale = 1.0
    if max(w, h) < 2000:
        scale = 2.0
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    result, _ = ocr(np.array(img))
    all_lines.append(f"\n========== {name} ({w}x{h}) ==========")
    if result:
        rows = []
        for box, text, score in result:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            yc = sum(ys) / 4
            xmin = min(xs)
            rows.append((yc, xmin, text, score))
        # sort by row band then x
        rows.sort(key=lambda r: (r[0], r[1]))
        band = 14 * scale
        cur = None
        bucket = []
        out_rows = []
        for y, x, t, s in rows:
            if cur is None or abs(y - cur) <= band:
                bucket.append((x, t, s))
                cur = y if cur is None else cur
            else:
                out_rows.append((cur, bucket))
                bucket = [(x, t, s)]
                cur = y
        if bucket:
            out_rows.append((cur, bucket))
        for y, b in out_rows:
            b.sort(key=lambda r: r[0])
            joined = "   |   ".join(f"{t}" for x, t, s in b)
            all_lines.append(f"y={y/scale:.0f}  {joined}")
    else:
        all_lines.append("(no text)")

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(all_lines))
print("saved")
