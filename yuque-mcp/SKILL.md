---
name: yuque-mcp
description: 通过 yuque MCP 服务器操作语雀（知识库、目录分组、文档、小记、搜索）。当用户提到语雀、在语雀创建分组/文档、整理知识库目录、读取或搜索语雀内容时使用。包含 MCP 接入配置、目录（TOC）操作标准流程与 429 限流处理办法。优先使用本技能而非浏览器自动化操作语雀。
---

# 语雀 MCP 使用指南

## 接入配置

QwenWork 自定义 MCP 名称建议为 `yuque`，启动方式 `npx -y yuque-mcp@latest`，环境变量 `YUQUE_TOKEN` 与 `YUQUE_PERSONAL_TOKEN`（同值）。

令牌获取与安全检查：

1. 令牌在语雀「账户设置 → 开发者设置 → API Token」（https://www.yuque.com/settings/tokens）创建。
2. 严禁把令牌明文写进技能文件、文档或对话产物。
3. 优先复用本机已有配置中的令牌（如 `~/.codex/config.toml`、`~/.claude/settings.json` 等编辑器 MCP 配置里的 yuque 段）；没有再向用户索取。

若 MCP 未接入（工具列表搜 `yuque` 为空），通过 QwenWork 连接器添加：

```
qw_action: key=qwenwork.settings.connector.custom, action=add,
params={ name:"yuque", config:{ command:"npx", args:["-y","yuque-mcp@latest"],
  env:{ YUQUE_TOKEN:"<token>", YUQUE_PERSONAL_TOKEN:"<token>" } } }
```

接入后工具名为 `mcp__yuque__yuque_*`。

## 工具速览

- 用户/知识库：`yuque_get_user`、`yuque_list_books`、`yuque_get_book`、`yuque_create_book`、`yuque_update_book`
- 文档：`yuque_list_docs`、`yuque_get_doc`、`yuque_create_doc`、`yuque_update_doc`
- 目录：`yuque_get_toc`、`yuque_update_toc`
- 搜索：`yuque_search`
- 小记：`yuque_list_notes`、`yuque_get_note`、`yuque_create_note`、`yuque_update_note`
- 画板资源：`yuque_get_resource`、`yuque_create_resource`、`yuque_update_resource`

所有 `repo_id` 参数均可传 namespace 字符串（形如 `用户名/知识库slug`，可从 `yuque_list_books` 或 `yuque_search` 获取）。

## 标准工作流：建分组 + 存文档

1. `yuque_get_toc` 取目录，找到父节点 `uuid`。
2. 建分组（TITLE 节点）：

   ```json
   {"action":"appendNode","action_mode":"child","target_uuid":"<父节点uuid，根级用空串>","type":"TITLE","title":"<分组名>"}
   ```

   返回完整目录，从中读取新分组 `uuid`。
3. `yuque_create_doc`（`repo_id`、`title`、`body`、`format:"markdown"`、`public:0|1`）创建文档。注意：新文档节点默认挂在目录**根级**。
4. 在目录返回中找到该 doc 节点 `uuid`，移动进分组：

   ```json
   {"action":"appendNode","action_mode":"child","target_uuid":"<分组uuid>","node_uuid":"<doc节点uuid>"}
   ```

5. 文档链接格式：`https://www.yuque.com/<namespace>/<slug>`（slug 取自 create_doc 返回）。

## 坑位与注意

- `yuque_update_toc` 的 `toc_data` 是**单操作 JSON 字符串**，不是数组；一次调用只做一件事。
- 直接用 `doc_ids` 新建 DOC 节点会落到根级，必须按第 4 步用 `node_uuid` 移动。
- 限流：令牌级 429（Too Many Requests），多为其他会话/工具耗尽配额，重置窗口小时级。诊断：匿名请求返回 401 = 仅鉴权问题；带令牌 429 = 限流。处理：等待重置后重试，或换新令牌。
- 操作语雀优先走 MCP，不要用浏览器自动化。
