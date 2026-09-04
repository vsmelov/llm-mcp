# -*- coding: utf-8 -*-
"""llm-mcp — дешёвые LLM через OpenRouter.

Использовать РЕДКО: для большинства разовых задач проще запустить haiku-субагента
из Claude. Этот сервер — для массовых мелких вызовов и специфичных моделей.
Ключ: .env рядом с этим файлом (OPENROUTER_API_KEY). См. README.md.
"""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

INSTRUCTIONS = f"""Дешёвые LLM через OpenRouter (ключ в {ROOT / '.env'}).

ВАЖНО: пользоваться этим сервером нужно в редких случаях — обычно проще и лучше
запустить haiku-субагента из Claude (Agent tool, model='haiku'): у него есть тулзы,
файлы и контекст сессии. OpenRouter уместен, когда нужно: (а) массово прогнать
сотни мелких независимых запросов из скрипта, (б) конкретная сторонняя модель,
(в) сравнить ответы разных моделей.

Для скриптов вызывай API напрямую (см. README.md), а не эти тулзы в цикле.
Модель по умолчанию: {DEFAULT_MODEL} (env OPENROUTER_MODEL)."""

mcp = FastMCP("llm", instructions=INSTRUCTIONS)


def _key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(f"Нет ключа: положи OPENROUTER_API_KEY в {ROOT / '.env'} (см. .env.example)")
    return key


@mcp.tool()
async def llm(prompt: str, model: str = "", system: str = "",
              max_tokens: int = 2000, temperature: float | None = None) -> str:
    """Один запрос к дешёвой LLM через OpenRouter. Вернёт текст ответа + строку usage.

    model — id модели OpenRouter (пусто = дефолтная). Примеры: google/gemini-2.5-flash-lite,
    deepseek/deepseek-chat-v3.1, openai/gpt-5-mini. Список с ценами — тулза llm_models."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = {"model": model or DEFAULT_MODEL, "messages": messages,
            "max_tokens": max_tokens, "usage": {"include": True}}
    if temperature is not None:
        body["temperature"] = temperature
    async with httpx.AsyncClient(timeout=180) as cl:
        r = await cl.post(f"{BASE}/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {_key()}"})
    if r.status_code != 200:
        return f"OpenRouter error {r.status_code}: {r.text[:500]}"
    d = r.json()
    text = d["choices"][0]["message"]["content"]
    u = d.get("usage", {})
    cost = u.get("cost")
    tail = f"\n\n[{d.get('model')}] in={u.get('prompt_tokens')} out={u.get('completion_tokens')}" + \
           (f" cost=${cost:.6f}" if isinstance(cost, (int, float)) else "")
    return text + tail


@mcp.tool()
async def llm_models(search: str = "", limit: int = 15) -> str:
    """Модели OpenRouter с ценами $/1M токенов (in/out). search — подстрока в id."""
    async with httpx.AsyncClient(timeout=60) as cl:
        r = await cl.get(f"{BASE}/models")
    rows = []
    for m in r.json().get("data", []):
        if search.lower() in m.get("id", "").lower():
            p = m.get("pricing", {})
            try:
                pin, pout = float(p.get("prompt", 0)) * 1e6, float(p.get("completion", 0)) * 1e6
            except (TypeError, ValueError):
                continue
            rows.append((m["id"], pin, pout, m.get("context_length") or 0))
    rows.sort(key=lambda x: x[1])
    lines = [f"{i} — in ${pin:.3f} / out ${pout:.3f} за 1M, ctx {ctx // 1000}k"
             for i, pin, pout, ctx in rows[:limit]]
    return "\n".join(lines) or "ничего не найдено"


if __name__ == "__main__":
    mcp.run()
