---
name: tmall-store-report
description: 采集天猫卖家后台出售中商品的销售、用户评价（含图片/追评/商家回复）与问大家问答数据，全程浏览器模拟人工点击、不调后端接口，生成左侧主图导航的交互式 HTML 总览（按累计销量降序、标题新标签打开详情页），并自动校验商品主图链接是否 404、过滤运费/补差/滤网/配件等非实物商品。当用户提到天猫商品数据、重新生成商品总览、采集天猫评论/评价、问大家、检查商品链接或主图是否有效时使用。
---

# 天猫在售商品数据总览

## 数据目录约定

在工作区建 `tmall_data/`，存放四类 JSON（采集产物），报告由 `scripts/build_report.py` 生成：

- `products.json`：`[{id,title,img,price,stock,cum_sales,sales_30d}]`（img 为去掉 `_100x100xz_.webp` 后缀的原图 URL）
- `reviews_part*.json`：`{ "<id>": {sold, rc, comments:[{user,meta,content,imgs,append,appendImgs,reply}]} }`，可分多个 part 文件
- `wdj_raw.json`：`[{id,q,asker,time,shown}]`，shown 为"查看回答"抽屉原文（含 `展开 <内容> <谁>于 <时间> 回答 <id>` 片段）

## 流程 A：全量重新采集（浏览器模拟点击，禁调 mtop/后端接口）

### A1 商品列表（卖家后台 qn.taobao.com 出售中页）

翻页用 computer 点击分页右箭头；每页用 javascript_tool 提取（`tr.next-table-row`）：
链接取 id，`td` 顺序为 标题/价格/库存/累计销量/30日销量。字段见 products.json 约定。

### A2 评论（每个商品，详情页）

1. `navigate` 到 `https://detail.tmall.com/item.htm?id=<id>`
2. JS 取 `已售`、`用户评价 · N`，对"查看全部评价"叶子节点 `scrollIntoView` 后返回中心坐标
3. computer 点击该坐标打开抽屉
4. JS 提取（抽屉 `div[class^="Drawer"]`，条目 `div[class^="Comment--"]`，最多 20 条）：
   user=`userName--`，meta=`meta--`，content=`contentWrapper--` 下首个 `content--`，
   主图=`contentWrapper--` 内 `album-- img` 且不在 `append--` 内，追评=`append--` innerText 及其 img，回复=`reply--`。
   img 的 src 补 `https:` 并去掉 `_\d+x\d+.*$` 尺寸后缀。无"查看全部评价"按钮则 comments=[]。

### A3 问大家（PC 详情页无此模块！用卖家后台）

1. `navigate` `https://myseller.taobao.com/home.htm/comment-manage/ask-all?current=1&pageSize=100`（首次有"我知道了"弹窗，JS 点掉）
2. JS 提取 43 行式列表：每行取 `a[href*="item.htm"]` 的 id/title，行内文本解析 问题/提问人/时间/`暂无回答可展示`
3. 有回答的行需点"查看回答"读抽屉。**后台标签处于 hidden 时 setTimeout 被节流**，用 `fetch('data:text/plain,')` 作微等待。注入 helper 后 fire-and-forget 启动循环、轻量轮询 `saved` 计数（页面 JS 在工具超时后仍继续跑）：

```js
const tick = () => fetch('data:text/plain,').then(()=>{});
// grab(i): 关旧抽屉→点第 i 个"查看回答"→tick 轮询抽屉→读"已展示回答/卖家回答"两 tab 的 table innerText→关抽屉；结果存 window.__wdjRes[i]
// 启动: window.__wdjRun(idxs) 内部 for 循环 await grab；工具调用只返回 'started'，之后轮询 Object.keys(__wdjRes).length
```

4. 完成后分块取回 `__wdjAll` 与 `__wdjRes`，合并写 `wdj_raw.json`（shown 取 res.shown）

### 坑位备忘

- javascript_tool 单次调用保持 <4s；长任务用 fire-and-forget + 轮询
- navigate 会激活标签；hidden 标签定时器节流 6 倍以上
- 录入 img URL 易抄错字符 → 必须做链接校验（流程 B 自动做）

## 流程 B：重新生成报告 + 链接基础检查

```bash
python3 scripts/build_report.py --data-dir <tmall_data> --out <输出.html>
```

脚本自动：过滤标题含 运费/补差/非实物/滤网/配件 的商品（`--exclude` 可改）；按 cum_sales 降序；
**逐张 HTTP 校验主图**：404 → 打印 BROKEN 列表并以退出码 2 结束（先修 products.json 再重跑），其它网络错误仅警告；
生成 HTML：左侧主图导航（销量/评论/问大家角标）、右侧 用户评价/问大家 双 tab、评论图灯箱、标题链接新标签打开详情页。
