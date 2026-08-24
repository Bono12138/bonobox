# Wiki Connector

让 Agent 在你现有的公司权限范围内，搜索和读取 Confluence Wiki。工具只读，不会编辑、评论或上传页面。

目前是 **Windows 优先的 Beta 版**。我们重点验证了 Windows 本地使用；不同公司的 Confluence 版本、登录方式和网络环境差异很大，所以不保证拿来就能用。安装失败或暂不兼容时，可以让 Agent 先尝试适配，再生成一份已脱敏的 GitHub 反馈。

## 最省事的用法

把下面这段话直接发给你的 Agent：

```text
请打开这个项目并阅读 README.md 和 INSTALL.md：
https://github.com/Bono12138/bonobox/tree/main/tools/wiki-connector

请帮我检查环境、安装工具并运行 doctor。不要让我在聊天里发送密码、Token、Cookie、公司网址或公司资料，也不要绕过公司的安全设置。

如果当前环境不兼容，请先根据实际报错做最小范围的适配并重新测试。无论最终成功还是失败，都运行 feedback，生成一份已删除公司名称、网址、账号、页面内容、搜索词、凭证和本机路径的反馈；先让我检查，再打开 GitHub Issue 页面。修改成功时，请在反馈中说明改了什么，方便项目吸收这个兼容方案。
```

Agent 会按照 [INSTALL.md](INSTALL.md) 完成安装。完整提示词也在 [PROMPT-CARD.md](PROMPT-CARD.md)。

## 两种连接方式

| 方式 | 适合情况 | 本地会留下什么 |
|---|---|---|
| `token` | 公司允许使用 Confluence Personal Access Token 或 API Token | `config.json` 只记录环境变量名；Token 由你放在当前终端的环境变量中 |
| `browser` | 需要在浏览器里完成 SSO、MFA、扫码等登录 | 独立的 `.browser-profile` 会保存在本机，其中可能包含登录会话；不要复制、上传或提交到 Git |

两种方式都只使用你本来拥有的 Wiki 权限。浏览器方式能否适配某种 SSO，取决于实际 Confluence、浏览器和公司登录流程；不能保证支持所有 SSO。

## 自己安装

需要 Python 3.9+。在项目目录中运行：

```powershell
python -m pip install -r requirements.txt
python wiki_connector.py init
python wiki_connector.py doctor
```

`init` 会询问 Wiki 地址和连接方式。不要把 Token 发到聊天里；如选择 `token`，请在本机终端中设置工具提示的环境变量。

检查通过后可以使用：

```powershell
python wiki_connector.py search --query "关键词" --limit 5
python wiki_connector.py read --page-id 123456
python wiki_connector.py history --page-id 123456
python wiki_connector.py status
```

命令输出为 JSON，方便 Agent 判断下一步。

## 出错时怎么反馈

先运行完整检查：

```powershell
python wiki_connector.py doctor
```

再生成本地脱敏报告：

```powershell
python wiki_connector.py report
```

确认报告中没有公司或个人信息后，打开预填的 GitHub Issue：

```powershell
python wiki_connector.py feedback
```

`feedback` 只打开 Issue 页面，不会自动发布。请在提交前再次删除公司名称、Wiki 地址、账号、页面标题和内容、搜索词、Token、Cookie、SQL、内网地址及本机绝对路径。

如果 Agent 修改后成功运行，也请提交反馈：写清原环境、原报错、修改内容和验证结果，项目就能把适配方案整理给更多人。

## 当前边界

- 公开版只提供 Wiki 只读能力。
- Windows 是当前主要支持环境；macOS、Linux 和 Confluence Cloud 仍需更多真实用户验证。
- 已提供 Confluence REST/CQL 和本地浏览器两条路径，但不声称兼容所有 Confluence 版本、反向代理、SSO 或安全策略。
- 工具不会扩大你的权限，也不应被用来绕过网络、身份验证或公司的数据安全要求。
- `doctor` 通过只说明当前连接和基本读操作可用，不代表所有页面和所有查询都能访问。

## 安全

- 不要把 `config.json`、`telemetry.jsonl`、`support-report.json`、`.browser-profile`、Token、Cookie 或真实结果提交到 GitHub。
- 不要让 Agent 在聊天中索要或复述密码、Token、Cookie。
- 浏览器配置目录可能包含有效登录会话，只能留在自己的电脑上。
- 公开 Issue 必须脱敏；不确定时只保存本地报告，不提交。

## 参与适配

真实环境的差异正是这个项目需要的反馈。能用、改后能用、暂时改不了，都可以通过 `feedback` 提交。请只提交可公开的最小复现信息和通用修改，不要上传公司资料或认证信息。

许可证：[MIT](LICENSE)。
