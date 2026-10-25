# skill-hub

通用 Agent 技能仓库（客户端无关，任意支持技能 / MCP 的 agent 客户端均可使用）。约定：一个技能一个文件夹，文件夹名 = 技能名，内含 `SKILL.md` 与配套 `scripts/`。

**在线使用手册（GitHub Pages）：<https://lyzane.github.io/skill-hub/>** —— 卡片式技能总览、完整技能说明、示例提示词一键复制。

本地技能目录（所用客户端的技能安装目录，如 `~/.qwenworkcn/skills/<name>/`、`~/.codex/skills/<name>/`、`~/.claude/skills/<name>/`）与仓库 `<name>/` 保持同步；改动后提交推送。

## 维护约定（所有维护者含任意 agent 均须遵守）

- **客户端解耦**：技能内容必须与具体 agent 客户端解耦。`SKILL.md`、metadata、scripts 中不得写入具体客户端名称及其专属工具名、配置键或私有路径，统一用通用能力表述（如"浏览器自动化""文件交付""在客户端的 MCP 配置中添加"）。确需说明客户端差异时，以通用格式（如 `mcpServers` JSON / stdio TOML）为准，各客户端差异只作为并列示例列举，不得把任一客户端当作默认环境。
- **敏感信息禁入**：令牌、cookie、账号 ID、私有知识库 namespace 等一律以 `<占位符>` 书写，不得明文进入仓库。
- **示例提示词必备**：新技能入库必须同时提交 `EXAMPLES.md`（典型场景的示例提示词）。写法要求：只说任务与输入，不复述技能内部处理逻辑（避免冗余和口径冲突）；可变信息一律用 `<尖括号>` 占位符；头部附「使用 <技能名> 技能：」显式触发兜底说明。
- **手册同步**：新增/修改技能的 `SKILL.md`、`EXAMPLES.md`、`icon.svg` 后，在 `scripts/build_docs.py` 的 `CATEGORIES` 中补登记（仅新增技能时），运行 `python3 scripts/build_docs.py`（依赖 `pip3 install markdown`）并将 `docs/` 一并提交推送。

## 技能列表

### 电商 · 数据采集

- <img src="tmall-review-report/icon.svg" width="18"> **天猫评价采集报告** `tmall-review-report` —— 采集天猫商品评价与问大家，生成主图导航的交互式 HTML 口碑总览。
- <img src="tmall-price-checker/icon.svg" width="18"> **天猫价格核对** `tmall-price-checker` —— 采集 SKU 价格输出 Excel/CSV，核对同店跨链接价格一致性。
- <img src="jd-review-collector/icon.svg" width="18"> **京东评论采集分析** `jd-review-collector` —— 采集京东带图/视频买家评论，情感分类 + 关键词提炼，产出交互式洞察报告。

### 电商 · 经营报表

- <img src="tmall-sales-to-warehouse-reconciliation/icon.svg" width="18"> **天猫销售仓库对账** `tmall-sales-to-warehouse-reconciliation` —— 清洗订单、分离补单，生成五个工作表核对仓库出库、退货与净销量。
- <img src="tmall-monthly-business-report/icon.svg" width="18"> **天猫月度经营报表** `tmall-monthly-business-report` —— 生成月度经营报告 Excel：订单拆分、利润核算、平台费用汇总，全公式化输出。

### 语雀

- <img src="yuque-sheet/icon.svg" width="18"> **语雀表格解析** `yuque-sheet` —— 解析语雀表格文档为结构化数据，支持导出 Excel / CSV / 高清图片 / 数据分析。
- <img src="yuque-mcp/icon.svg" width="18"> **语雀 MCP 操作** `yuque-mcp` —— 通过 yuque MCP 服务器操作语雀：知识库、目录分组、文档、小记、搜索。

### 办公工具

- <img src="invoice-organizer/icon.svg" width="18"> **发票整理** `invoice-organizer` —— 按用途、金额和销售方品牌整理发票，删除确认重复项并汇报统计。
- <img src="picture-slicer/icon.svg" width="18"> **图片切割器** `picture-slicer` —— 把超长图片裁成编号分片，支持按 PSD/PSB 参考线精确切分。

各技能目录下的 `EXAMPLES.md` 提供典型场景的示例提示词，复制后替换占位符即可发给 agent 使用；在线手册中的示例支持一键复制。
