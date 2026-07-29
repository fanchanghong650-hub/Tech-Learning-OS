"""DeepSeek API 客户端 — 封装 API 调用逻辑"""

import json
from openai import OpenAI
from ..config import settings
from ..prompts.templates import (
    SYSTEM_PROMPT_TECH, SYSTEM_PROMPT_LN, build_user_prompt,
    CHECK_PROMPT_TECHNICAL, CHECK_PROMPT_CASUAL, build_check_user_prompt,
)


class AIClient:
    """调用 DeepSeek API 分析文本。"""

    def __init__(self):
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    def analyze(self, text: str, book: str = "", chapter: str = "", mode: str = "tech") -> dict:
        """分析一段英文文本。

        Args:
            text: 用户输入的英文段落
            book: 当前书名/系列名
            chapter: 当前章节/卷
            mode: "tech"（技术阅读）或 "ln"（轻小说）

        Returns:
            dict: {"translation": str, "chunks": [...]}
        """
        system_prompt = SYSTEM_PROMPT_LN if mode == "ln" else SYSTEM_PROMPT_TECH
        user_prompt = build_user_prompt(text, book, chapter, mode)

        try:
            response = self._client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise RuntimeError(f"API 调用失败：{e}") from e

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI 返回的不是合法 JSON：{e}\n\n原始返回：{content[:500]}") from e

        result.setdefault("translation", "")
        result.setdefault("chunks", [])
        return result

    def check_writing(self, text: str, content_type: str = "summary") -> dict:
        """检查用户的英文写作表达。"""
        if content_type == "diary":
            system_prompt = CHECK_PROMPT_CASUAL
        else:
            system_prompt = CHECK_PROMPT_TECHNICAL

        user_prompt = build_check_user_prompt(text, content_type)

        try:
            response = self._client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise RuntimeError(f"API 调用失败：{e}") from e

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI 返回的不是合法 JSON：{e}\n\n原始返回：{content[:500]}") from e

        result.setdefault("issues", [])
        result.setdefault("overall_note", "")
        return result
