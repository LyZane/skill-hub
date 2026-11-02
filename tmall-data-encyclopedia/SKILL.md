---
name: tmall-data-encyclopedia
description: 天猫/淘宝店铺数据获取操作手册＋数据目录：从千牛、万相台无界、支付宝开放平台、千牛服务报告页拉取订单明细、推广消耗、售后退款、店铺体验分、账务流水的标准命令、页面操作细节、防呆校验与踩坑总账；并登记各处数据的字段、批量/单条粒度、最新可拉时点与备用获取链。凡涉及拉取/同步/补齐店铺经营数据、导出或导入报表、AutoGLM 驱动 Chrome 取数、对账缺单排查、问「某数据在哪/有什么字段/怎么拿」，或问「数据到哪天了 / 为什么缺数 / 帮我补数据」，一律先读本技能再动手。
---

# 天猫数据获取百科（tmall-data-encyclopedia）

天猫店铺经营数据（订单/推广/退款/体验分/支付宝账单）怎么拉、怎么验证、出问题怎么排——
所有实测经验的结晶。本技能配套一套经营看板系统使用：**所有命令、脚本、代码路径
（`scripts/`、`app/`、`docs/`）均指该看板仓库，须在看板仓库根目录执行**。
**这是一个活技能**：每个用它拉数的 agent 都是维护者，跑出新发现（新坑、更快的路、页面改版）
必须回写本技能（见文末「维护协议」），让下一次拉取更快更稳。

配套的权威文档在看板仓库内（本技能与其保持同步，冲突时以最近实测为准并回改两边）：
`docs/06-数据导入指南.md`、`docs/07-推广消耗自动导出SOP.md`、`docs/09-订单明细自动导出SOP.md`、
看板仓库 `AGENTS.md` 的「补数据清单」。

## 一、数据源地图（先看这张表再动手）

| 源 | 通道 | 最快能拉到 | 标准命令（看板仓库根目录跑） | 成功判据（必核对，退出码 0 不算数） |
|----|------|-----------|--------------------------|-------------------------------------|
| 支付宝账单 | **API 直连（已通）** | **今天盘中**（实时接口） | `.venv/bin/python -c "from app.services.sync import run_sync; run_sync('alipay_bill')"` | 输出 stats 无 `days_fail`；水位=昨天属正常（游标设计如此，见 references/alipay.md） |
| 订单明细 | 千牛导出（AutoGLM） | **今天盘中**（结束日期显式写今天） | `scripts/export_order_report.sh [N\|起 止]` | 导入回执非空行 + 覆盖校验过 + 对账缺失 0；详见 references/orders.md |
| 推广消耗 | 万相台导出（AutoGLM） | **只有昨天**（昨日数据次日上午才生成） | `scripts/export_promo_report.sh [N\|起 止]` | 导入回执非空行；凌晨只拿到前天属正常，别反复重试 |
| 售后退款 | 千牛导出（AutoGLM） | **今天**（缺省近 90 天截至今天） | `scripts/export_refund_report.sh [起 止]` | 必见「退款报表导入完成：N 条」 |
| 店铺真实体验分 | 页面读取（AutoGLM） | **只有昨天**（统计日 T-1） | `scripts/fetch_experience_score.sh` | 必见「体验分导入完成：N 天…」+ `get_watermark('experience')` |
| 仓库售后登记 | 月度文件（人工转发） | 收到文件那天 | 设置 → 数据导入 手动上传 | 导入回执；月更，无需每日补 |

各源水位游标与兜底查询在 `app/services/freshness.py` 的 `SOURCES`。

## 二、标准流程：补数据 / 拉最新

1. **前置检查（必做）**：`curl -sI http://127.0.0.1:8000 | grep -i '^server'` 应为 `uvicorn`。
   是别的进程（如 `python3 -m http.server`）→ 先按看板仓库 AGENTS.md 重启服务，否则浏览器导出全部白跑、
   导入还会静默失败（501）。案例见 references/pitfalls.md #4。
2. **查各源水位**：`freshness.get_watermark`（或看板上「数据水位」页），找出落后的源。
3. **逐源补齐**——不要只补部分源；每个源拉到它**各自**的极限时点（上表），不是统一停到昨天：
   - 支付宝：API 一条命令，随时可跑，最先跑（其他源的对账依赖它）。
   - 订单：拉最新时结束日期显式写今天，如 `scripts/export_order_report.sh 2026-10-28 2026-11-03`。
   - 推广：上午跑才能拿到昨天；凌晨跑脚本会主动报「平台数据未生成」，不要重试。
   - 退款：缺省近 90 天到今天，直接 `scripts/export_refund_report.sh` 即可。
   - 体验分：`scripts/fetch_experience_score.sh`，顺带采当月趋势点。
4. **核对再汇报**：`get_watermark` 逐源复核，汇报时写清「每源覆盖到哪天」。
   对账报「N 笔付款扣费不在订单表」时，先查 `sync_runs` 确认导入真的落库了，再怀疑缺单。

## 三、通用铁律

1. **浏览器脚本共用一个 Chrome 会话，必须串行执行，不能并行**（AutoGLM 会互相抢标签页）。
2. **以回执/库内水位为准，不信退出码**。历史三大静默失败：导入端点 404（refunds→refund）、
   端口被占导入 POST 501、autoglm stdout 提示行污染路径捕获——表象都是「看起来成功了」。
   详见 references/pitfalls.md。
