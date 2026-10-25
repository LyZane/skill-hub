# -*- coding: utf-8 -*-
"""按 URL 去重下载 data.json 中的 SKU 图片，压缩为 160px JPEG 缩略图，输出 manifest.json。
用法: python3 download_images.py <data.json> <输出目录>"""
import json, os, sys, urllib.request
from PIL import Image as PILImage

def main():
    if len(sys.argv) < 3:
        sys.exit("用法: python3 download_images.py <data.json> <输出目录>")
    data_path, outdir = sys.argv[1], sys.argv[2]
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    urls = []
    for item in data.get("items", []):
        for row in item.get("rows", []):
            if row.get("image"):
                urls.append(row["image"])
    uniq = list(dict.fromkeys(urls))
    os.makedirs(outdir, exist_ok=True)
    manifest, failed = {}, []
    for url in uniq:
        name = os.path.basename(url)
        small = os.path.join(outdir, name)
        raw = os.path.join(outdir, "raw_" + name)
        if not (os.path.exists(small) and os.path.getsize(small) > 200):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0", "Referer": "https://detail.tmall.com/"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(raw, "wb") as fh:
                    fh.write(resp.read())
                with PILImage.open(raw) as im:
                    im = im.convert("RGB")
                    im.thumbnail((160, 160))
                    im.save(small, "JPEG", quality=85)
            except Exception as e:
                failed.append((url, str(e)))
        manifest[url] = os.path.abspath(small)
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(json.dumps({"unique": len(uniq), "ok": len(uniq) - len(failed),
                      "failed": failed}, ensure_ascii=False))

if __name__ == "__main__":
    main()
