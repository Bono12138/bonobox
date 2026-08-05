# 3 分钟开始使用

## 使用前确认

- Windows 10/11。
- Python 3.10 或更高版本。
- 你的 Agent 支持 MCP 工具调用。
- 当前电脑允许访问公开互联网。
- 搜索词不含客户数据、凭据或未公开业务信息。

如果你使用的聊天工具已经自带搜索，并且只在该工具内聊天，不需要安装本工具。

## 第一步：解压

把 ZIP 解压到一个长期保留、路径较短的目录，例如：

```text
C:\Tools\portable-search-mcp
```

配置完成后不要随意移动这个目录，否则 Agent 找不到服务脚本。

## 第二步：安装

在解压目录打开 PowerShell：

```powershell
.\install.ps1
```

如果公司设备阻止脚本运行，请先按公司软件管理要求处理，不要关闭安全软件或修改全局安全策略。

看到下面两类 `PASS` 表示本机安装和协议检查完成：

```text
PASS configuration=...
PASS protocol server=portable-search-mcp tools=3
```

## 第三步：接入 Agent

打开安装目录里的 `mcp-config.local.json`，把 `portable-search` 这一项复制到你的 Agent MCP 配置中，然后重启 Agent。

不同 Agent 的配置入口名称可能是 “MCP Servers”“Tools”“External Tools” 或 “Model Context Protocol”。如果产品只支持模型 API、不支持 MCP，需要由平台管理员把本服务接到它的工具调用层。

## 第四步：联网验证

```powershell
.\verify.ps1 -Live
```

出现以下结果表示实际网络搜索成功：

```text
PASS live_search valid_results=...
```

## 第五步：让 Agent 调用

可以先问：

```text
请使用 search_web 查找 Python 官方文档，列出来源链接。
```

测试最新新闻时要明确时间范围：

```text
请使用 search_news 搜索近一天的人工智能新闻，显示每条的发布时间和原文链接；没有可核对发布时间的结果不要称为今日新闻。
```

## 如何确认答案真的用了搜索

- Agent 的工具调用记录中出现 `search_web` 或 `search_news`。
- 回答包含可以打开的 `http://` 或 `https://` 来源链接。
- 新闻回答显示 `published_at`，并与问题要求的时间范围一致。
- 重要信息打开原文核对，不只依赖摘要。

如果失败，请查看 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。
