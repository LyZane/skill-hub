#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无头 Chrome 2x 渲染 + PIL 裁边。
用法: python3 render.py <out_dir> <标题>
读取 out_dir/widths.json（full + p1..pN），对 page_*.html 截图裁边，
输出 <标题>-完整版.png 与 <标题>-打印版-第N页.png 到 out_dir。
"""
import json, os, subprocess, sys

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

def main():
    out_dir, title = os.path.abspath(sys.argv[1]), sys.argv[2]
    widths = json.load(open(os.path.join(out_dir, "widths.json")))
    chrome = next((p for p in CHROME_CANDIDATES if os.path.exists(p)), None)
    if not chrome:
        sys.exit("未找到 Chrome，请修改 CHROME_CANDIDATES")

    from PIL import Image, ImageChops
    names = {"full": f"{title}-完整版.png"}
    for key in sorted((k for k in widths if k != "full"), key=lambda k: int(k[1:])):
        names[key] = f"{title}-打印版-第{key[1:]}页.png"
    for key, w in widths.items():
        html = os.path.join(out_dir, f"page_{key}.html")
        shot = os.path.join(out_dir, f"shot_{key}.png")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--screenshot={shot}",
                        f"--window-size={w},1600", f"file://{html}"],
                       check=True, capture_output=True)
        im = Image.open(shot).convert("RGB")
        bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
        if bbox:
            im = im.crop((0, 0, im.size[0], min(im.size[1], bbox[3] + 72)))
        im.save(os.path.join(out_dir, names[key]), optimize=True)
        os.remove(shot)
        print(names[key], im.size)

if __name__ == "__main__":
    main()
