# Tech Learning OS

本地 AI 技术阅读助手，通过英文原文学习计算机专业知识。

## 安装

```bash
pip install -e .
cp .env.example .env   # 编辑 .env 填入 DEEPSEEK_API_KEY
```

## 目录结构

```
notes/
  Reading/           ← tlos read 自动生成
    CSAPP/
      preface/
  Summary/            ← 用户写学习总结（技术写作检查）
    CSAPP/
  Diary/              ← 用户写英文日记（日常写作检查）
```

手动新增学习资料：直接在 `notes/Summary/` 下 `mkdir` 即可，`tlos check` 自动发现。

## 命令

### `tlos status` — 查看当前配置

### `tlos context` — 设置阅读上下文

```bash
tlos context --book CSAPP --chapter "Chapter 1"
```

### `tlos read` — 阅读一段英文

1. 在 PDF/网页中复制英文原文（Cmd+C）
2. 运行 `tlos read`
3. AI 翻译全文、提取术语 + 语块
4. 可输入自己的理解
5. 自动保存到 `notes/Reading/{书}/{章}/`

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
