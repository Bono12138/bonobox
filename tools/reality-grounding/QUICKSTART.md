# 快速开始

## 让 Agent 安装

把这段话和项目地址一起发给 Agent：

```text
请阅读 README.md，检查当前 Agent 的 Skill 目录，把 reality-grounding 和 reality-strategy 安装进去。不要覆盖已有同名目录。安装后运行 verify.py，并确认当前 Agent 能发现两个 Skill。然后先用 $reality-grounding 问清会改变路线的现场信息，再用 $reality-strategy 找出卡住的一步，盘点手边的人、关系、场景、内容和环境条件，提出一个可逆的第一步。不要默认别人会配合。
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
请使用 $reality-grounding。优先检查我已经提供的证据。缺少会改变路线的信息时，先问一至三个我凭日常观察就能回答的问题，不要先给完整方案。找到真正卡住的一步，再选择一个现实中能执行的动作；实施后继续问我实际结果，根据反馈调整下一步。
```

好的结果应当区分事实、制度、实际做法、推断和未知，也应在缺少关键权限或配合时保留分支或停止。直接办法走不通时，它会寻找现场已有的替代通道，但不会把公开羞辱、造谣或纯猎奇当成聪明。它不需要为了显得认真而向你索取完整 SOP。
