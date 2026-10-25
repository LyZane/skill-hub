---
name: tmall-price-checker
description: 采集天猫/淘宝商品 SKU 价格数据（名称/原价/实付价/库存/图片），支持商家后台出售中列表（本店全店首选）/已打开标签页/列表页/URL 列表四种输入。下游输出 Excel（多 sheet 单工作簿、内嵌图片）/ CSV，核心能力是同店跨链接价格一致性核对（同一真实 SKU 复用到多个链接时排查漏改价）。当用户要求采集天猫商品价格、整理 SKU 价格表、核对各链接价格一致性、排查漏改价时使用。
version: 2.0.0
---

# 天猫 SKU 价格采集与一致性核对

## 第 0 步：采集前自检（必做，不符即停）

开始采集前确认三件事一致，任一不符**立即停止并询问用户**，不得自行猜测数据源继续：

1. **浏览器**：浏览器自动化当前连接的浏览器是否就是用户说的那个（同名扩展可能装在 Chrome/Canary/Edge 多个浏览器里，守护进程同一时刻只绑定一个扩展；用 `find_tab(active:true)` 借标签页，借到的是哪个浏览器的就是哪个）。连接不符时引导用户在目标浏览器启用扩展并重启浏览器，再重试。
2. **账号与店铺**：借到的标签页/后台页显示的登录账号、店铺名是否就是用户口中的"本店"。买家账号的卖家后台出售中为 0 件——发现 0 件先怀疑接错浏览器/账号，而不是店铺真的没商品。
3. **页面**：用户说"当前打开的是 X 页"时，先读取页面确认类型；实际不是 X 页时告知用户并确认真实入口，不要默默改用其他来源凑数。

## 核心流程：输入 → 规范化 data.json

**输入四种形态**：
- **B0 商家后台出售中列表（"本店/全店"首选，最快路径）**：直接 `navigate` 到 `https://myseller.taobao.com/home.htm/SellManage/on_sale/?current=1&pageSize=20`，从 `document.body.innerText` 用正则 `ID:(\d{6,})` 取商品 ID（同时可取标题），翻页改 `current` 参数直到取满（页头有"共N件商品x/y"）。**不要走店铺前台**（category.htm/search.htm 新版装修页渲染不稳定，反复刷新易触发风控变空页）。拿到 ID 列表后逐个打开详情页采集。
- **A 已打开的详情标签页**：`tabs_context` 过滤 `item.htm?id=`（天猫/淘宝）标签页，直接复用。
- **B 列表页**（店铺全部宝贝/搜索结果）：先滚动加载完毕，`javascript_tool` 执行 `scripts/extract_links.js` 全文取商品 URL 列表，再逐个打开（已有同 URL 标签页则复用，否则 `tabs_create_mcp` + `navigate`）。
- **C 用户给的 URL 列表**：同 B 逐个打开。

详情页只认 detail.tmall.com / item.taobao.com，同一批可混合。

每个商品：在其标签页 `javascript_tool` 执行 `scripts/extract_tmall_sku.js` 全文，聚合为工作目录 `data.json`。

### 适配器
- `scripts/extract_tmall_sku.js` — 读 `window.__ICE_APP_CONTEXT__.loaderData.home.data.res`：`skuCore.sku2info`（价格/库存）+ `skuBase.props/skus`（规格名/图）。一个链接多个 SKU。

### data.json schema（统一）
```json
{
  "collectedAt": "YYYY-MM-DD", "platform": "tmall", "shop": "店铺名",
  "items": [{
    "platform": "tmall", "itemId": "商品ID", "title": "标题", "url": "链接",
    "shop": "店铺名",
    "rows": [{
      "skuId": "...", "skuName": "规格名（多属性用 + 连接）",
      "listPrice": "标价/划线价", "promoPrice": "实付价（店铺优惠后）",
      "quantity": 库存或null,
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

## 下游 C：数据分析
直接读 data.json 聚合（各链接价格带、真实 SKU 分组统计），按需输出结论。

## 一致性核对口径（内置于 build_report.py）
- 同一 SKU 图片 URL = 同一真实 SKU（卖家常把同一真实 SKU 复用到多个链接承接流量）。
- 基准价 = 各链接实付价的众数；原价或实付价偏离即标红，并给出建议实付价。
- 疑似同 SKU 提示：同容量且归一化名称相似度 ≥0.8 但图片不同；排除 wifi 有无、旋钮/触控、颜色差异。

## Pitfalls
- 必须在用户已登录的 Chrome 标签页内执行；不要用 requests/无头浏览器抓详情页（反爬空壳）。
- 天猫 `window.__ICE_APP_CONTEXT__` 不存在 = 未加载完或旧框架：刷新重试，仍失败如实告知，不得编造数据。
- 天猫 skuId "0" 是整品默认行（起步价，可能带"起"字），跳过；多属性 propPath 形如 `pid:vid;pid:vid`。
- **单规格商品（滤网/配件/运费补差链接等）`skuBase.skus` 为空数组**，价格库存挂在 `skuCore.sku2info["0"]` 上：采为一行 `skuId:"0", skuName:"默认规格（无多SKU）"`，image 留空。
- **部分 SKU 行 `subPrice` 为空**（无促销时实付价=标价）：build_report.py 对 `promoPrice=None` 会抛 TypeError，聚合 data.json 时把空 promoPrice 回填为 listPrice。
- 价格为采集时点页面快照，会随促销变动；Excel 内嵌图片浮于单元格上，排序/筛选后不随行。
- 列表页取链接前务必滚动/翻页加载完；extract_links 返回 0 条时退回正则 `[?&]id=\d+` 扫页面文本。

## Verification
- openpyxl 读回工作簿：核对各 sheet 行数、内嵌图片数、冲突/标红单元格。
- 天猫去重图片数通常≈真实 SKU 数。
