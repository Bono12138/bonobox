# 快速开始

## 让 Agent 安装

把这段话和项目地址一起发给 Agent：

```text
请阅读 README.md，检查当前 Agent 的 Skill 目录，把 reality-grounding 和 reality-strategy 安装进去。不要覆盖已有同名目录。先检测可用的 Python 3 命令：Windows 通常是 py -3，macOS 和 Linux 通常是 python3。安装后运行 verify.py，并确认当前 Agent 能发现两个 Skill。然后先用 $reality-grounding 区分原始诉求和当前办法；叙述混乱时，给我两三种参与方以及钱、货、合同和时间顺序的情境让我确认，只问会改变路线的问题。再用 $reality-strategy 查明真实阻碍和决策链，提出一个能改变局势的第一步。目标与价值判断由我决定。
```

项目地址：

```text
https://github.com/Bono12138/bonobox/tree/main/tools/reality-grounding
```

## 手动安装

macOS 和 Linux：

```bash
python3 install.py --target agents
python3 verify.py --skill-path ~/.agents/skills/reality-grounding
```

Windows：

```powershell
py -3 install.py --target agents
py -3 verify.py --skill-path "$HOME/.agents/skills/reality-grounding"
```

Codex 用户把 `agents` 改成 `codex`；Claude Code 用户改成 `claude`。自定义目录使用同一个 Python 3 命令运行 `install.py --path /path/to/skills`。

## 第一次测试

把 AI 上一次给你的离谱建议重新发给它，再加一句：

```text
请使用 $reality-grounding。先区分我真正要实现的结果和我当前想到的办法。优先检查我已经提供的证据；叙述混乱时，先整理两三种具体情境让我纠正，不要把调查问卷扔给我。缺少会改变路线的信息时，只问一至三个我容易回答的问题。关系清楚以后再用 $reality-strategy 查真实原因和实际决策链，设计能改变局势的动作；实施后继续问我实际结果。
```

好的结果应当区分事实、制度、实际做法、推断和未知，也应在缺少关键权限或配合时保留分支或停止。直接办法走不通时，它会寻找现场已有的替代通道，但不会把公开羞辱、造谣或纯猎奇当成聪明。它不需要为了显得认真而向你索取完整 SOP。
