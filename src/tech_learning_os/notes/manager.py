"""笔记管理器 — 生成和保存 Markdown 格式学习笔记"""

import os
import re
from datetime import datetime
from ..config import settings


def save_note(term_data: dict, original_text: str, my_understanding: str = "") -> str:
    """保存一条学习笔记为 Markdown 文件。

    Args:
        term_data: AI 返回的术语数据，格式为 {"term": "...", "definition_zh": "...", "chunks": [...], "related": [...]}
        original_text: 用户输入的英文原文
        my_understanding: 用户自己的理解（可选）

    Returns:
        str: 保存的文件路径
    """
    term_name = term_data.get("term", "note")
    slug = _slugify(term_name)

    # 确保目录存在
    os.makedirs(settings.notes_path, exist_ok=True)

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
    filepath = os.path.join(settings.notes_path, filename)

    chunks_md = _format_chunks(term_data.get("chunks", []))
    related_md = _format_related(term_data.get("related", []))

    md = f"""# {term_data.get('term', '笔记')}

> {original_text}

**书籍**：{settings.current_book}  ·  **章节**：{settings.current_chapter}  ·  **日期**：{datetime.now().strftime('%Y-%m-%d')}

---

## 翻译

{term_data.get('translation', '')}

## 技术解释

{term_data.get('definition_zh', '')}

## 语块积累

{chunks_md}

## 关联概念

{related_md}

## 我的理解

{my_understanding if my_understanding else '（待填写）'}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    return filepath


def _slugify(text: str) -> str:
    """把术语名转为文件名安全的格式。

    >>> _slugify("cache miss")
    'cache-miss'
    >>> _slugify("DRAM (Dynamic RAM)")
    'dram-dynamic-ram'
    """
    text = text.lower().strip()
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    return text


def _format_chunks(chunks: list) -> str:
    """格式化语块列表为 Markdown 表格。"""
    if not chunks:
        return "（无）"
    lines = ["| 英文 | 中文 | 说明 |", "|------|------|------|"]
    for c in chunks:
        en = c.get("en", "")
        zh = c.get("zh", "")
        note = c.get("note", "")
        lines.append(f"| {en} | {zh} | {note} |")
    return "\n".join(lines)


def _format_related(related: list) -> str:
    """格式化关联概念列表。"""
    if not related:
        return "（无）"
    return "\n".join(f"- {r}" for r in related)
