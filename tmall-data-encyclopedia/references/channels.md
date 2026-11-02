# 自动化通道：AutoGLM、chrome_exec、API（含死路档案）

## 通道 1：AutoGLM 浏览器代理（当前主力）

驱动**真实 Chrome**（扩展通道，带用户登录态）完成与人工完全相同的页面操作。原则：凡操作
商家后台，一律走这种带登录态的 Chrome 通道；agent 客户端自带的内置/无头浏览器没有登录态，
不要用。

**环境（一次性）**：
1. Chrome 装好 [AutoGLM 扩展](https://chromewebstore.google.com/detail/autoglm/jelniggicmclhfgnlapbkgfibmgelfnp)
2. Chrome 已登录千牛（`qn.taobao.com`）与万相台（`one.alimama.com`）
3. `~/.openclaw-autoclaw/config.json` 已确认浏览器偏好/信任模式
4. `autoglm` 命令在 `~/.local/bin`（脚本会自动加 PATH）

**调用套路**（各导出脚本已封装，手工兜底时照抄）：
- `autoglm run --task "<任务描述>" --tab-id <id>`（复用标签页）或 `--start-url <url>`（新开）
- 标签页复用：从 `~/.openclaw-autoclaw/session_pool.json` 按 URL 关键字找 tabId——省去重新
  加载与登录，且多脚本共用一个 Chrome **必须串行**。
- 任务提示词必备三件套（血泪换来的）：
  1. **严禁下载旧任务**（标签页停在记录页时会直接下旧报表，2026-10-31 实测 2 个动作就把
     空报表又下一遍）；
  2. **日期边界写法**（结束日期=结束日的下一天 00:00:00，半开区间）；
  3. **日历操作描述**（点日期框弹日历、点头部年月展开年月选择器、Escape 关划词悬浮层）。
- **stdout 污染坑**：autoglm ≥1.1.8 长任务（≥20 步）会往 stdout 打 `cat .../task_result.md`
  提示行——凡 `FILE=$(autoglm run ...)` 捕获输出的写法必须 `>&2` 重定向。
- 取证：每步截图在 `~/.openclaw-autoclaw/sessions/<session_id>/task_result.md`；stdout 里有
  session id 可精确定位，按 mtime 找最新是兜底。

## 通道 2：chrome_exec.sh（页面 JS 直连，快路）

`scripts/chrome_exec.sh <url关键字> <js文件> [兜底URL]`——osascript → Chrome
「execute javascript」（需 Chrome 菜单 视图→开发者→允许来自 Apple 事件的 JavaScript 已开，
首次 macOS 弹一次授权）。带登录态、同源 Cookie，可直接 fetch 页面自己的 XHR 接口拿 JSON，
**比 UI 导出快一个量级**。

AppleScript 已踩平的坑（改脚本时别回退）：
- 用 shell `cat` 读 JS 文件（`read as «class UTF8»` 在新 macOS 返回 data 报 -1700）；
- tab 对象没有 index 属性（-1728），定位用循环内保留的 tab 引用；
- `execute javascript` 只回**同步**结果——异步 fetch 用两段式：第一段发请求把结果挂
  `window.__x`，sleep 后第二段读 `window.__x`。

待落地机会：体验分「每月趋势」XHR 直连（等一次抓包，见 references/experience.md）。

## 通道 3：平台 API（支付宝已通；订单/推广暂缓）

| 源 | 接口 | 状态 |
|----|------|------|
| 支付宝账单 | `alipay.data.bill.accountlog.query` | **已通**，实时无限制（references/alipay.md） |
| 淘宝订单 | `taobao.trades.sold.increment.get`（按修改时间增量，窗口上限约 90 天） | 代码就绪（`app/connectors/taobao_orders.py`），**需软件著作权**创建应用，暂缓；申请步骤 docs/04a |
| 万相台推广 | `taobao.universalbp.new.report.query.account` 等 | 代码就绪（`app/connectors/alimama_report.py`，返回结构做了容错解析），同样等 TOP 凭证 |

拿到 TOP 凭证后：填 `secrets/secrets.env` 重启即与导出通道并行，订单/推广可逐步从浏览器
导出切换到 API（更快更稳），浏览器导出降级为兜底。这是本技能「越来越快」的最大跳变点。

## 死路档案（已实测证伪，别再花时间试）

| 路 | 结论 |
|----|------|
| Chrome DevTools 协议（CDP 9222） | Chrome 136+ 禁止默认用户数据目录开远程调试，端口上只有空壳 404；独立 profile 又没登录态 |
| AutoGLM 页面内执行 JS | 动作集只有 navigate/click/type/extract_content 等，无 execute-js |
| agent 客户端内置浏览器 | 没有商家后台登录态，无法用于千牛/万相台。若所用客户端日后提供「连接本机 Chrome 扩展」的后端，在带登录态页面执行 JS（如 playwright.evaluate）是比抓包更顺的直连路径 |
| 万相台「昨日」数据凌晨拉 | 平台次日上午才生成；脚本已加护栏报「平台数据未生成」，重试无意义 |
| 支付宝离线下载接口 | 未签约无权限，用在线实时接口替代 |
