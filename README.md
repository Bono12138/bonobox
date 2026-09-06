<p align="center">
  <img src="docs/bonobox-logo.png" alt="BonoBox rabbit mascot in a toolbox" width="260" />
</p>

<h1 align="center">BonoBox · BB 箱子</h1>

<p align="center"><strong>一个箱子，一件真工具，一组真实测试。</strong></p>

<p align="center">
  <a href="README.en.md">English</a> ·
  <a href="#工具目录">工具目录</a> ·
  <a href="ROADMAP.md">路线图</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a>
</p>

<p align="center">
  <a href="https://github.com/Bono12138/bonobox/actions/workflows/tool-tests.yml"><img src="https://github.com/Bono12138/bonobox/actions/workflows/tool-tests.yml/badge.svg" alt="Tool tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-F5C518.svg" alt="MIT license" /></a>
  <a href="https://github.com/Bono12138/bonobox"><img src="https://img.shields.io/github/stars/Bono12138/bonobox?style=flat&color=0B3A67" alt="GitHub stars" /></a>
</p>

**BonoBox（简称 BBX，外号 BB 箱子）**是 Bono 持续发布实用小工具的公开仓库。这里不放只有想法的空目录：每件工具都要有最短使用路径、真实测试、可观察的成功标准，以及明确的不能使用场景。

如果某件工具帮你省了时间，欢迎点一个 Star。后续公开工具和重要更新都会继续装进同一个 BB 箱子。

## 节目资料

[Astra：AI 基础设施研究](episodes/astra-investment-research-20260905/)——PPT、Excel、原始提示词和公开来源索引。研究日期：2026 年 9 月 5 日。

## 工具目录

| 工具 | 解决的问题 | 实测表现 | 状态 |
|---|---|---|---|
| [Portable Search MCP](tools/portable-search-mcp/) | 给支持 MCP 的本地模型、Agent、IDE 和自动化流程增加公开网页、新闻和图片搜索 | 90/90 请求成功；网页/图片 66/66、新闻 24/24 轮有结果；P50 2.537 秒 | v2.1.0 · 已发布 |
| [Superset 只读查询 Skill](tools/superset-query/) | 让 Agent 通过用户已有的 Superset SQL Lab 通道执行有边界的 SELECT 查询，并汇集跨公司的脱敏兼容性反馈 | 自动测试覆盖写入拦截、结果上限、CSV 安全、会话身份、错误分类和公开兼容性报告；旧版同步 SQL Lab 路线有维护者私下验证 | v1.0.0-beta.2 · 公开 Beta |
| [Wiki Connector](tools/wiki-connector/) | 让 Agent 通过用户自己的 Wiki 权限搜索和读取资料，并自动生成脱敏诊断反馈 | 离线测试覆盖 URL、安全边界、诊断报告和错误脱敏；真实环境仍需由使用者运行 `doctor` 验证 | v0.1.0-beta.1 · 公开 Beta |
| [丢掉幻想：Reality Grounding + Reality Strategy](tools/reality-grounding/) | 让 Agent 找回原始问题、还原真实关系，再查明阻碍并设计能改变局势的行动 | 成对安装、自检和结构验证通过本地测试；包含十类调查案例和九类策略案例，具体模型和宿主仍需确认实际触发 | v0.5.0 · 公开候选 |

## 第一件工具：Portable Search MCP

它把公开网络搜索包装成 3 个标准 MCP 工具：

- `search_web`：网页标题、摘要和来源链接；
- `search_news`：新闻标题、来源、发布时间和严格时间过滤；
- `search_images`：图片地址、来源页和尺寸信息。

不需要商业搜索 API Key，支持 Windows 一键安装、自检和 Agent 辅助安装。

### 实际搜索表现

2026-08-05 在 Windows、Python 3.13.3、`ddgs 9.14.4` 环境运行 30 组查询、每组 3 轮，共 90 次公开网络请求：

| 指标 | 实测结果 | 怎么理解 |
|---|---:|---|
| 请求成功率 | **90/90（100%）** | 三轮均未出现最终请求失败 |
| 网页/图片有结果率 | **66/66（100%）** | 18 组网页、4 组图片查询均返回结果 |
| 返回链接有效率 | **100%** | 本次返回的链接均为 HTTP(S) 公网 URL |
| 普通语句找指定官网 | **16/18（88.9%）** | 目标域名进入前 5；两次漏检均为人民银行官网 |
| 使用 `site:` 限定官网 | **18/18（100%）** | 目标域名每次排在第 1 位 |
| 新闻有结果率 | **24/24（100%）** | 每条新闻都有可解析日期并通过时间窗口检查 |
| 响应时间 | **P50 2.537 秒；P95 9.055 秒** | 多数查询约 2–3 秒，少量免费网页后端请求仍较慢 |

当前版本适合为 Agent 扩展公开信息候选来源，也适合使用 `site:`、时间范围和明确关键词做定向检索。普通语句官网导航仍可能漏掉目标域名；需要确定来源时必须写明域名。免费后端不提供固定排序、持续可用或分钟级新闻保证。

完整方法、逐轮匿名化指标、优化前后对比和复跑脚本见[测试报告](tools/portable-search-mcp/docs/TEST-REPORT.md)与[最终基准数据](tools/portable-search-mcp/docs/benchmark-2026-08-05-v3.json)。

