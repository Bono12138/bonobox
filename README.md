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

## 工具目录

| 工具 | 解决的问题 | 实测表现 | 状态 |
|---|---|---|---|
| [Portable Search MCP](tools/portable-search-mcp/) | 给支持 MCP 的本地模型、Agent、IDE 和自动化流程增加公开网页、新闻和图片搜索 | 33 次实时请求成功 31 次；网页/图片 27/27 次有结果；P50 2.244 秒 | v2.0.1 · 已发布 |

## 第一件工具：Portable Search MCP

它把公开网络搜索包装成 3 个标准 MCP 工具：

- `search_web`：网页标题、摘要和来源链接；
- `search_news`：新闻标题、来源、发布时间和严格时间过滤；
- `search_images`：图片地址、来源页和尺寸信息。

不需要商业搜索 API Key，支持 Windows 一键安装、自检和 Agent 辅助安装。

### 它到底搜得怎么样

2026-08-05 在 Windows、Python 3.13.3、`ddgs 9.14.4` 环境运行 11 组查询、每组 3 轮，共 33 次公开网络请求：

| 指标 | 实测结果 | 怎么理解 |
|---|---:|---|
| 请求成功率 | **31/33（93.9%）** | 2 次中文新闻请求在重试后仍遇到上游临时不可用 |
| 网页/图片有结果率 | **27/27（100%）** | 9 组网页与图片查询每轮都返回结果 |
| 返回链接有效率 | **100%** | 本次返回的链接均为 HTTP(S) 公网 URL |
| 普通语句找指定官网 | **4/9（44.4%）** | 免费后端的自然排序不稳定，不能当精确导航器 |
| 使用 `site:` 限定官网 | **9/9（100%）** | 指定来源后，目标域名每次进入前 5 |
| 当天新闻有结果率 | **3/6（50%）** | 工具宁可返回空结果，也不拿旧闻冒充当天新闻 |
| 响应时间 | **P50 2.244 秒；P95 4.618 秒** | 当前网络条件下，多数查询约 2 秒，慢请求约 5–10 秒 |

这组结果说明：它适合给 Agent 快速扩展公开信息候选来源，也适合用 `site:`、时间范围和明确关键词做定向检索；它不适合承诺固定排序、持续 100% 可用或分钟级新闻覆盖。

完整方法、逐轮匿名化指标和复跑脚本见[测试报告](tools/portable-search-mcp/docs/TEST-REPORT.md)与[原始基准数据](tools/portable-search-mcp/docs/benchmark-2026-08-05.json)。

### 下载和安装

从 [Portable Search MCP v2.0.1 Release](https://github.com/Bono12138/bonobox/releases/tag/portable-search-mcp-v2.0.1) 下载 `portable-search-mcp-v2.0.1.zip`，解压后在 PowerShell 运行：

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
请解压 portable-search-mcp-v2.0.1.zip，先完整阅读 QUICKSTART.md，再按文档完成 Windows 安装和 MCP 配置。
安装后运行 .\verify.ps1 -Live。
最后只告诉我：安装目录；configuration、protocol、live_search 是否 PASS；工具列表中是否出现 search_web、search_news、search_images。
不要输出或上传账号、令牌、Cookie、本机隐私路径、mcp-config.local.json 或敏感搜索词。
```

完整使用说明、适用场景、提示词、测试证据和局限见[工具文档](tools/portable-search-mcp/README.md)。

## BB 箱子的发布标准

每件工具正式进入 BonoBox 前，至少满足：

1. 解决一个能说清楚的实际问题；
2. 五分钟内能找到下载、安装和第一次使用方法；
3. 有手动操作路径，适合时也提供 Agent 辅助路径；
4. 有自动化测试，必要时增加真实环境与表现测试；
5. 写明成功标准、已知限制和不能使用的场景；
6. 发布包采用白名单构建，不包含凭据、本机配置、缓存和敏感数据；
7. 每次发布有独立版本、变更说明和可下载产物。

品牌与视觉使用规则见 [BonoBox Brand Guide](docs/BRAND-GUIDE.md)。

## 更新与反馈

- 使用问题和可复现故障：[Bug report](https://github.com/Bono12138/bonobox/issues/new?template=bug_report.yml)
- 新工具和改进建议：[Tool idea](https://github.com/Bono12138/bonobox/issues/new?template=tool_idea.yml)
- 一般讨论和使用分享：[Discussions](https://github.com/Bono12138/bonobox/discussions)
- 安全问题：不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 私下报告

反馈前请删除账号、令牌、Cookie、本机隐私路径、客户数据和敏感搜索词。

## License

仓库自有代码采用 [MIT License](LICENSE)。每件工具使用的第三方项目仍保留各自许可证和版权，详见工具目录中的第三方说明。
