# 快速开始

## 让 Agent 安装

把这段话和项目地址一起发给 Agent：

```text
请阅读 README.md，检查当前 Agent 的 Skill 目录，把 reality-grounding 安装进去。不要覆盖已有同名目录。安装后运行 verify.py，并确认当前 Agent 能发现这个 Skill。然后用 $reality-grounding 重新分析我刚才的问题：先查实际权限、参与的人、日常做法和会改变行动的未知信息，不要默认别人会配合。
```

项目地址：

```text
https://github.com/Bono12138/bonobox/tree/main/tools/reality-grounding
```

## 手动安装

```bash
python install.py --target agents
python verify.py --skill-path ~/.agents/skills/reality-grounding
```

Codex 用户把 `agents` 改成 `codex`；Claude Code 用户改成 `claude`。自定义目录使用 `python install.py --path /path/to/skills`。

## 第一次测试

把 AI 上一次给你的离谱建议重新发给它，再加一句：

```text
请使用 $reality-grounding。先指出这份建议偷偷假设了哪些权限、配合和实际做法；优先检查我已经提供的证据，只问答案会改变下一步的问题。
```

好的结果应当区分事实、制度、实际做法、推断和未知，也应在缺少关键权限或配合时保留分支或停止。它不需要为了显得认真而向你索取完整 SOP。
