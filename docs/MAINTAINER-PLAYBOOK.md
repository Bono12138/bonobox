# Maintainer playbook

## 增长目标

让 `bono-tools` 成为一个长期更新的公开工具入口。Star 是用户愿意持续关注的结果，不是用空目录、夸大承诺或高频无效发布换来的数字。

## 内容和发布节奏

1. 每个工具先解决一个具体问题，再用一句话说明结果。
2. README 第一屏固定出现：问题、下载、三步开始、成功标准、限制。
3. 每次有用户可感知变化才发 Release；修正文案可合并进下一次功能发布。
4. Release 标题使用 `<tool>-v<version>`，方便一个仓库维护多个工具。
5. 每次发布同步一张演示图或 30–60 秒短演示，并链接到同一个 GitHub Release。

## 分发路径

- GitHub：README、Release、Topics、Discussions 和可复现 Issue；
- 公司内部：短版工具分享页负责下载和上手，长版技术页负责证据和边界；
- 对外内容：围绕真实问题写一条短说明，展示“原来的麻烦—三步使用—可验证结果—限制”，统一链接到 Release；
- 后续工具继续进入同一仓库，不为单个小工具分散新建仓库。

## 建议观察的信号

- Release 下载数；
- Star 增长与新 Release 的对应关系；
- 安装成功和失败 Issue；
- Discussions 中出现的真实使用场景；
- 第二次使用、复用到其他 Agent 的反馈。

不单独维护复杂统计系统。GitHub 自带 Insights、Release 下载数和 Issues 足以支撑早期判断。
