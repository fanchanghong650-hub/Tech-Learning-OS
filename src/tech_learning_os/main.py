"""CLI 入口 — 命令行交互主循环"""

import argparse
import subprocess
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

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "context":
        cmd_context(args)
    elif args.command == "read":
        cmd_read()
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
