# 给 Agent 的安装与适配说明

用户把这个项目交给你后，请完成安装、真实检查和反馈。目标不是只把依赖装上，而是让用户能够实际搜索和读取一篇其本人有权访问的 Wiki 页面。

## 必须遵守

- 不要要求用户在聊天中发送密码、Token、Cookie、公司网址、页面内容或公司资料。
- 不要关闭证书校验、绕过 SSO/MFA、导出浏览器 Cookie，或扩大用户权限。
- 不要把 `config.json`、`.browser-profile`、`telemetry.jsonl`、`support-report.json` 上传到 GitHub。
- 只做当前环境需要的最小修改；修改前保留清晰 diff，修改后重新测试。
- 无论成功或失败，都生成脱敏反馈，但只在用户检查后才由用户提交 Issue。

## 1. 检查环境

在本项目目录执行：

```powershell
python --version
python -m pip install -r requirements.txt
python wiki_connector.py --version
```

要求 Python 3.9+。当前公开版以 Windows 为主要支持环境。浏览器通道还需要本机安装 Chrome、Edge 或 Chromium。

## 2. 选择连接方式

只需确认两件事：Wiki 登录页面地址，以及公司是否允许使用 Confluence Personal Access Token/API Token。提醒用户可以在 `init` 的本机终端提示中填写地址，不必发到聊天里。

- 允许使用 Token：选择 `token`，优先走官方 REST API。
- 没有 Token、不能确定或需要 SSO/MFA：先试 `browser`。

不要承诺浏览器通道支持所有 SSO。它使用独立的本地浏览器配置，`.browser-profile` 会保存登录会话，必须留在本机。

## 3. 初始化

交互方式：

```powershell
python wiki_connector.py init
```

也可以明确参数：

```powershell
python wiki_connector.py init --wiki-url <用户在本机提供的地址> --channel token
python wiki_connector.py init --wiki-url <用户在本机提供的地址> --channel browser
```

默认要求 HTTPS。只有用户明确知道内网 Wiki 只能通过 HTTP 访问时，才可在说明风险后使用 `--allow-http`；不要替用户擅自放宽。

Token 只能由用户在本机终端放入当前进程使用的环境变量。不要把 Token 写进命令历史、脚本、配置文件或聊天记录。

浏览器窗口打开后，清楚告诉用户：

> Wiki 登录窗口已经打开，请按公司的正常流程完成登录。不要把密码或验证码发给我；登录完成后告诉我即可。

## 4. 做真实验证

先运行：

```powershell
python wiki_connector.py doctor
```

再让用户给出一个不敏感的普通关键词，完成一次真实搜索，并读取其中一篇用户确认可以展示的页面：

```powershell
python wiki_connector.py search --query "<关键词>" --limit 3
python wiki_connector.py read --page-id <页面ID>
```

不要把搜索结果或页面正文放进公开反馈。向用户报告：连接方式、`doctor` 是否通过、搜索是否有结果、读取是否成功。

## 5. 不兼容时先适配

先根据实际错误判断失败位置：Python/依赖、浏览器、本地连接、Wiki 基础路径、REST 路径、Confluence 版本、Token 类型、认证方式、SSO、反向代理、证书、公司安全策略、用户权限或搜索语法。

可以修改公开项目代码来适配，但必须满足：

1. 不读取、打印或持久化凭证；
2. 不关闭 TLS/证书校验，不绕过认证；
3. 不增加写入 Wiki 的能力；
4. 修改范围可解释，可用离线测试或当前环境复测；
5. 不把公司专属地址、账号、页面结构硬编码进工具。

修改后重新运行 `doctor`、一次真实 `search` 和一次 `read`。如果仍然失败，停止反复尝试，保留最小复现和明确的失败阶段。

## 6. 生成脱敏反馈

先生成本地报告：

```powershell
python wiki_connector.py report
```

检查并删除以下内容：公司名称、Wiki 地址、用户名/邮箱、页面标题与正文、搜索词、Token、Cookie、内网域名/IP、文件内容和本机绝对路径。

然后运行：

```powershell
python wiki_connector.py feedback
```

它只会打开预填的 GitHub Issue 页面，不会自动发布。请让用户先看内容，再决定是否提交。

反馈至少写清：

- 成功、修改后成功，还是仍然失败；
- 操作系统、Python 版本、连接通道和可公开的 Confluence 类型/大版本；
- 失败发生在安装、初始化、登录、`doctor`、搜索还是读取；
- 脱敏后的错误类型；
- 如果修改成功，说明改动文件、原因和验证命令，最好附通用化的补丁或 PR。

## 7. 交付给用户

最后用直白中文说明：现在是否可用、用户以后要运行哪条命令、本地保存了哪些配置或浏览器会话、哪些内容绝不能上传，以及 Issue 页面是否仍待用户检查提交。
