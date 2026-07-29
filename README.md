# Tech Learning OS

本地 AI 技术阅读助手，通过英文原文学习计算机专业知识，同时也支持轻小说阅读。

## 安装

```bash
pip install -e .
cp .env.example .env   # 编辑 .env 填入 DEEPSEEK_API_KEY
```

## 目录结构

```
notes/
  Reading/           ← 技术模式 (tlos read --mode tech)
    CSAPP/
      preface/
  LN/                 ← 轻小说模式 (tlos read --mode ln)
    86-eighty-six/
      vol-1/
  Summary/            ← 用户写学习总结（技术写作检查）
    CSAPP/
  Diary/              ← 用户写英文日记（日常写作检查）
```

## 命令

### `tlos status` — 查看当前配置

### `tlos context` — 设置阅读上下文

```bash
tlos context                    # 交互式选择（推荐）
tlos context --mode ln          # 切换到轻小说模式并交互选择
tlos context --book CSAPP --chapter "Chapter 1"   # 快捷方式
```

### `tlos read` — 持续阅读会话

进入后保持运行，每次复制新段落回来按 Enter 即可继续分析，不用反复敲命令。同一天同一书同一章的阅读追加到同一个 `{日期}.md` 文件中。

```bash
tlos read               # 使用已保存的上下文
tlos read --mode ln     # 轻小说模式

# 会话中：
#   按 Enter → 分析剪贴板内容
#   输入 :q → 退出
#   Ctrl+C → 退出
```

退出时显示本次会话统计（读了几段，保存在哪）。

### `tlos check` — 检查英文写作

```bash
tlos check                                  # 自动找最新 md
tlos check --type summary                   # 技术总结模式
tlos check --type summary --course CSAPP    # 指定课程
tlos check --type diary                     # 日记模式
tlos check path/to/file.md                  # 指定文件
```

规则：
- 英文写错的 → 标注原因，不给正确写法（自己改）
- 写中文的 → 给英文表达建议（不会写的部分）

## 技术栈

Python 3.9 + DeepSeek API + OpenAI SDK + Markdown
