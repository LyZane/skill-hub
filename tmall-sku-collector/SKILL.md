---
name: tmall-sku-collector
description: 采集天猫/淘宝商品详情页的 SKU 数据（名称/原价/实付价/库存/图片）并做跨链接价格一致性核对。当用户提供已打开的商品标签页、商品列表页或 URL 列表，要求采集 SKU 价格、整理商品价格表、核对/检查各链接价格一致性、排查漏改价时使用。核心能力：浏览器标签页注入解析页面数据 → 规范化 SKU JSON → Excel（多 sheet 单工作簿、内嵌图片）/ CSV / 一致性分析等多种下游输出。
version: 1.0.0
---

# 天猫/淘宝商品 SKU 采集与价格一致性核对

## 核心能力：详情页 → 规范化 SKU JSON（所有下游的第一步）

输入三种形态，先统一归一到 `data.json`：

- **A 已打开的详情标签页**：`tabs_context` 过滤 URL 含 `item.htm?id=` 的标签页，直接复用。
- **B 列表页**（店内全部宝贝/搜索结果/卖家后台商品管理等）：在该标签页先滚动加载完毕，再 `javascript_tool` 执行 `scripts/extract_links.js` 全文拿商品 URL 列表；随后逐个打开（已有同 URL 标签页则复用，否则 `tabs_create_mcp` + `navigate`）。
- **C 用户给的 URL 列表**：同 B 逐个打开。

每个商品：在其标签页 `javascript_tool` 执行 `scripts/extract_sku.js` 全文，返回单个 item 的 JSON；聚合所有 item 保存为工作目录 `data.json`。

### data.json schema
```json
{
  "collectedAt": "YYYY-MM-DD",
  "shop": "店铺名（可为空）",
  "items": [{
    "itemId": "商品ID", "title": "商品标题", "url": "详情页链接",
    "rows": [{
      "skuId": "...", "skuName": "规格名（多属性用 + 连接）",
      "listPrice": "优惠前标价", "promoPrice": "店铺优惠后价",
      "quantity": 库存数, "image": "SKU图URL"
    }]
  }]
}
```

## 下游 A：Excel（默认，多 sheet 单工作簿，勿拆多文件）
1. （需内嵌图时）`python3 scripts/download_images.py data.json imgs/` — 按 URL 去重下载 + 压缩为 160px 缩略图 + 生成 `manifest.json`。
2. `python3 scripts/build_report.py data.json out.xlsx --manifest imgs/manifest.json [--shop 店铺名]`
   - 输出 4 个 sheet：SKU明细（内嵌图、标题超链接）/ 商品汇总（主图+价格带）/ 核对总览（一致性判定+疑似同SKU提示）/ 差异明细（偏离价标红）。
   - 依赖 openpyxl/pillow：本机不保证预装，先 `import` 验证，缺则 `pip install`。

## 下游 B：CSV
`python3 scripts/to_csv.py data.json out.csv` — 明细行展平，Excel/pandas 直接可读。

## 下游 C：数据分析
直接读 data.json 聚合（各链接价格带、真实 SKU 分组统计、改价前后对比等），按需输出结论。

## 一致性核对口径（已内置于 build_report.py）
- **同一 SKU 图片 URL = 同一真实 SKU**（卖家常把同一真实 SKU 复用到多个链接承接流量，SKU 图不变）。
- 基准价 = 各链接实付价的众数；原价或实付价偏离众数即标红，并给出"建议实付价"。
- 疑似同 SKU 提示：同容量（如 13L）且归一化名称相似度 ≥0.8 但图片不同；排除 wifi 有无、旋钮/触控、颜色差异（这些本就是不同 SKU）。

## Pitfalls
- 必须在用户已登录的 Chrome 标签页内执行；不要用 requests/无头浏览器抓详情页（反爬会拿到空壳）。
- `window.__ICE_APP_CONTEXT__` 不存在 = 页面未加载完或旧版框架：先刷新标签页重试；仍失败则如实告知用户，不得编造数据。
- skuId "0" 是整品默认行（起步价，可能带"起"字），聚合时跳过；多属性商品 propPath 形如 `pid:vid;pid:vid`。
- 价格为采集时点的页面展示快照（原价=「优惠前」，实付价=「店铺优惠后」），会随促销变动；报告里注明采集时间。
- 列表页取链接前务必滚动/翻页加载完；extract_links 返回 0 条时退回正则 `[?&]id=\d+` 扫页面文本。
- Excel 内嵌图片浮于单元格上方，排序/筛选后图片不随行移动，需提醒用户。

## Verification
- openpyxl 读回工作簿：核对各 sheet 行数、内嵌图片数、冲突状态与标红单元格。
- 去重后的图片数通常≈真实 SKU 数，可与用户口径互相印证；分组异常时优先检查图片 URL 归组。
