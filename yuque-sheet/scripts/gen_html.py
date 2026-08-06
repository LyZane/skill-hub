#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 extract.js 产出的 data.json 生成打印友好的 HTML 页面。
用法: python3 gen_html.py <data.json> <imgs_dir> <out_dir> [split_col]
split_col = 第 2 页起始产品列号；缺省自动取中点并避开合并单元格。
输出: out_dir/page_full.html, page_p1.html, page_p2.html, widths.json
"""
import json, base64, os, re, sys, html as H

ACCENTS = ["#047857", "#1d4ed8", "#b45309", "#6d28d9", "#0e7490", "#be185d", "#4d7c0f", "#9333ea"]

def rgba(s):
    s = (s or "").strip()
    if s.startswith("#"):
        h = s.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [1]
    m = re.findall(r"[\d.]+", s)
    return [float(x) for x in m[:4]] if m else [255, 255, 255, 1]

def blend(pastel, accent, t=0.22):
    p, a = rgba(pastel), rgba(accent)
    return "#%02x%02x%02x" % tuple(int(p[i] + (a[i] - p[i]) * t) for i in range(3))

def main():
    data_path, imgs_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    split_arg = int(sys.argv[4]) if len(sys.argv) > 4 else None
    os.makedirs(out_dir, exist_ok=True)
    data = json.load(open(data_path, encoding="utf-8"))
    cells, merges, back_colors = data["cells"], data["merges"], data.get("backColors") or []
    title = data.get("title") or "表格"

    grid = {}
    max_r = max_c = 0
    for r, c, v, bg in cells:
        grid[(r, c)] = (v, bg)
        max_r, max_c = max(max_r, r), max(max_c, c)

    anchor, covered = {}, set()
    for r, c, rs, cs in merges:
        anchor[(r, c)] = (rs, cs)
        for i in range(r, r + rs):
            for j in range(c, c + cs):
                if (i, j) != (r, c):
                    covered.add((i, j))

    def img_uri(src):
        fn = src.split("/")[-1]
        p = os.path.join(imgs_dir, fn)
        ext = "jpeg" if fn.lower().endswith((".jpg", ".jpeg")) else "png"
        with open(p, "rb") as f:
            return f"data:image/{ext};base64," + base64.b64encode(f.read()).decode()

    # 百分比启发式: 数字<1 且同行其它单元格含 '%'
    pct_cells = set()
    row_has_pct = set()
    for (r, c), (v, bg) in grid.items():
        if isinstance(v, str) and "%" in v:
            row_has_pct.add(r)
    for (r, c), (v, bg) in grid.items():
        if isinstance(v, (int, float)) and 0 < v < 1 and r in row_has_pct:
            pct_cells.add((r, c))

    def label_of(r):
        e = grid.get((r, 0))
        return str(e[0]) if e and not isinstance(e[0], dict) else ""

    def is_num(x):
        return isinstance(x, (int, float)) or (isinstance(x, str) and re.fullmatch(r"\d+(\.\d+)?", x or ""))

    def cell_html(r, c):
        e = grid.get((r, c))
        if not e:
            return ""
        v, bg = e
        if isinstance(v, dict) and "img" in v:
            return f'<img src="{img_uri(v["img"])}" alt="">'
        text = str(v) if not isinstance(v, dict) else (v.get("link") or "")
        if (r, c) in pct_cells and isinstance(v, (int, float)):
            text = f"{v * 100:.0f}%"
        elif is_num(v) and "价" in label_of(r):
            text = "¥" + text
        text = H.escape(text)
        text = text.replace("✅", '<span class="yes">✓</span>').replace("❌", '<span class="no">✕</span>')
        return text.replace("\n", "<br>")

    def theme(bg):
        if bg is None or bg < 0:
            return "#ffffff", "#e2e8f0", "#0f172a"
        pastel = back_colors[bg] if bg < len(back_colors) else "#f1f5f9"
        accent = ACCENTS[bg % len(ACCENTS)]
        return pastel, blend(pastel, accent), accent

    def pick_split():
        if split_arg:
            return split_arg
        mid = (1 + max_c) // 2 + 1
        def bad(s):
            return any(c < s <= c + cs - 1 for _, c, _, cs in merges)
        for off in range(0, max_c):
            for s in (mid + off, mid - off):
                if 2 <= s <= max_c and not bad(s):
                    return s
        return mid

    def build_table(c_start, c_end, font_px, label_w, prod_w):
        cols = [0] + list(range(c_start, c_end + 1))
        total_w = label_w + prod_w * len(cols[1:])
        cg = f'<col style="width:{label_w}px">' + f'<col style="width:{prod_w}px">' * len(cols[1:])
        rows_html = []
        for r in range(max_r + 1):
            tds = []
            for c in cols:
                if (r, c) in covered:
                    continue
                e = grid.get((r, c))
                bg = e[1] if e else -1
                pastel, head_bg, accent = theme(bg)
                cls, style = [], []
                if c == 0:
                    cls.append("label")
                elif r == 0:
                    cls.append("cat"); style.append(f"background:{head_bg};color:{accent}")
                elif e and isinstance(e[0], dict) and "img" in e[0]:
                    cls.append("imgcell"); style.append(f"background:{pastel}")
                elif r == 1 or (e and isinstance(e[0], dict) and "img" in e[0]):
                    cls.append("imgcell"); style.append(f"background:{pastel}")
                elif r == 2:
                    cls.append("model"); style.append(f"background:{pastel};color:{accent}")
                else:
                    style.append(f"background:{pastel}")
                if e and is_num(e[0]):
                    cls.append("num")
                if r == max_r:
                    cls.append("who")
                span = ""
                if (r, c) in anchor:
                    rs, cs = anchor[(r, c)]
                    cs2 = len([cc for cc in range(c, c + cs) if cc == 0 or c_start <= cc <= c_end])
                    if rs > 1: span += f' rowspan="{rs}"'
                    if cs2 > 1: span += f' colspan="{cs2}"'
                tds.append(f'<td class="{" ".join(cls)}" style="{";".join(style)}"{span}>{cell_html(r, c)}</td>')
            rows_html.append("<tr>" + "".join(tds) + "</tr>")
        return total_w, f'<table style="width:{total_w}px"><colgroup>{cg}</colgroup>{"".join(rows_html)}</table>'

    def build_page(sub, c_start, c_end, font_px, label_w, prod_w, out_name):
        total_w, table = build_table(c_start, c_end, font_px, label_w, prod_w)
        pad = 36
        page_w = total_w + pad * 2
        page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ background:#fff; }}
  body {{ font-family:"PingFang SC","Hiragino Sans GB","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
         font-size:{font_px}px; color:#1e293b; -webkit-font-smoothing:antialiased; }}
  .page {{ width:{page_w}px; padding:{pad}px; }}
  .head {{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:18px; }}
  .head h1 {{ font-size:{int(font_px*1.9)}px; font-weight:700; color:#0f172a; letter-spacing:1px; }}
  .head h1 .accent {{ color:#0284c7; }}
  .head .meta {{ font-size:{int(font_px*0.85)}px; color:#94a3b8; }}
  .subnote {{ font-size:{int(font_px*0.9)}px; color:#64748b; margin:-8px 0 14px; }}
  table {{ border-collapse:collapse; table-layout:fixed; border:2px solid #cbd5e1; }}
  td {{ border:1px solid #e2e8f0; padding:5px 6px; text-align:center; vertical-align:middle;
        word-break:break-all; line-height:1.35; }}
  td.label {{ background:#f8fafc; font-weight:600; color:#334155; text-align:left; padding-left:10px;
              font-size:{int(font_px*0.95)}px; }}
  td.cat {{ font-weight:700; font-size:{int(font_px*1.15)}px; letter-spacing:2px; }}
  td.imgcell {{ padding:6px; }}
  td.imgcell img {{ max-width:100%; max-height:118px; object-fit:contain; display:inline-block; }}
  td.model {{ font-weight:600; font-size:{int(font_px*0.92)}px; }}
  td.num {{ font-family:"SF Pro Display","DIN Alternate",Arial,sans-serif; font-weight:600; }}
  tr:first-child td {{ height:42px; }}
  tr:nth-child(2) td {{ height:132px; }}
  td.who {{ font-size:{int(font_px*0.9)}px; color:#475569; padding:8px 6px; }}
  .yes {{ color:#059669; font-weight:700; }}
  .no {{ color:#dc2626; font-weight:700; }}
</style></head><body><div class="page">
  <div class="head"><h1><span class="accent">{H.escape(title)}</span></h1>
  <div class="meta">数据来源：语雀 ｜ 导出 {__import__('datetime').date.today().isoformat()}</div></div>
  {f'<div class="subnote">{sub}</div>' if sub else ''}
  {table}
</div></body></html>"""
        open(os.path.join(out_dir, out_name), "w", encoding="utf-8").write(page)
        return page_w

    # 分页: 按系列色带(row0 分类)打包, 同一系列不跨页, 每页产品列 <= MAX_COLS 保证 A4 横向可读
    MAX_COLS = 9
    cat_at = {}
    for (r, c), (v, bg) in grid.items():
        if r == 0 and c > 0 and not isinstance(v, dict):
            cat_at[c] = (bg, str(v))
    bands = []
    if cat_at:
        cur = None
        for c in range(1, max_c + 1):
            if c in cat_at:
                bg, name = cat_at[c]
                if cur is not None and cur[2] == bg:
                    cur[1] = c
                    cur[3].append(name)
                else:
                    if cur:
                        bands.append(cur)
                    cur = [c, c, bg, [name]]
            elif cur is not None:
                cur[1] = c
        if cur:
            bands.append(cur)
    else:
        s = pick_split()
        bands = [[1, s - 1, -1, []], [s, max_c, -1, []]]
    pages = []
    cur = None
    for b in bands:
        n = b[1] - b[0] + 1
        if cur is not None and (cur[1] - cur[0] + 1) + n <= MAX_COLS:
            cur[1] = b[1]
            cur[3] += b[3]
        else:
            if cur:
                pages.append(cur)
            cur = [b[0], b[1], b[2], list(b[3])]
    if cur:
        pages.append(cur)

    widths = {}
    widths["full"] = build_page("", 1, max_c, 13, 150, 132, "page_full.html")
    for i, pg in enumerate(pages, 1):
        n = pg[1] - pg[0] + 1
        prod_w = 210 if n <= 5 else (175 if n <= 9 else 155)
        font = 16 if n <= 5 else 15
        names = " + ".join(pg[3]) if pg[3] else f"列 {pg[0]}–{pg[1]}"
        sub = f"打印版 第 {i} / {len(pages)} 页 ｜ {names}"
        widths[f"p{i}"] = build_page(sub, pg[0], pg[1], font, 170, prod_w, f"page_p{i}.html")
    json.dump(widths, open(os.path.join(out_dir, "widths.json"), "w"))
    print("pages =", [(p[0], p[1], p[3]) for p in pages], "widths =", widths)

if __name__ == "__main__":
    main()
