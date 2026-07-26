"""CLI 入口 — 命令行交互主循环"""

import argparse
import glob
import os
import subprocess
from typing import Optional
from .config import settings
from .ai.client import AIClient
from .notes.manager import save_note


def main():
    parser = argparse.ArgumentParser(
        prog="tlos",
        description="Tech Learning OS — 本地 AI 技术阅读助手",
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")
    sub.add_parser("status", help="查看当前配置状态")
    ctx = sub.add_parser("context", help="设置或查看当前阅读上下文")
    ctx.add_argument("--book", help="书名，如 'CSAPP'")
    ctx.add_argument("--chapter", help="章节，如 'Preface'")
    sub.add_parser("read", help="开始交互式阅读")
    chk = sub.add_parser("check", help="检查英文写作表达")
    chk.add_argument("path", nargs="?", help="要检查的 md 文件路径（可选）")
    chk.add_argument("--type", choices=["summary", "diary"], help="内容类型")
    chk.add_argument("--course", help="课程名（如 CSAPP）")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "context":
        cmd_context(args)
    elif args.command == "read":
        cmd_read()
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()


def cmd_status():
    problems = settings.validate()
    print("=== Tech Learning OS 状态 ===")
    print(f"API 模型:   {settings.model}")
    print(f"API 地址:   {settings.base_url}")
    print(f"API Key:    {'已设置' if settings.api_key else '未设置'}")
    print(f"笔记目录:   {settings.notes_path}")
    print(f"当前书籍:   {settings.current_book or '未设置'}")
    print(f"当前章节:   {settings.current_chapter or '未设置'}")
    if problems:
        print(f"\n问题:")
        for p in problems:
            print(f"  - {p}")


def cmd_context(args):
    if args.book:
        settings.current_book = args.book
    if args.chapter:
        settings.current_chapter = args.chapter
    settings.save_state()
    print(f"当前书籍: {settings.current_book or '未设置'}")
    print(f"当前章节: {settings.current_chapter or '未设置'}")
    print(f"笔记路径: {settings.notes_path}")


def _read_clipboard() -> str:
    """从系统剪贴板读取文本（macOS 用 pbpaste）。"""
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except Exception:
        return ""


def cmd_read():
    if not settings.current_book:
        print("请先设置上下文：tlos context --book CSAPP --chapter Preface")
        return

    # 读取剪贴板
    text = _read_clipboard()
    if not text:
        print("剪贴板为空。请先在 PDF 或网页中复制一段英文（Cmd+C），再运行 tlos read。")
        return

    client = AIClient()
    print(f"📖 {settings.current_book} · {settings.current_chapter}")
    print(f"📋 剪贴板内容 ({len(text)} 字符)：")
    print(text[:200] + ("..." if len(text) > 200 else ""))
    print()

    # 调用 AI
    print("⏳ 分析中...")
    try:
        result = client.analyze(text, settings.current_book, settings.current_chapter)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    # 显示结果
    print()
    print("─" * 50)
    print(f"📝 翻译：\n{result['translation']}")
    print()

    terms = result.get("terms", [])
    if terms:
        for i, t in enumerate(terms, 1):
            print(f"🔹 术语 {i}: {t['term']}")
            print(f"   {t['definition_zh']}")
            chunks = t.get("chunks", [])
            if chunks:
                for c in chunks:
                    print(f"   📎 {c['en']} → {c['zh']} ({c.get('note', '')})")
            related = t.get("related", [])
            if related:
                print(f"   🔗 关联: {', '.join(related)}")
            print()
    else:
        print("(未提取到专业术语)")

    note = result.get("note", "")
    if note:
        print(f"💡 {note}")
        print()

    print("─" * 50)

    # 我的理解
    print("输入你的理解（可跳过，直接按 Enter）：")
    try:
        understanding = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        understanding = ""

    # 保存
    for t in terms:
        t["translation"] = result["translation"]
        path = save_note(t, text, understanding)
        print(f"✅ 已保存: {path}")
    print()


# === tlos check ===

def _scan_check_dirs():
    """扫描 notes/Summary/ 和 notes/Diary/ 下所有可用目录。"""
    base = settings.notes_dir
    dirs = []
    for content_type in ["Summary", "Diary"]:
        type_dir = os.path.join(base, content_type)
        if not os.path.isdir(type_dir):
            continue
        # 二级目录（课程目录）
        try:
            entries = sorted(os.listdir(type_dir))
        except OSError:
            continue
        for entry in entries:
            course_dir = os.path.join(type_dir, entry)
            if os.path.isdir(course_dir):
                dirs.append({
                    "type": content_type.lower(),
                    "path": course_dir,
                })
        # 一级目录下直接有 .md 文件
        if any(f.endswith(".md") for f in entries):
            dirs.append({
                "type": content_type.lower(),
                "path": type_dir,
            })
    return dirs


def _infer_type_from_path(path: str) -> str:
    """从文件路径推断内容类型。"""
    normalized = os.path.normpath(path)
    if "Diary" in normalized.split(os.sep):
        return "diary"
    if "Summary" in normalized.split(os.sep):
        return "summary"
    return "summary"


def _find_latest_md(directory: str) -> Optional[str]:
    """递归查找目录下最新修改的 .md 文件。"""
    pattern = os.path.join(directory, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _find_latest_check_md():
    """在所有 check 目录中找最新的 .md 文件。"""
    dirs = _scan_check_dirs()
    candidates = []
    for d in dirs:
        f = _find_latest_md(d["path"])
        if f:
            candidates.append(f)
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)




def cmd_check(args):
    filepath = args.path

    if filepath:
        if not os.path.isfile(filepath):
            print(f"❌ 文件不存在：{filepath}")
            return
        content_type = _infer_type_from_path(filepath)
    elif args.type:
        base = os.path.join(settings.notes_dir, args.type.capitalize())
        if args.course:
            base = os.path.join(base, args.course)
        if not os.path.isdir(base):
            print(f"❌ 目录不存在：{base}")
            return
        filepath = _find_latest_md(base)
        if not filepath:
            print(f"❌ 目录下没有 .md 文件：{base}")
            return
        content_type = args.type
    else:
        filepath = _find_latest_check_md()
        if not filepath:
            print("❌ notes/Summary/ 和 notes/Diary/ 下没有找到 .md 文件。")
            print("  请先创建目录并放入 .md 文件，例如：")
            print("  mkdir -p notes/Summary/CSAPP")
            return
        content_type = _infer_type_from_path(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    type_label = "技术总结" if content_type == "summary" else "日记"
    print(f"🔍 写作检查 · {type_label}")
    print(f"📄 {filepath} ({len(text)} 字符)")
    print()

    client = AIClient()
    print("⏳ 检查中...")
    try:
        result = client.check_writing(text, content_type)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    print()
    issues = result.get("issues", [])
    type_label_zh = {
        "grammar": "语法错误",
        "word_choice": "用词不当",
        "chinglish": "中式英语",
        "unnatural": "表达不自然",
        "missing_english": "缺英文表达",
    }
    for i, issue in enumerate(issues, 1):
        itype = issue.get("issue_type", "")
        tlabel = type_label_zh.get(itype, itype)
        snippet = issue.get("text", "")
        explanation = issue.get("explanation_zh", "")

        if itype == "missing_english":
            print(f"问题 {i}: \"{snippet}\"")
            print(f"  类型: {tlabel}")
            print(f"  建议: {explanation}")
        else:
            print(f"问题 {i}: \"{snippet}\"")
            print(f"  类型: {tlabel}")
            print(f"  说明: {explanation}")
        print()

    overall = result.get("overall_note", "")
    if overall:
        print(f"💡 整体建议: {overall}")
        print()
