# Superset 只读查询 Skill｜五分钟开始

## 先确认适用

只有同时满足以下条件才继续：

- Windows 10 或 11；
- Python 3.10 或更高版本；
- 你本人可以在浏览器中登录 Superset；
- 你本人可以打开 SQL Lab 并执行 `SELECT 1`；
- 登录页面直接接受用户名和密码；
- 你知道 SQL Lab 使用的数据库连接 ID 和默认 schema；
- 组织允许当前 Agent 和模型处理相关数据。

SSO、OAuth、MFA、自定义登录页和新版 API-only 部署不属于当前版本。不要关闭认证或 TLS 来强行兼容。

## 1. 安装

从 GitHub Release 同时下载 ZIP 和同名 `.sha256` 文件。在 PowerShell 中核对：

```powershell
(Get-FileHash .\bonobox-superset-query-v1.0.0-beta.2.zip -Algorithm SHA256).Hash.ToLower()
Get-Content .\bonobox-superset-query-v1.0.0-beta.2.zip.sha256
```

两处哈希必须一致。随后解压，在 PowerShell 进入解压目录。

Codex：

```powershell
.\install.ps1 -Target Codex
```

Cursor：

```powershell
.\install.ps1 -Target Cursor
```

自定义目录：

```powershell
.\install.ps1 -Destination C:\your\skills\query-superset
```

安装程序不会读取或迁移密码、Cookie、会话、配置和查询结果。目标目录已经存在时，它会停止；确认旧版本不再需要后，使用 `-Force` 明确覆盖同名文件。

## 2. 找到数据库连接 ID

这里需要的是 Superset SQL Lab 中的数据库连接编号，不是用户 ID，也不是数据库密码。

优先按以下顺序获取：

1. 请 Superset 管理员提供；
2. 查看 SQL Lab 当前数据库选择对应的页面 URL 或组织内部说明；
3. 如果无法确认，停止配置，不要猜测其他连接编号。

## 3. 配置和认证

进入安装后的 `query-superset` 目录：

```powershell
python scripts\superset_query.py configure
python scripts\superset_query.py auth
```

`configure` 询问：

- Superset HTTPS 地址；
- 你的用户名；
- 数据库连接 ID；
- 默认 schema；
- 可选的组织 CA 文件。

默认最多保存 10,000 行。需要更小的上限时，可以再次配置：

```powershell
python scripts\superset_query.py configure --max-result-rows 1000
```

`auth` 在终端中隐藏密码输入，并使用 Windows DPAPI 加密保存。不要把密码发给 Agent。

## 4. 验证

```powershell
python scripts\test_superset_query.py
python scripts\superset_query.py status
python scripts\superset_query.py doctor
```

通过标准：

- 自动测试全部通过；
- `status` 显示配置和凭据存在；
- `doctor` 返回 `ok: true`；
- 实际认证用户名与配置用户名一致；
- `SELECT 1` 成功。

## 5. 第一次查询

```powershell
python scripts\superset_query.py run --sql "SELECT 1 AS connection_test"
```

再尝试一个范围很小的元数据查询或汇总查询。不要把客户明细作为第一次测试。

## 直接交给 Agent 的提示词

```text
请打开 https://github.com/Bono12138/bonobox/tree/main/tools/superset-query，并完整阅读 README.md、QUICKSTART.md、COMPATIBILITY.md、query-superset/SKILL.md 和 references/capabilities.md。
先只做环境体检，检查操作系统、Python、Agent、数据平台、平台版本、登录方式、查询接口、SQL Lab 权限和组织的数据使用要求。
符合当前公开 Beta 范围后，核对 Release ZIP 的 SHA-256，再安装并运行单元测试、status 和 doctor。doctor 必须真实执行 SELECT 1，实际身份必须与配置一致。
需要密码时，只让我本人在交互式终端中隐藏输入；不要让我把密码、Cookie、Token 或会话发到聊天里。
不要关闭 TLS，不要绕过 SSO、MFA、VPN或公司权限，不要猜数据库连接 ID，也不要扩大数据库权限。
无论成功、部分成功、失败还是当前不支持，都准备一份脱敏兼容性报告。能运行脚本时使用 compatibility-report；不能运行时按 GitHub 的 Data platform compatibility report 模板整理。
公开报告不得包含公司名称、内部网址、用户名、凭据、Cookie、Token、SQL、结果、数据库或表名、查询编号、本机隐私路径、客户数据与内部截图。提交 Issue 前先把完整内容给我确认。
完成后告诉我：环境判断、安装路径、测试结果、doctor 是否成功、身份是否匹配、当前限制，以及建议提交的 Issue 类型。
```

## 失败以后

先看错误类别，再决定下一步。不要连续盲重试。

- `auth`：检查登录方式和账号；
- `permission`：停止并申请权限；
- `sql`：修正 SQL；
- `object`：查询 `information_schema`；
- `resource`：缩小扫描和结果；
- `network`：检查 VPN、DNS、代理、访问客户端和 CA；
- `server`：保留脱敏错误和版本信息。

仍无法解决时，使用 GitHub Issue 模板。公开反馈前删除地址、账号、SQL、查询结果、客户数据、原始 manifest、查询编号和内部截图。安全漏洞不要发公开 Issue，应使用仓库的私密安全上报入口。

如果已经完成环境判断，可以生成统一报告：

```powershell
python scripts\superset_query.py compatibility-report --result failed --platform superset-legacy --platform-version unknown --login-type password-form --transport legacy-sync --agent other --database-type unknown --doctor-result failed --failure-stage doctor --error-category network
```

将输出交给用户本人检查，再提交到[数据平台兼容性报告](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml)。
