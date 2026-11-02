# 支付宝账单获取（API 直连——唯一已打通的 API 通道）

命令：`.venv/bin/python -c "from app.services.sync import run_sync; run_sync('alipay_bill')"`
（也可设置页手动触发；每日定时由 APScheduler 自动跑，见 `app/services/scheduler.py`）

## 接口与凭证

- 走「商家账单数据查询及下载接口」产品的**在线实时接口** `alipay.data.bill.accountlog.query`。
- 实测（2026-10-27）：**离线下载接口（downloadurl.query）未签约无权限**；在线接口可用且字段
  更全——`account_log_id` 唯一流水 ID（去重键）、`biz_desc` 费用科目、`biz_orig_no` 常为天猫订单号。
- 在线接口**无次数限制**。凭证配置见 `docs/04b-支付宝开放平台申请指南.md`（RSA2 公钥模式，
  `secrets/secrets.env`），申请到可用约 1~2 个工作日。

## 拉取口径（`app/connectors/alipay_bill.py`）

- 按 `trans_dt` 逐日拉 00:00:00~23:59:59 全量，分页 200/页、单日防御上限 1 万笔。
- `sync_bills` 默认从水位次日开始、拉到**今天**（实时接口当日盘中数据可见）。
- **水位游标只推进到昨天**（2026-11-01 起）：今天永远视为未封日，次日例行同步会整日重拉
  今天补全——防止盘中部分数据把游标顶到今天、漏掉晚间流水。所以看到「拉了今天但水位停在
  昨天」是设计如此，不是 bug。
- 去重：优先 `account_log_id`（`log-<id>`），缺失时按 单号|类型|memo|金额|方向|时间 sha1。
- 金额统一取绝对值入库（`amount_fen`），方向看 `direction` 字段。

## 在整个链路里的双重角色

1. 自身是财务收支/看板的数据源；
2. **是订单导出的对账锚点**：付款当天按单扣的「消费者体验提升计划服务费」（memo 带订单号，
   类目 `0170125T|服务费-` 前缀）是「窗口内确实发生过付款订单」的独立证据，`app/services/recon.py`
   用它核对订单表覆盖度。**所以补数据时先同步支付宝，再跑订单导出**，对账才有原料。
   口径注意：该费并非每单都扣（下界探测）；memo 单号合并单=主订单号、单一子单=子订单号，
   须同时匹配 tid ∪ oid。

## 故障排查速查

| 现象 | 处置 |
|------|------|
| `AlipayError: 部分日期失败` | stats 里有 `fail_detail` 逐日原因；网络抖动重跑即可（幂等，upsert） |
| 提示未配置凭证 | `secrets/secrets.env` 缺 ALIPAY_APP_ID/ALIPAY_APP_PRIVATE_KEY，见 docs/04b |
| 想重拉某几天 | 水位只进不退；直接指定日期区间调 `sync_bills(session, client, date_from, date_to)`（upsert 幂等） |
