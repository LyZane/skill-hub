---
name: jd-review-collector
description: 采集京东商品页（item.jd.com）带图/视频买家评论并做口碑分析：下载评论原图与视频、逐条情感分类与关键词提炼，产出固定风格的交互式 HTML 报告（情感/评分/SKU/关键词/含视频多维筛选、图片灯箱、视频播放、唯一ID可复制）。当用户给出京东商品链接或提到"采集京东评论/评价""评论分析""买家秀下载""竞品口碑"时使用。内置反人机验证策略（默认50条、慢速翻页、逐页本地回传）。
---

# 京东评论采集与分析

对京东商品页「图/视频」评论做限量采集、媒体下载、情感/关键词分析，产出固定模板风格的 HTML 交互报告。

## 默认规则（用户约定，可被当次指定覆盖）

- 只采「图/视频」筛选下的评论；默认 **50 条**（5 页 × 10），采够即停。
- 翻页间隔 3~5.5s 随机；每页**立即 POST 回传本地接收服务**落盘。
- 遇人机验证（页面刷新、注入的 JS 状态丢失）：已回传 **≥20 条** → 用现有数据收尾；<20 条 → 暂停询问用户。
- 不追求全量：平台对带图评论仅开放约 75 页（maxPage），强爬必触发验证。

## 工作流

```
- [ ] 1. 定位标签页/商品ID，建工作目录 <workspace>/jd_<pid>/{incoming,media}，后台启动 receiver
- [ ] 2. 页面注入 scripts/crawl_kit.js；滚到底渲染评论区 → 点 #comment-root .all-btn 开浮层 → 点「图/视频」chip → 清空 __rateReq 并 __mkRun
- [ ] 3. __crawl('media', 5, 50)；轮询 __runStatus()；按验证规则收尾
- [ ] 4. merge_runs.py 合并 → download_media.py 下载媒体
- [ ] 5. 读 review_texts.txt，逐条写 sentiment_keywords.json（agent 亲自分析）
- [ ] 6. build_report.py 用内置模板生成 index.html，交付 outputs/京东评论采集_<pid>/
```

### 关键操作细节

- 注入：用 `javascript_tool` 执行 `scripts/crawl_kit.js` 全文（一次）。接收地址默认 `http://127.0.0.1:18923`，可用 `window.__recvUrl` 覆盖。
- 筛选生效校验：捕获请求 body 含 `"type":"4"`。
- 验证检测：`window.__runStatus` 报 not a function / `__runs` 丢失 = 页面被刷新；改读 `incoming/` 计数收尾。
- 接收服务：`python3 scripts/receiver.py <workdir>/incoming`（后台运行）。

### 情感与关键词分析规范

- 情感四类：**正面 / 负面 / 中性 / 有褒有贬**。含明确吐槽（哪怕轻微，如"偏重""有水流声"）归「有褒有贬」；平淡/不及预期归「中性」。
- 关键词：产品维度短语，逗号分隔（雾量大、静音不扰眠、容量大、加水省心）；吐槽点同样进关键词。
- 产出 `sentiment_keywords.json`：`{"R01": {"sentiment": "...", "keywords": "a,b,c"}, ...}`，key 与 R 序号对应。

### 报告（模板固化，风格功能保持一致）

- 模板 `templates/report.html` 是唯一风格来源，**不要手写新 HTML**；用 `scripts/build_report.py <workdir> <pid> "<商品名>" [短标题]` 注入数据生成。
- 报告功能基线：统计头（条数/图/视频/正面率）、情感光谱、高频关键词 TOP（点击多选筛选，OR 语义）、吐槽点专栏；筛选器含 情感 / 评分 / SKU 下拉单选 / 关键词多选 / 含视频；搜索高亮；排序（顺序/点赞/时间）；图片灯箱（←→/Esc）；视频内联播放；**唯一 ID（commentId）完整展示、点击复制**；相对路径引用 media/，离线可开。

## 唯一 ID 规则

- 优先京东原生 `commentId`（全局唯一）；若缺失则生成稳定 ID（如 `sha1(昵称+时间+文案前80字)` 前 16 位）。
- R01… 序号仅用于行号与媒体文件命名（R{序号}_img{n}.jpg / R{序号}_vid{n}.mp4 / _cover.jpg）。

## 技术事实（踩坑沉淀）

- 旧接口 `club.jd.com/comment/productPageComments.action` 已废弃。新接口 POST `api.m.jd.com/client.action`（`appid=pc-rate-qa&functionId=getCommentListPage`）带 h5st 签名，**只能页面内触发 + XHR hook 截响应**。
- 响应：`result.floors[mId=commentlist-list].data[].commentInfo`；翻页终点 `result.pageInfo.data.hasNextPage/maxPage`。
- commentInfo：userNickName(脱敏)、commentData、commentDate、commentScore、productSpecifications、praiseCnt、replyList(商家回复)、afterComment(追评)；pictureInfoList mediaType=1 图（largePicURL **去 `.dpg` 后缀即原图**）、=2 视频（videoPlayUrl 为 mp4 直链，picURL 封面）。
- 类名带 hash：滚动容器按「浮层内 overflow-y auto/scroll 且 scrollHeight>clientHeight」定位（crawl_kit 已实现）。
- https 页面 fetch `http://127.0.0.1` 属回环豁免；Content-Type `text/plain` 免 CORS 预检。下载媒体带 `Referer: https://item.jd.com/`。

## 依赖

openpyxl 非必需；**Pillow 非必需**（报告不嵌图）；脚本仅用标准库。浏览器侧需 Chrome 已登录京东（用户标签页）。
