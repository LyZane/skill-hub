# skill-hub

千问办公（QwenWork）个人技能仓库。约定：一个技能一个文件夹，文件夹名 = 技能名，内含 `SKILL.md` 与配套 `scripts/`。

本地技能目录 `~/.qwenworkcn/skills/<name>/` 与仓库 `<name>/` 保持同步；改动后提交推送。

## 技能列表
- `yuque-sheet` — 解析语雀表格文档（lakesheet）为结构化数据，支持打印高清图片 / 导出 Excel / CSV / 数据分析。
- `ecom-sku-collector` — 采集电商平台（天猫/淘宝、京东）商品 SKU 数据（名称/价格/库存/图片），支持已打开标签页 / 列表页 / URL 列表三种输入；下游输出 Excel（多 sheet、内嵌图片）/ CSV / 同店跨链接价格一致性核对 / 天猫 vs 京东跨平台比价。前身为 tmall-sku-collector，扩展京东采集后改名。
