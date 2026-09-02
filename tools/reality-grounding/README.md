# 丢掉幻想：Reality Grounding + Reality Strategy

![AI 的建议正确得没有用：正式授权邮件与现实执行条件的对照](docs/reality-grounding-share-card.png)

很多 AI 建议每句话都正确，放进真实公司却一步也走不动。它会默认经理愿意授权、其他部门愿意配合、制度写了就会执行，也容易把自己猜出来的条件当成已经存在。

这是一对配合使用的 Skill。`reality-grounding` 先区分“真正要实现的结果”和“别人已经提出来的办法”，再用尽量少的问题还原参与方、相关地点、对象或资源、责任与授权、承诺和执行顺序。`reality-strategy` 接着查清公开说法背后的真实阻碍和实际决策链，改变默认动作、责任、代价、支持者或行动顺序。第一次行动以后继续收集反馈，不把“给过建议”当成“问题已经解决”。

## 直接交给 Agent

把下面这段话发给支持本地文件和 Agent Skills 的 Agent：

```text
请打开下面的项目，完整阅读 README.md 和 QUICKSTART.md：
https://github.com/Bono12138/bonobox/tree/main/tools/reality-grounding

请先检查你当前是否支持 Agent Skills，再把 reality-grounding 和 reality-strategy 安装到当前 Agent 实际使用的 Skill 目录。不要覆盖同名 Skill；如果已经存在，请先比较差异并告诉我。

先检测可用的 Python 3 命令：Windows 通常使用 `py -3`，macOS 和 Linux 通常使用 `python3`。安装后用该命令运行 verify.py，并传入实际安装后的 reality-grounding 目录。

验证通过后，请明确告诉我：两个 Skill 分别安装到了哪里；当前 Agent 是否都能发现；验证器是否 PASS。然后先用 $reality-grounding 区分原始诉求和当前办法；叙述混乱时，先给我两三种参与方与钱、货、合同流的情境让我确认，只问会改变路线的问题。再用 $reality-strategy 查明真实阻碍和决策链，提出一个能改变局势的第一步。实施后继续问我实际结果，根据反馈调整下一步。

不要让我在聊天中发送密码、Token、Cookie、公司内部资料或客户数据，也不要绕过现有安全设置。
```

如果 Agent 不支持 Skills，它仍然可以读取 `reality-grounding/SKILL.md` 作为当前任务的参考说明，但这不等于已经安装，也不能保证以后自动触发。

## 自己安装

需要 Python 3.9+。以下命令都在本目录运行。

macOS 和 Linux：

安装到通用 Agent Skills：

```bash
python3 install.py --target agents
```

安装到 Codex：

```bash
python3 install.py --target codex
```

安装到 Claude Code：

```bash
python3 install.py --target claude
```

安装到指定 Skill 根目录：

```bash
python3 install.py --path /path/to/skills
```

安装器默认安装两个 Skill，不会覆盖已有的同名目录。目标已经存在但内容不同时，它会停止，让你先检查差异。只想安装其中一个时，可以加 `--skill reality-grounding` 或 `--skill reality-strategy`。

安装完成后运行：

```bash
python3 verify.py --skill-path /实际路径/reality-grounding
```

看到以下输出，才能确认文件、引用和结构验证器已经安装完整：

```text
PASS reality-grounding files and record validator
PASS reality-strategy files and behaviour guards
PASS paired reality Skills verification complete
```

Windows 中把以上命令开头的 `python3` 换成 `py -3`。

## 它会怎样改变回答

普通建议可能直接说：

> 请经理发一封正式授权邮件，明确各部门职责，并建立固定周会。

安装后，Agent 应先判断用户说的“做 B”究竟是原始目标，还是解决 A 的一种猜想。多人、多地或交易叙述混乱时，它会先画出少数几种具体关系，请用户做最小纠正，而不是扔回一份长问卷。关系清楚后，它再查真正掌握决定的人、公开理由背后的持续原因，以及谁在承担沉默和拖延的成本。没有查清的连接仍是明确标注的假设，不会被补成事实。

## 能力边界

- 它不会读心，也不会自动知道所有不成文规则。
- 它不会扩大 Agent 的文件、系统或组织权限。
- `verify.py` 能证明两个 Skill 的文件完整、引用有效，并检查关键行为要求是否存在；它不能证明每种模型、每个宿主都会稳定触发或正确执行。
- 真正使用时仍要检查 Agent 是否发现并调用了两个 Skill，再用一个实际问题观察回答有没有先调查现实条件、找到受阻环节并持续跟进。
- 不要为了完成调查把公司资料、客户数据、账号或凭据上传到公开 Issue。

## 测试和反馈

本项目包含十类现实调查案例、九类现实策略案例和结构验证器。测试方法及当前结果见 [测试报告](docs/TEST-REPORT.md)。

如果安装成功、触发失败、回答仍然跳过现有证据，或某个 Agent 不支持这种 Skill 结构，请提交 [Reality Grounding 反馈](https://github.com/Bono12138/bonobox/issues/new?template=reality_grounding_feedback.yml)。提交前删除公司名称、人物姓名、内部网址、文件内容、真实任务信息、账号、凭据和本机绝对路径。

许可证：[MIT](LICENSE)。