3. **导出成功 ≠ 导入成功**。每步都要看到上表「成功判据」里的回执才算数。
4. 已下载到 `~/Downloads` 的报表文件是资产：导入失败时不必重新导出，重启服务后用
   `curl -F "file=@文件" http://127.0.0.1:8000/settings/import/<orders|promo|refund>` 补导。
5. **优先跑现成脚本，不要手写浏览器任务**。脚本的提示词里已固化全部护栏（半开区间边界、
   严禁下载旧任务、隐私弹窗确认等）。只有脚本坏了才考虑手工 AutoGLM，且必须复用脚本里
   的任务提示词改（各 references 里有）。
6. 拉数结果对用户汇报时用大白话（老妪能解），别说「快照」「游标」这类内部词。

## 四、通道优先级（用户 2026-11-03 定：优雅高效优先）

**取数方式按此优先级选，前者不通才降级；UI 经验保留作兜底，但研究出更优雅的途径是本技能
存在的目的**：

**API 直连 > AJAX/XHR 重放 > 网页源码解析 > 文件导出 > UI 操作（AutoGLM 点点）**

- **API 直连**：支付宝账单已走 `alipay.data.bill.accountlog.query`（实时、无次数限制）。
  订单/推广的 TOP API 因需软件著作权暂缓，代码已就绪（`app/connectors/taobao_orders.py`、
  `alimama_report.py`），拿到凭证即可切换。
- **AJAX/XHR 重放（重点研究方向）**：平台页面自己的数据接口，带登录态 fetch 即得 JSON，
  比浏览器 UI 导出快一个量级。两条现成路：`scripts/chrome_exec.sh`（页面上下文执行 JS，
  两段式异步套路见 references/channels.md）；或 F12 抓包 Copy as cURL 重放。**抓到任何端点
  必须记录到 references/catalog.md 的「直连研究台账」**（Cookie/签名不入库，只记参数与响应
  结构），这是全队共享的直连资产。
- **文件导出**：千牛/万相台的报表导出→导入（当前订单/推广/退款的主力通道，各 references
  有完整操作细节）。
- **UI 操作（AutoGLM）**：驱动真实 Chrome 做与人工相同的操作，最通用但最慢，任何直连不通
  时它都能兜底。环境要求、session pool、task_result.md 取证见 references/channels.md。
- **已证死路**（别再试）：CDP 9222（Chrome 136+ 禁默认 profile 远程调试）、autoglm 页面执行
  JS（无此能力）、agent 客户端内置浏览器（无登录态）。详见 references/channels.md「死路档案」。

## 五、按需深读（references/）

| 文件 | 什么时候读 |
|------|-----------|
| [references/catalog.md](references/catalog.md) | **查数第一站**：某数据在哪（本地库/平台）、有什么字段、批量还是单条、最新到几号、此路不通的备选链；直连研究台账与已捕获端点 |
| [references/orders.md](references/orders.md) | 拉订单；查漏单/对账；订单导出报错 |
| [references/promo.md](references/promo.md) | 拉推广消耗；万相台页面问题 |
| [references/refund.md](references/refund.md) | 拉退款报表（回填退款原因） |
| [references/experience.md](references/experience.md) | 拉体验分；趋势回补；直连研究结论 |
| [references/alipay.md](references/alipay.md) | 支付宝同步口径；水位语义；对账原理 |
| [references/channels.md](references/channels.md) | AutoGLM 用法细节；chrome_exec 快路；API 演进；死路档案 |
| [references/pitfalls.md](references/pitfalls.md) | 任何异常先来这儿对号入座；**新坑也记到这儿** |
| [references/CHANGELOG.md](references/CHANGELOG.md) | 本技能的迭代历史 |

## 六、维护协议（每个使用者的义务）

本技能存在的意义就是「越用越快越稳」，这依赖回写。用完一次拉数任务后，**先对照下面清单
再收尾**：

1. **出新坑了**（脚本失败、页面改版、回执异常、静默失败）→ 排查清楚根因后：
   - 在 `references/pitfalls.md` **顶部**追加一条：`日期 / 现象 / 根因 / 防呆措施`，附取证路径
     （如 `~/.openclaw-autoclaw/sessions/<sid>/task_result.md`、`data/server.log` 摘录）；
   - 同步修正对应源的 reference 文件与脚本/文档（脚本在 `scripts/`，SOP 在 `docs/06/07/09`）。
2. **找到更快的路**（如某源 XHR 抓包成功可直连）→ 更新 `references/channels.md` 的通道状态、
   SKILL.md 第四节排序，并考虑把新通道做成脚本沉淀到 `scripts/`。
3. **摸清了任何一处数据**（新表/新列、平台返回字段、批量还是单条、最新时点变化、备选链
   通断）→ 回写 `references/catalog.md` 对应小节；**抓到任何 XHR 端点记入其「直连研究台账」**
   （Cookie/签名不入库，只记方法/URL/参数/响应结构）。
4. **口径/时点变化**（如平台出数时间提前）→ 更新 SKILL.md 第一节表格与看板仓库 AGENTS.md
   补数据清单。
5. 任何改动在 `references/CHANGELOG.md` 记一行（日期 + 一句话）。
6. 写法要求：一条一坑、给证据、说人话；不删历史记录（含被推翻的结论，标注「已失效」即可，
   死路档案的价值在于防止后人重试）。
7. 技能文件不是运行时代码，改完**无需重启服务**（改了看板仓库的 `scripts/` 或 `app/` 才按其
   AGENTS.md 约定处理并重启）。本技能的权威版本在 skill-hub 仓库，看板仓库经符号链接引用，
   改动落在任一侧都是同一份文件；是否 git 提交遵循当时会话的授权惯例。
