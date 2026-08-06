---
name: ecom-sku-collector
description: 采集电商平台商品 SKU 数据（名称/原价/实付价/库存/图片）：天猫/淘宝详情页、京东详情页，支持已打开标签页/列表页/URL 列表三种输入。下游支持 Excel（多 sheet 单工作簿、内嵌图片）/ CSV / 同店跨链接价格一致性核对 / 跨平台（天猫 vs 京东）比价分析。当用户要求采集商品价格、整理 SKU 价格表、核对各链接价格一致性、排查漏改价、竞对比价时使用。
version: 1.0.0
---

# 电商 SKU 采集与价格分析（天猫/京东）

## 核心流程：输入 → 平台路由 → 规范化 data.json

**输入三种形态**：
- **A 已打开的详情标签页**：`tabs_context` 过滤 `item.htm?id=`（天猫/淘宝）或 `item.jd.com` 标签页，直接复用。
- **B 列表页**（店铺全部宝贝/搜索结果/后台商品管理）：先滚动加载完毕，`javascript_tool` 执行 `scripts/extract_links.js` 全文取商品 URL 列表，再逐个打开（已有同 URL 标签页则复用，否则 `tabs_create_mcp` + `navigate`）。
- **C 用户给的 URL 列表**：同 B 逐个打开。

**平台路由**（按域名）：detail.tmall.com / item.taobao.com → 天猫适配器；item.jd.com → 京东适配器。同一批可混合采集，data.json 用 `platform` 字段区分。

每个商品：在其标签页 `javascript_tool` 执行对应脚本全文，聚合为工作目录 `data.json`。

### 适配器
- `scripts/extract_tmall_sku.js` — 读 `window.__ICE_APP_CONTEXT__.loaderData.home.data.res`：`skuCore.sku2info`（价格/库存）+ `skuBase.props/skus`（规格名/图）。一个链接多个 SKU。
- `scripts/extract_jd_item.js` — 解析渲染后 DOM：`.page-right-price`（主价格 + 口径标签 + 划线价）、`.specification-item-sku`（规格选项+缩略图）、`.sku-title-name`、`a[href*=mall.jd.com]`（店铺）。京东规格变体是独立商品页，每页采一个 SKU。

### data.json schema（统一）
```json
{
  "collectedAt": "YYYY-MM-DD", "platform": "tmall|jd|mixed", "shop": "店铺名",
  "items": [{
    "platform": "tmall|jd", "itemId": "商品ID", "title": "标题", "url": "链接",
    "shop": "店铺名", "commentCount": "评价数（京东可选）",
    "rows": [{
      "skuId": "...", "skuName": "规格名（天猫多属性用 + 连接；京东=选中的变体名）",
      "listPrice": "标价/划线价", "promoPrice": "实付价（天猫=店铺优惠后，京东=到手价）",
      "priceTag": "价格口径（京东：到手价/补贴价…）", "quantity": 库存或null,
      "image": "SKU图URL"
    }]
  }]
}
```

## 下游 A：Excel（默认，多 sheet 单工作簿，勿拆多文件）
1. （需内嵌图时）`python3 scripts/download_images.py data.json imgs/` — 按 URL 去重下载 + 160px 缩略图 + manifest.json。
2. `python3 scripts/build_report.py data.json out.xlsx --manifest imgs/manifest.json [--shop 店铺名]`
   - 输出 4 个 sheet：SKU明细 / 商品汇总 / 核对总览（同店跨链接一致性判定）/ 差异明细（偏离众数价标红）。
   - 依赖 openpyxl/pillow：先 `import` 验证，缺则 `pip install`。

## 下游 B：CSV
`python3 scripts/to_csv.py data.json out.csv` — 明细行展平。

## 下游 C：跨平台比价（天猫 vs 京东）
`python3 scripts/build_compare.py <tmall_data.json> <jd_data.json> <out.xlsx> [--manifest imgs/manifest.json]`
- 天猫侧按"SKU 图片 URL 相同 = 同一真实 SKU"归组取众数实付价；京东侧每链接即一个 SKU。
- 自动匹配规则：标题归一化后相似度 + 容量(如13L)与配置关键词（WiFi/触控/机械/无雾/冷热雾）重合度打分，输出匹配置信度，低置信度行标黄待人工复核。
- Sheet：比价总览（天猫价/京东价/差额/谁更低/置信度）、待复核与未匹配。

## 下游 D：数据分析
直接读 data.json 聚合（各链接价格带、真实 SKU 分组统计、竞对价格带分布），按需输出结论。

## 一致性核对口径（内置于 build_report.py）
- 同一 SKU 图片 URL = 同一真实 SKU（卖家常把同一真实 SKU 复用到多个链接承接流量）。
- 基准价 = 各链接实付价的众数；原价或实付价偏离即标红，并给出建议实付价。
- 疑似同 SKU 提示：同容量且归一化名称相似度 ≥0.8 但图片不同；排除 wifi 有无、旋钮/触控、颜色差异。

## Pitfalls
- 必须在用户已登录的 Chrome 标签页内执行；不要用 requests/无头浏览器抓详情页（反爬空壳）。
- 天猫 `window.__ICE_APP_CONTEXT__` 不存在 = 未加载完或旧框架：刷新重试，仍失败如实告知，不得编造数据。
- 京东接口（api.m.jd.com pc_detailpage_wareBusiness）带 h5st 签名，不要尝试复现，只解析渲染后 DOM。
- 京东价格口径不统一（到手价/补贴价/PLUS价），保留 priceTag 字段；补贴价可能无划线原价。京东价格受登录账号与收货地区影响，报告注明采集时点。
- 京东规格选项里可能有「团购优选 咨询享优惠」类询价占位项，不是真实 SKU。
- 天猫 skuId "0" 是整品默认行（起步价，可能带"起"字），跳过；多属性 propPath 形如 `pid:vid;pid:vid`。
- 价格为采集时点页面快照，会随促销变动；Excel 内嵌图片浮于单元格上，排序/筛选后不随行。
- 列表页取链接前务必滚动/翻页加载完；extract_links 返回 0 条时退回正则 `[?&]id=\d+` 扫页面文本。

## Verification
- openpyxl 读回工作簿：核对各 sheet 行数、内嵌图片数、冲突/标红单元格。
- 天猫去重图片数通常≈真实 SKU 数；京东每页恰有一个选中变体。
- 比价表抽查 3~5 对匹配是否符合容量/配置语义，低置信度行必须提示用户复核。
