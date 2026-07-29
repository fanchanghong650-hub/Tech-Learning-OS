"""笔记管理器 — 生成和追加 Markdown 格式学习笔记"""

import os
from datetime import datetime
from ..config import settings


def append_note(original_text: str, result: dict, my_understanding: str = "", count: int = 0) -> str:
    """追加一条学习笔记到当天的 Markdown 文件。

    同一天同一书同一章的阅读都会追加到同一个 {date}.md 文件中。

    Args:
        original_text: 用户输入的英文原文
        result: AI 返回的分析结果 {"translation": str, "chunks": [...]}
        my_understanding: 用户自己的理解（可选）
        count: 本次会话中已读的序号（0 表示第一篇）

    Returns:
        str: 追加到的文件路径
    """
    os.makedirs(settings.notes_path, exist_ok=True)

    filename = f"{datetime.now().strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(settings.notes_path, filename)
    is_new = not os.path.exists(filepath)

    chunks_md = _format_chunks(result.get("chunks", []))

    if settings.mode == "ln":
        label_book = "系列"
        label_ch = "卷"
    else:
        label_book = "书籍"
        label_ch = "章节"

    if is_new:
        header = f"""# {datetime.now().strftime('%Y-%m-%d')}

## {settings.current_book or '未设置'} · {settings.current_chapter or '未设置'}

"""
    else:
        header = ""

    entry = f"""> {original_text}

**翻译**：{result.get('translation', '')}

**语块积累**：

{chunks_md}

**我的理解**：{my_understanding if my_understanding else '（待填写）'}

"""

    with open(filepath, "a", encoding="utf-8") as f:
        if header:
            f.write(header)
        if not is_new:
            f.write("---\n\n")
        f.write(entry)

    return filepath


def _format_chunks(chunks: list) -> str:
    if not chunks:
        return "（无）"
    lines = ["| 英文 | 中文 | 说明 |", "|------|------|------|"]
    for c in chunks:
        en = c.get("en", "")
        zh = c.get("zh", "")
        note = c.get("note", "")
        lines.append(f"| {en} | {zh} | {note} |")
    return "\n".join(lines)
