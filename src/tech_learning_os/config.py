"""配置管理 — 从环境变量和 .env 文件读取配置"""

import os
import json
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# 上下文状态保存文件（当前工作目录下）
STATE_FILE = ".tlos_state.json"


@dataclass
class Settings:
    """应用的全局配置。"""

    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"))
    notes_dir: str = field(default_factory=lambda: os.getenv("TLOS_NOTES_DIR", "notes"))
    current_book: str = ""
    current_chapter: str = ""

    def validate(self) -> list[str]:
        problems = []
        if not self.api_key:
            problems.append("缺少 DEEPSEEK_API_KEY，请在 .env 文件中设置")
        return problems

    @property
    def notes_path(self) -> str:
        book = self.current_book.lower().replace(" ", "-") if self.current_book else "general"
        chapter = self.current_chapter.lower().replace(" ", "-") if self.current_chapter else "misc"
        return os.path.join(self.notes_dir, book, chapter)

    def load_state(self):
        """从 .tlos_state.json 恢复上次的阅读上下文。"""
        path = os.path.join(os.getcwd(), STATE_FILE)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.current_book = data.get("book", "")
                self.current_chapter = data.get("chapter", "")
            except (json.JSONDecodeError, OSError):
                pass

    def save_state(self):
        """保存当前阅读上下文到 .tlos_state.json。"""
        path = os.path.join(os.getcwd(), STATE_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"book": self.current_book, "chapter": self.current_chapter}, f, ensure_ascii=False)


# 全局单例
settings = Settings()
settings.load_state()  # 启动时恢复上次的上下文
