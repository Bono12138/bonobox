# 数据平台兼容性清单

这份清单只记录代码已经支持、自动测试覆盖或真实用户反馈过的环境。没有列出不代表永远不能支持，只表示目前没有足够证据。

## 当前状态

| 平台或环境 | 状态 | 证据 |
|---|---|---|
| Windows 10/11、Python 3.10+、Superset 用户名密码表单登录、旧版同步 SQL Lab | 公开 Beta | 自动测试；维护者在一个真实企业部署中完成过 `SELECT 1` 和受控查询 |
| Superset 新版 `/api/v1/sqllab/execute/` | 等待连接器 | 当前代码未实现 |
| Superset SSO、OAuth、MFA、CAPTCHA 或自定义登录 | 等待安全的认证方案和真实测试环境 | 不允许绕过企业认证 |
| macOS、Linux | 等待安全凭据存储和安装测试 | 当前代码依赖 Windows DPAPI |
| Power BI | 等待需求与测试环境 | 当前没有连接器 |
| Metabase | 等待需求与测试环境 | 当前没有连接器 |
| DBX | 等待用户说明具体产品、接口与测试条件 | 当前没有连接器，也不预设它与 Databricks 相同 |
| Databricks | 等待需求与测试环境 | 当前没有连接器 |
| 其他企业数据平台 | 等待社区报告 | 先提交平台、认证和最小查询方式，不要提交内部资料 |

## 怎样贡献一个兼容性样本

成功、部分成功、失败和明确不支持都可以提交[数据平台兼容性报告](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml)。

这个项目也接受 Agent 协助完成的适配：先在本地单独分支中做最小修改并运行测试，再用 Issue 记录原版结果、改造结果和剩余限制。通用、脱敏且有测试的代码通过 Pull Request 提交，并关联对应 Issue。原版成功、改造成功、改造失败和暂时无法改造都是有效样本。

适配只能修改本地工具或新增独立连接器，不得修改企业平台、绕过认证或扩大权限。不同平台保持独立连接器，共享兼容性报告和贡献流程。

Superset Query `1.0.0-beta.2` 可以生成一份有固定字段的脱敏草稿：

```powershell
python scripts\superset_query.py compatibility-report `
  --result success `
  --platform superset-legacy `
  --platform-version 4.1 `
  --login-type password-form `
  --transport legacy-sync `
  --agent codex `
  --database-type trino `
  --doctor-result passed `
  --failure-stage none `
  --error-category none
```

提交前仍需由用户本人复核。报告中不得增加公司名称、内部地址、用户名、凭据、Cookie、Token、SQL、结果、对象名称、查询编号、本机路径、客户数据或内部截图。

## 怎样认定“支持”

- 自动测试通过，只证明公开包结构和代码路径正常；
- 单个用户成功，只证明该用户的具体环境成功；
- 只有多个可区分环境反复成功、失败边界明确、安装和排错说明完整，才会扩大正式支持范围；
- 不允许通过关闭 TLS、绕过 SSO/MFA 或扩大数据库权限来制造成功案例。
