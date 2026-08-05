<p align="center">
  <img src="docs/bono-tools-banner.svg" alt="Bono Tools" width="900" />
</p>

# bono-tools

[English](README.en.md) · [工具目录](#工具目录) · [路线图](ROADMAP.md) · [参与贡献](CONTRIBUTING.md)

[![Tool tests](https://github.com/Bono12138/bono-tools/actions/workflows/tool-tests.yml/badge.svg)](https://github.com/Bono12138/bono-tools/actions/workflows/tool-tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2B9A8F.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Bono12138/bono-tools?style=flat&color=0B3A67)](https://github.com/Bono12138/bono-tools/stargazers)

> 一组真正能用、可以检查、清楚说明边界的小工具。每个工具都提供最短使用路径、实际测试和失败时的处理办法。

如果这里的某个工具帮你省了时间，可以点一个 Star。后续新工具和重要更新都会在同一个仓库发布。

## 工具目录

| 工具 | 解决的问题 | 最短开始方式 | 状态 |
|---|---|---|---|
| [Portable Search MCP](tools/portable-search-mcp/) | 给支持 MCP 的本地模型、Agent、IDE 和自动化流程增加公开网页、新闻和图片搜索 | 下载 ZIP，运行 `install.ps1`，再执行 `verify.ps1 -Live` | v2.0.0 · 已测试 |

仓库只收录已经可以交付的工具。没有完成安装、验证、安全检查和边界说明的试验项目，不提前占一个空目录。

## 第一个工具：Portable Search MCP

它把公开网络搜索包装成标准 MCP 工具，供不同模型和 Agent 复用。当前提供：

- `search_web`：公开网页标题、摘要和来源链接；
- `search_news`：新闻标题、来源、发布时间和严格时间过滤；
- `search_images`：图片地址、来源页和尺寸信息；
- 无需商业搜索 API Key；
- Windows 一键安装与自检；
- 37 项自动化测试，另有全新 ZIP 安装和实时搜索测试。

### 下载和安装

从 [Portable Search MCP v2.0.0 Release](https://github.com/Bono12138/bono-tools/releases/tag/portable-search-mcp-v2.0.0) 下载 `portable-search-mcp-v2.0.0.zip`，解压后在 PowerShell 运行：

```powershell
.\install.ps1
.\verify.ps1 -Live
```

看到以下三类输出，才算安装完成：

```text
PASS configuration=...
PASS protocol server=portable-search-mcp tools=3
PASS live_search valid_results=...
```

随后把生成的 `mcp-config.local.json` 中的配置复制到自己的 Agent，并重启 Agent。这个本机配置文件包含安装路径，不要上传或转发。

### 让 Agent 帮你安装

把 ZIP 发给自己的 Agent，并复制：

```text
请解压 portable-search-mcp-v2.0.0.zip，先完整阅读 QUICKSTART.md，再按文档完成 Windows 安装和 MCP 配置。
安装后运行 .\verify.ps1 -Live。
最后只告诉我：安装目录；configuration、protocol、live_search 是否 PASS；工具列表中是否出现 search_web、search_news、search_images。
不要输出或上传账号、令牌、Cookie、本机隐私路径、mcp-config.local.json 或敏感搜索词。
```

完整使用说明、适用场景、测试证据和局限见 [工具文档](tools/portable-search-mcp/README.md)。

## 这个仓库的发布标准

每个工具正式进入 `bono-tools` 前，至少满足：

1. 解决一个能说清楚的实际问题；
2. 五分钟内能找到下载、安装和第一次使用方法；
3. 同时支持手动操作和适合时的 Agent 辅助操作；
4. 有自动化测试，必要时增加真实环境测试；
5. 写明成功标准、已知限制和不能使用的场景；
6. 发布包采用白名单构建，不包含凭据、本机配置、缓存和敏感数据；
7. 每次发布有独立版本、变更说明和可下载产物。

## 更新与反馈

- 使用问题和可复现故障：提交 [Bug report](https://github.com/Bono12138/bono-tools/issues/new?template=bug_report.yml)；
- 新工具和改进建议：提交 [Tool idea](https://github.com/Bono12138/bono-tools/issues/new?template=tool_idea.yml)；
- 一般讨论和使用分享：使用 [Discussions](https://github.com/Bono12138/bono-tools/discussions)；
- 安全问题：不要创建公开 Issue，请按 [SECURITY.md](SECURITY.md) 私下报告。

反馈前请删除账号、令牌、Cookie、本机隐私路径、客户数据和敏感搜索词。

## 项目结构

```text
bono-tools/
├── tools/                     # 每个已发布工具一个独立目录
│   └── portable-search-mcp/   # 第一个工具：源码、测试和完整文档
├── docs/                      # 仓库品牌素材和维护说明
├── .github/                   # CI、Issue 模板和社区入口
├── ROADMAP.md                 # 公开路线图
└── README.md                  # 统一入口和快速开始
```

## License

仓库自有代码采用 [MIT License](LICENSE)。每个工具使用的第三方项目仍保留各自的许可证和版权，详见工具目录中的第三方说明。
