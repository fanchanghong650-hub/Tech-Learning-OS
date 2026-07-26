"""DeepSeek API 客户端 — 封装 API 调用逻辑"""

import json
from openai import OpenAI
from ..config import settings
from ..prompts.templates import (
    SYSTEM_PROMPT, build_user_prompt,
    CHECK_PROMPT_TECHNICAL, CHECK_PROMPT_CASUAL, build_check_user_prompt,
)


class AIClient:
    """调用 DeepSeek API 分析技术文本。

    使用方式：
        client = AIClient()
        result = client.analyze("A cache miss occurs when...", "CSAPP", "Chapter 6")
    """

    def __init__(self):
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    def analyze(self, text: str, book: str = "", chapter: str = "") -> dict:
        """分析一段英文技术文本。

        Args:
            text: 用户输入的英文段落
            book: 当前书名（如 "CSAPP"）
            chapter: 当前章节（如 "Chapter 6"）

        Returns:
            dict: AI 返回的结构化分析结果

        Raises:
            RuntimeError: API 调用失败或返回格式异常
        """
        user_prompt = build_user_prompt(text, book, chapter)

        try:
            response = self._client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
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

        # 确保必要字段存在
        result.setdefault("translation", "")
        result.setdefault("terms", [])
        result.setdefault("note", "")
        return result

    def check_writing(self, text: str, content_type: str = "summary") -> dict:
        """检查用户的英文写作表达。

        Args:
            text: 用户写的中英文混合文本
            content_type: 内容类型，"summary"（技术总结）或 "diary"（日记）

        Returns:
            dict: {"issues": [...], "overall_note": ""}

        Raises:
            RuntimeError: API 调用失败或返回格式异常
        """
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
