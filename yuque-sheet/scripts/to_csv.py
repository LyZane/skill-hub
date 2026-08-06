#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data.json → CSV 二维表（合并区非锚点单元格留空；图片转 URL；链接转文本）。
用法: python3 to_csv.py <data.json> <out.csv>
"""
import csv, json, sys

def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    cells = data["cells"]
    max_r = max_c = 0
    grid = {}
    for r, c, v, bg in cells:
        grid[(r, c)] = v
        max_r, max_c = max(max_r, r), max(max_c, c)

    def text(v):
        if v is None:
            return ""
        if isinstance(v, dict):
            return v.get("link") or v.get("img") or ""
        return str(v)

    with open(sys.argv[2], "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for r in range(max_r + 1):
            w.writerow([text(grid.get((r, c))) for c in range(max_c + 1)])
    print("saved", sys.argv[2], f"({max_r + 1}x{max_c + 1})")

if __name__ == "__main__":
    main()
