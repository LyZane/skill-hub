# 数据目录（共建：摸清一处数据就回写一处）

> 目的：需要任何数据时先查这里——它在哪、有什么字段、批量还是单条、最新能拉到几号、
> 此路不通时备选链是什么。**所有 agent 共同维护**：新表/新列/新端点/时点变化都要回写。
> 取数优先级（用户 2026-11-03 定）：**API > AJAX/XHR > 网页源码解析 > 文件导出 > UI 操作**；
> 前者不通才降级，UI 经验保留在 references 各文件里作兜底。

## 查数顺序（先近后远）

1. **本地库**（`data/*.sqlite3`，秒回，先查这里——多数分析根本不用去平台拉）
2. **API/AJAX 直连**（带登录态 fetch 或开放平台接口）
3. **文件导出**（平台生成报表 → 导入）
4. **UI 页面操作**（AutoGLM，最慢，兜底）

---

## 一、本地已落库数据（SQLite）

查询方式：`.venv/bin/python` + `from app.db import SessionLocal`，或走系统各页面接口。
表定义权威来源：`app/models.py`；水位语义：`app/services/freshness.py`。

### orders（订单主表，一行一单）
`tid`(主订单号,唯一) `status`(平台标准状态) `payment_fen`(买家实付,含运费扣优惠) `post_fee_fen` `total_fee_fen` `discount_fen` `buyer_nick` `buyer_open_uid` `receiver_state/city/district` `seller_memo` `buyer_message` `created` `pay_time` `modified` `end_time` `is_replacement`(补单) `stat_excluded`(剔除统计) `raw`(原始行) `fetched_at`
**粒度**：批量（按日窗/按 tid）。覆盖：近 3 个月按付款时间、更早按创建时间圈单。

### order_items（子订单，一行一个商品）
`tid` `oid`(子订单号) `num_iid`(商品ID) `sku_id` `outer_sku_id`(商家编码,成本匹配键) `outer_item_id` `title` `sku_properties`(规格) `num` `price_fen`(标价) `payment_fen`(子单实付) `cost_snapshot_fen`(默认成本,导入时取好即固定) `cost_snapshot_at` `cost_override_fen`(纠正后成本,优先) `refund_status` `refund_fen` `refund_reason`(退款报表回填) `refund_note`(退款单商家备注)
**粒度**：批量；单条按 tid/oid/outer_sku_id。

### alipay_entries（支付宝账务流水，一行一笔）
`entry_dt` `account_log_id`(支付宝流水号,对账中心查详情用) `alipay_order_no` `biz_order_no`(常为天猫订单号) `biz_type` `category_name`(费用科目) `memo`（付款扣费带订单号，对账锚点） `counterpart` `direction`(收入/支出/不计收支) `amount_fen`(恒正) `balance_fen` `category_id`(自动归类) `manual_category`(人工归类优先) `dedupe_key`(唯一) `bill_date` `raw`
**粒度**：批量逐日。最新到**今天盘中**（游标只记到昨天，见 references/alipay.md）。

### refund_orders（退款单全量，一行一单，导出列一列不丢）
`refund_id`(幂等键) `tid` `outer_sku_id` `item_title` `refund_status` `goods_status`(货物状态,判发货后退款) `after_sale_type`(退货退款/仅退款/换货) `biz_scope`(售中/售后) `return_tracking_no`(退货物流单号,到仓比对键) `return_logistics_co` `buyer_return_time` `apply_time` `finish_time`(归期依据) `refund_amount_fen` `partial_full` `reason`(买家原因) `seller_note`(真实原因常在此) `raw` `updated_at`
**粒度**：批量导出文件。

### promo_daily（万相台日消耗，一行一天）
`stat_date`(唯一) `charge_fen` `raw`(场景级明细：日期+场景+花费)
**粒度**：批量。最新到**昨天**（昨日数次日上午生成）。

### experience_score_daily（体验分，一行一天）
`stat_date`(唯一) `score`(主分0~100) `item_score`(商品质量) `logistics_score` `service_score` `raw` `updated_at`
**粒度**：单条/采样。最新到**昨天**（统计日 T-1）。

### warehouse_returns（仓库售后登记，只留本店单）
幂等键＝`tracking_no`(小写)+`registered_at`；另有 `express_co` `after_sale_no` `online_order_no` `shop_name` `qty` `sku_code`(退货说明解析出的商家编码) `wh_received` `received_at` 等 ~25 列，全列见 `app/models.py`。
**粒度**：批量月度文件。

### 成本与维护域
`skus`（一行一商家编码：`outer_sku_id` 唯一、`cost_fen` 含运费、`kind`＝NULL标准/bundle组合/accessory配件）、`sku_aliases`（错码→标准码映射）、`sku_fallbacks`（无编码兜底：商品+规格）、`sku_cost_history`（调价历史）、`fee_categories`（费用归类规则）、`expenses`（手动杂项费用）、`replacement_orders`（补单登记）。

### 运维域
`sync_runs`（每次同步/导入的 source/status/stats——**判断导入是否真落库就看它**）、`kv`（水位：`wm_orders`/`alipay_bill_last_date`/`promo_last_date`/`experience_last_date`/`wm_refunds`/`wm_warehouse`）、`tokens`（平台授权）。

---

## 二、平台侧数据源与获取链（需要最新数据时）

