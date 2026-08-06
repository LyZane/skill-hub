---
name: yuque-sheet
description: 解析语雀表格文档（lakesheet）为结构化数据，并支持多种下游输出：打印高清图片、导出 Excel/CSV、数据分析。当用户给出 yuque.com 表格文档链接并要求解析/读取/导出/打印/转图片/转 Excel/分析/统计时使用。核心能力：浏览器登录态提取 → deflate 解压 → SpreadJS 解析。
version: 2.0.0
---

# 语雀表格解析与多用输出

## 核心能力：提取结构化数据（所有下游的第一步）
1. 浏览器打开文档（复用用户登录态）：`tabs_create_mcp` 建 tab → `navigate` 到 URL。
2. `javascript_tool` 执行 `scripts/extract.js` 全文（自读 window.appData 的 slug/book_id）。第一次调用返回 JSON 长度；第二次调用 `window.__extract` 取回全文，保存为工作目录 `data.json`。
3. （下游 A/B 带图时需要）下载内嵌图片：从 data.json 提取去重 img src，`curl -sS -o <basename> -H "Referer: https://www.yuque.com/" -H "User-Agent: Mozilla/5.0 ..." <url>` 并行下载到 `imgs/`。

### data.json schema
```json
{
  "title": "文档标题",
  "backColors": ["rgba(236,253,245,1)", "..."],
  "cells": [[row, col, value, bgIndex], "..."],
  "merges": [[row, col, rowspan, colspan], "..."]
}
```
- value 形态：字符串 | 数字 | `{img: url}` | `{link: 显示文本}`；bgIndex=-1 表示无系列色带。
- backColors 下标即 bgIndex（语雀样式 `_bN` token 的 N）。

## 下游 A：打印高清图片
1. `python3 scripts/gen_html.py data.json imgs out`
   - 生成 `page_full.html` + `page_p1..pN.html` + `widths.json`。
   - 分页规则（用户明确要求）：按 row0 分类拆"系列色带"，同一系列不跨页，每页产品列 ≤9，保证 A4 横向可读；列数少的页自动加宽列宽、加大字号。
2. `python3 scripts/render.py out "<标题>"`
   - 无头 Chrome `--force-device-scale-factor=2` 截图 + PIL 裁底边，输出 `<标题>-完整版.png` 与 `<标题>-打印版-第N页.png`。
3. Read 逐张校验后复制到用户工作目录并 present_files。

## 下游 B：导出 Excel
`python3 scripts/to_xlsx.py data.json out.xlsx [--with-images imgs]`
- 写值（纯数字串转数值）、应用合并单元格、系列色带填充、表头行加粗、列宽行高；`--with-images` 在第 2 行嵌入产品图。
- 依赖 openpyxl；本机未预装，缺则 `pip3 install openpyxl`。

## 下游 C：CSV / 数据分析
- `python3 scripts/to_csv.py data.json out.csv`：展开为二维表（合并区非锚点单元格留空；图片转 URL；链接转文本），Excel/pandas 可直接打开。
- 或直接读 data.json 分析：`grid[(r,c)]` + merges 即可任意聚合对比；系列分组直接用 bgIndex。

## Pitfalls
- 不要 WebFetch 抓语雀正文（只有壳）；不要注入 pako（CSP 拦截），必须用原生 `DecompressionStream('deflate')`。
- 空对象 `{}` 的 cell.v 当空单元格。
- 数字 <1 且同行其它单元格含 '%' 时打印版按百分比格式化（0.65→65%）；行标签含"价"的纯数字加 ¥ 前缀。若与原表显示不符，直接改 data.json 后重跑下游。
- Chrome 截图 window 宽度必须等于 widths.json 的 page_w，高度留余量 1600；底边由 render.py 裁。
- 打印版单页不要塞太多列（用户反馈过"挤、不方便 A4 打印"）：按系列拆页、每页 ≤9 产品列。

## Verification
- 图片：Read 目视（色带齐全、图行完整、合并无错位、价格带 ¥）；PNG 宽 ≥3000px。
- Excel/CSV：用 openpyxl/pandas 读回，抽查行列数与几个单元格、合并区数量。
