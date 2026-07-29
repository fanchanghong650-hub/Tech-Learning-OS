"""CLI 入口 — 命令行交互主循环"""

import argparse
import glob
import os
import subprocess
from typing import Optional
from .config import settings
from .ai.client import AIClient
from .notes.manager import append_note


def main():
    parser = argparse.ArgumentParser(
        prog="tlos",
        description="Tech Learning OS — 本地 AI 技术阅读助手",
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")
    sub.add_parser("status", help="查看当前配置状态")

    ctx = sub.add_parser("context", help="设置或查看当前阅读上下文")
    ctx.add_argument("--book", help="书名/系列名")
    ctx.add_argument("--chapter", help="章节/卷")
    ctx.add_argument("--mode", choices=["tech", "ln"], help="阅读模式")

    read = sub.add_parser("read", help="开始交互式阅读")
    read.add_argument("--mode", choices=["tech", "ln"], help="阅读模式（覆盖已保存的上下文）")

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
        cmd_read(args)
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()


def cmd_status():
    problems = settings.validate()
    mode_label = "技术阅读" if settings.mode == "tech" else "轻小说"
    subdir = "Reading" if settings.mode == "tech" else "LN"
    print("=== Tech Learning OS 状态 ===")
    print(f"API 模型:   {settings.model}")
    print(f"API 地址:   {settings.base_url}")
    print(f"API Key:    {'已设置' if settings.api_key else '未设置'}")
    print(f"阅读模式:   {mode_label} ({settings.mode})")
    print(f"笔记目录:   {os.path.join(settings.notes_dir, subdir)}")
    print(f"当前书籍:   {settings.current_book or '未设置'}")
    print(f"当前章节:   {settings.current_chapter or '未设置'}")
    if problems:
        print(f"\n问题:")
        for p in problems:
            print(f"  - {p}")


# === tlos context ===

def _scan_books(mode: str) -> list[str]:
    """扫描指定模式下的所有书/系列目录。"""
    subdir = "LN" if mode == "ln" else "Reading"
    base = os.path.join(settings.notes_dir, subdir)
    if not os.path.isdir(base):
        return []
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return []
    return [e for e in entries if os.path.isdir(os.path.join(base, e))]


def _scan_chapters(mode: str, book: str) -> list[str]:
    """扫描指定书/系列下的所有章节/卷。"""
    subdir = "LN" if mode == "ln" else "Reading"
    base = os.path.join(settings.notes_dir, subdir, book)
    if not os.path.isdir(base):
        return []
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return []
    return [e for e in entries if os.path.isdir(os.path.join(base, e))]


def _interactive_context(mode: str):
    """交互式选择书籍和章节。"""
    label = "轻小说系列" if mode == "ln" else "书籍"
    books = _scan_books(mode)
    if not books:
        subdir = "LN" if mode == "ln" else "Reading"
        print(f"notes/{subdir}/ 下还没有任何目录。")
        print(f"请先创建：mkdir -p notes/{subdir}/书名/章节")
        return

    print(f"=== 选择{label} ===")
    for i, b in enumerate(books, 1):
        display = b.replace("-", " ").title()
        print(f"  {i}. {display}")
    print(f"  0. 取消")

    try:
        choice = input("请选择（输入编号）：").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if choice == "0" or not choice:
        return
    try:
        idx = int(choice) - 1
        selected_book = books[idx]
    except (ValueError, IndexError):
        print("无效选择")
        return

    # 选章节
    chapters = _scan_chapters(mode, selected_book)
    chapter_label = "卷" if mode == "ln" else "章节"
    if not chapters:
        print(f"'{selected_book}' 下还没有子目录。")
        print(f"请先创建：mkdir -p notes/{'LN' if mode == 'ln' else 'Reading'}/{selected_book}/<{chapter_label}>")
        return

    print(f"\n=== 选择{chapter_label} ===")
    for i, c in enumerate(chapters, 1):
        display = c.replace("-", " ").title()
        print(f"  {i}. {display}")
    print(f"  0. 取消")

    try:
        choice = input("请选择（输入编号）：").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if choice == "0" or not choice:
        return
    try:
        idx = int(choice) - 1
        selected_chapter = chapters[idx]
    except (ValueError, IndexError):
        print("无效选择")
        return

    settings.current_book = selected_book
    settings.current_chapter = selected_chapter
    settings.save_state()

    mode_label = "轻小说模式" if mode == "ln" else "技术模式"
    print(f"\n✅ 已切换：{mode_label} · {selected_book} · {selected_chapter}")


def cmd_context(args):
    if args.mode:
        settings.mode = args.mode
        settings.save_state()

    if args.book:
        settings.current_book = args.book
    if args.chapter:
        settings.current_chapter = args.chapter

    if args.book or args.chapter:
        settings.save_state()
        mode_label = "轻小说" if settings.mode == "ln" else "技术"
        print(f"模式: {mode_label}")
        print(f"当前书籍: {settings.current_book or '未设置'}")
        print(f"当前章节: {settings.current_chapter or '未设置'}")
    else:
        # 交互式选择
        _interactive_context(settings.mode)


# === tlos read ===

def _read_clipboard() -> str:
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except Exception:
        return ""


def cmd_read(args):
    if args.mode:
        settings.mode = args.mode
        settings.save_state()

    if not settings.current_book:
        if _scan_books(settings.mode):
            _interactive_context(settings.mode)
            if not settings.current_book:
                return
        else:
            return

    mode_label = "轻小说" if settings.mode == "ln" else "技术"
    client = AIClient()
    read_count = 0
    first_save_path = None
    last_text = None

    print(f"📖 {settings.current_book} · {settings.current_chapter}  [{mode_label}]")
    print("持续阅读模式 — 每次复制英文后回来按 Enter 即可分析")
    print("输入 :q 退出，Ctrl+C 也可退出")
    print()

    while True:
        # 检查剪贴板
        text = _read_clipboard()
        if text and text == last_text:
            print(f"📋 剪贴板内容未变化，已跳过（{len(text)} 字符）")
            print()
            try:
                user_input = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_input.lower() == ":q":
                break
            continue
        if not text:
            print("剪贴板为空，等待中...（复制内容后按 Enter，输入 :q 退出）")
        else:
            print(f"📋 剪贴板 ({len(text)} 字符)：{text[:100]}{'...' if len(text) > 100 else ''}")
            print()

        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() == ":q":
            break
        if not text and not user_input:
            continue

        if not text:
            continue

        print("⏳ 分析中...")
        try:
            result = client.analyze(text, settings.current_book, settings.current_chapter, settings.mode)
        except RuntimeError as e:
            print(f"❌ {e}")
            continue

        print()
        print("─" * 50)
        print(f"📝 翻译：\n{result['translation']}")
        print()

        chunks = result.get("chunks", [])
        if chunks:
            print("📎 语块积累:")
            for i, c in enumerate(chunks, 1):
                print(f"  {i}. {c['en']}")
                print(f"     → {c['zh']}")
                if c.get("note"):
                    print(f"     {c['note']}")
            print()
        else:
            print("(未提取到需要积累的表达)")
            print()

        print("─" * 50)

        print("输入你的理解（可跳过，直接按 Enter）：")
        try:
            understanding = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            understanding = ""

        path = append_note(text, result, understanding, read_count)
        if read_count == 0:
            first_save_path = path
        read_count += 1
        last_text = text

        print(f"✅ 已追加到: {path}")
        print()
        print("─" * 50)
        print("继续阅读？复制下一段英文后按 Enter，输入 :q 退出")

    # 退出统计
    print()
    if read_count > 0:
        print(f"📊 本次会话共阅读 {read_count} 段，保存至：{first_save_path}")
    else:
        print("本次会话未阅读内容。")


# === tlos check ===

def _scan_check_dirs():
    base = settings.notes_dir
    dirs = []
    for content_type in ["Summary", "Diary"]:
        type_dir = os.path.join(base, content_type)
        if not os.path.isdir(type_dir):
            continue
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
        if any(f.endswith(".md") for f in entries):
            dirs.append({
                "type": content_type.lower(),
                "path": type_dir,
            })
    return dirs


def _infer_type_from_path(path: str) -> str:
    normalized = os.path.normpath(path)
    if "Diary" in normalized.split(os.sep):
        return "diary"
    if "Summary" in normalized.split(os.sep):
        return "summary"
    return "summary"


def _find_latest_md(directory: str) -> Optional[str]:
    pattern = os.path.join(directory, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _find_latest_check_md():
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
