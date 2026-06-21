"""NL->SQL generation. Output is *untrusted* until it passes the guard."""

from __future__ import annotations

import re

from loguru import logger

from txt2sql.generate.prompt import build_prompt
from txt2sql.models import GeneratedSQL, SchemaInfo
from txt2sql.providers.base import LLMProvider


def _strip_fences(text: str) -> str:
    """Models often wrap SQL in ```sql fences or add prose. Extract the SQL."""
    text = text.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


class Generator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def generate(self, question: str, schema: SchemaInfo) -> GeneratedSQL:
        prompt = build_prompt(question, schema)
        raw = await self.provider.generate(prompt)
        sql = _strip_fences(raw)
        logger.debug("generated SQL: {}", sql)
        return GeneratedSQL(raw_sql=sql, explanation=f"Generated for: {question}")