### 下载和安装

从 [Portable Search MCP v2.1.0 Release](https://github.com/Bono12138/bonobox/releases/tag/portable-search-mcp-v2.1.0) 下载 `portable-search-mcp-v2.1.0.zip`，解压后在 PowerShell 运行：

部分浏览器会对刚发布、下载量较少的 ZIP 显示安全提醒。请从上述 Release 页面的 **Assets** 下载，并核对 SHA-256：

```text
8aa427aa0455b91069a802a2ee2d7151b5f0bafc8848435abf91131da2c3eb11
```

文件名和哈希均一致时，可以在下载记录中选择“保留”。不要关闭安全浏览或公司防护策略；信息不一致时请取消下载并提交 Issue。

```powershell
.\install.ps1
.\verify.ps1 -Live
```

出现下面三类输出才算安装完成：

```text
PASS configuration=...
PASS protocol server=portable-search-mcp tools=3
PASS live_search valid_results=...
```

随后把生成的 `mcp-config.local.json` 配置复制到自己的 Agent，并重启 Agent。这个文件包含本机安装路径，不要上传或转发。

### 让 Agent 帮你安装

把 ZIP 发给自己的 Agent，并复制：

```text
请解压 portable-search-mcp-v2.1.0.zip，先完整阅读 QUICKSTART.md，再按文档完成 Windows 安装和 MCP 配置。
安装后运行 .\verify.ps1 -Live。
最后只告诉我：安装目录；configuration、protocol、live_search 是否 PASS；工具列表中是否出现 search_web、search_news、search_images。
不要输出或上传账号、令牌、Cookie、本机隐私路径、mcp-config.local.json 或敏感搜索词。
```

完整使用说明、适用场景、提示词、测试证据和局限见[工具文档](tools/portable-search-mcp/README.md)。

## 第二件工具：Superset 只读查询 Skill

它不让 Agent 直接连接数据库，而是继续使用用户本人已有的 Superset SQL Lab 查询通道。公开 Beta 提供常见写入和管理形式拦截、Windows DPAPI 凭据保护、会话身份绑定、错误分类、默认 10,000 行结果上限和查询证据。本地检查不是完整 SQL 解析器，最终只读由 Superset 和底层数据库权限保证。

当前版本只支持 Windows、用户名密码表单登录和旧版同步 SQL Lab 接口。SSO、MFA、新版 API、Power BI、Metabase、DBX 和 Databricks 尚未支持。用户可以把[工具文档](tools/superset-query/)里的完整提示词直接交给自己的 Agent，由 Agent 做环境判断、安装、真实 `SELECT 1` 验证并准备脱敏反馈。成功、失败、当前不支持和其他平台需求都可以提交[数据平台兼容性报告](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml)。

## 第三件工具：Wiki Connector

它让 Agent 使用用户本人已有的 Wiki 权限搜索和读取资料。初版优先支持 Windows，并提供 API Token 和本地浏览器两条连接方式；实际是否可用取决于 Wiki 版本、登录方式、权限和企业安全策略。

把[工具文档](tools/wiki-connector/)中的提示词交给 Agent，Agent 会安装、运行 `doctor`、尝试在安全边界内适配，并生成不含公司资料的诊断报告。无论直接成功、修改后成功还是暂时无法使用，都可以提交 [Wiki Connector 兼容性反馈](https://github.com/Bono12138/bonobox/issues/new?template=wiki_connector_compatibility.yml)。

## 第四件工具：丢掉幻想

`reality-grounding` 先区分真正要实现的结果和已经被提出来的办法。遇到多人、多地或交易叙述混乱时，它会还原参与方、所在地、钱、货、合同和时间顺序，只问真正会改变路线的问题。

`reality-strategy` 接着查清公开说法背后的真实阻碍和实际决策链，再改变默认动作、责任、代价、支持者或行动顺序。它负责把可行性、成本、暴露面和后果说清，目标与价值判断仍由用户决定。两个 Skill 的安装提示词、自检方法、案例和能力边界见[工具文档](tools/reality-grounding/)。

## 更新与反馈

- 使用问题和可复现故障：[Bug report](https://github.com/Bono12138/bonobox/issues/new?template=bug_report.yml)
- 新工具和改进建议：[Tool idea](https://github.com/Bono12138/bonobox/issues/new?template=tool_idea.yml)
- 数据平台成功、失败、兼容性和连接器需求：[Compatibility report](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml)
- Wiki 安装成功、失败、适配结果和需求：[Wiki Connector report](https://github.com/Bono12138/bonobox/issues/new?template=wiki_connector_compatibility.yml)
- Reality Grounding / Reality Strategy 安装、触发和回答行为：[Reality Skills report](https://github.com/Bono12138/bonobox/issues/new?template=reality_grounding_feedback.yml)
- 一般讨论和使用分享：[Discussions](https://github.com/Bono12138/bonobox/discussions)
- 安全问题：不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 私下报告

反馈前请删除账号、令牌、Cookie、本机隐私路径、客户数据和敏感搜索词。

## License

仓库自有代码采用 [MIT License](LICENSE)。每件工具使用的第三方项目仍保留各自许可证和版权，详见工具目录中的第三方说明。