### 1 · 支付宝账务流水
- **① API 直连（已通，首选）**：`alipay.data.bill.accountlog.query`，批量逐日+分页 200/页，
  最新**今天盘中**。返回字段：`account_log_id`/`alipay_order_no`/`biz_orig_no`(订单号)/`type`/
  `biz_desc`(科目)/`trans_memo`/`other_account`/`direction`/`trans_amount`/`balance`/`trans_dt`。
- ② 离线下载接口（downloadurl.query）：**死路**，未签约无权限。
- ③ 支付宝对账中心页面人工查单：兜底（拿 `account_log_id` 去查详情）。

### 2 · 淘宝订单
- **① TOP API（最优，待软件著作权）**：`taobao.trades.sold.increment.get`，按**修改时间**增量、
  批量分页 100/页、窗口≤90 天，最新**实时**。字段（子单级最全）：tid/status/payment/
  total_fee/post_fee/discount_fee/buyer_nick/created/pay_time/modified/end_time/receiver_*/
  seller_memo/buyer_message + orders.oid/num_iid/sku_id/outer_sku_id/outer_item_id/title/
  sku_properties_name/num/price/payment/refund_status。代码就绪 `app/connectors/taobao_orders.py`。
- **② 千牛文件导出（当前主力）**：批量，最新**今天盘中**。可识别列名（ALIASES）：订单编号/
  子订单编号/付款时间/创建时间/订单状态/宝贝标题/商家编码/宝贝属性/购买数量/单价/
  买家实付金额(子单级)/优惠/邮费/买家会员名/收货地址/订单备注/买家留言/退款状态/退款金额/
  退款原因/商品ID（列名变体全表见 `app/connectors/order_import.py`）。
- ③ 千牛「已卖出宝贝」页面按单号搜索：单条兜底。

### 3 · 万相台推广消耗
- **① TOP API（待软著）**：`taobao.universalbp.new.report.query.account`（账户报表按天含
  charge）+ `...get.can.use.bizcode`；返回结构随版本变化，解析已做容错（`alimama_report.py`）。
- **② 报表文件导出（当前主力）**：批量，最新**昨天**。zip 内 GBK CSV 71 列，导入取
  日期/花费/场景名 三类列（别名：日期·统计日期·投放日期｜花费·消耗·日消耗｜场景名字·场景名称）。
- ③ 报表页肉眼读数：单点兜底。

### 4 · 售后退款单
- **① 千牛退款报表导出（当前唯一自动化）**：批量，最新**今天**（缺省近 90 天截至今天）。
  全字段：退款编号/订单编号/支付宝交易号/订单付款时间/商品sku信息/商品id/宝贝标题/
  退款完结时间/退款申请时间/买家实际支付金额/退款总额/退款状态/货物状态/售后类型/
  退货物流单号/退货物流公司/买家退款原因/退款原因标签/买家退货时间/售中或售后/
  商家备注/部分退款全额退款/审核操作人/客服介入状态/责任方 等 30+ 列（全表见
  `app/connectors/refund_import.py` ALIASES）。
- ② 退款管理页按退款号查：单条兜底。
- ③ 待研究：退款列表页 XHR 直连（未抓包，见台账）。

### 5 · 店铺真实体验分
- **① 趋势弹窗 XHR（最优潜力，待一次抓包）**：整月逐日序列一次请求秒回。
- **② AutoGLM 读页面（当前主力）**：当日一条 + 趋势悬停采样（~9 秒/点）。
- ③ 「指标表现」导出文件：当期 8 项底层考核指标明细（商品负反馈率/48h揽收及时率/旺旺满意度/
  平台求助率等，含分数档标准），**非逐日序列**，暂未入库，日后指标级分析可接。

### 6 · 仓库售后登记
- 月度 xlsx 文件（仓库财务人工转发，唯一来源，无自动化通道）。列见 `warehouse_return_import.py`。

---

## 三、直连研究台账（优雅途径优先，抓到就记）

**抓包方法**：Chrome F12 → Network → 过滤 Fetch/XHR → 在页面做一次目标操作 → 找到返回数据的
请求 → Copy as cURL。**Cookie/签名不入库**，只记：`方法 URL?关键参数 → 响应结构（字段列表）`。

| 目标 | 通道 | 状态 | 下一步 |
|------|------|------|--------|
| 体验分逐月趋势 | 页面 XHR 重放 / `scripts/chrome_exec.sh` 页面内 fetch | **待一次抓包**（2026-11-02 问询未获答复） | 下次补数时再请用户 F12 Copy as cURL；拿到即新增直连连接器，页面读取降为兜底 |
| 淘宝订单 API | TOP 开放平台 | 待软件著作权（docs/04a） | 拿到凭证填 `secrets/secrets.env` 即与导出并行 |
| 万相台消耗 API | TOP universalbp | 同上（代码就绪） | 同上；联调只需改 `_build_report_request/_extract_rows` |
| 退款管理列表 | 页面 XHR | 未研究 | 下次导出退款报表时顺带抓包记录 |
| 万相台报表生成 | 页面 XHR | 未研究 | 若有「生成报表」接口可绕过 UI 直接申请+下载 |
| 千牛已卖出列表 | 页面 XHR | 未研究 | 同上；订单单条查询可比导出快 |

已捕获端点（格式：`方法 URL?参数 → 响应结构`，抓到一个追加一行）：

- （暂无。第一个端点由下次抓包写入。）
