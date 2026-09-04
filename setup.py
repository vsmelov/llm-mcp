#!/usr/bin/env python3
"""Проверка готовности к запуску: зависимости, .env с ключом OpenRouter.

    python setup.py

Ничего не скачивает и никуда не отправляет — только смотрит, что на месте,
создаёт .env из шаблона и печатает готовую команду подключения.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OK, WARN, BAD = "[ok]", "[ ! ]", "[x ]"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

problems: list[str] = []


def say(mark: str, text: str, hint: str = "") -> None:
    print(f" {mark} {text}")
    if hint:
        print(f"      {hint}")


def fail(text: str, hint: str) -> None:
    say(BAD, text, hint)
    problems.append(text)


def check_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        say(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} — нужен 3.10+", "поставь свежий Python")


def check_deps() -> None:
    missing = [
        pkg
        for mod, pkg in (("mcp", "mcp"), ("httpx", "httpx"), ("dotenv", "python-dotenv"))
        if importlib.util.find_spec(mod) is None
    ]
    if missing:
        fail(
            "не установлены зависимости: " + ", ".join(missing),
            f'"{sys.executable}" -m pip install -r requirements.txt',
        )
    else:
        say(OK, "зависимости установлены")


def check_env() -> None:
    env_path, example = ROOT / ".env", ROOT / ".env.example"
    if not env_path.exists():
        if not example.exists():
            fail("нет ни .env, ни .env.example", "репозиторий склонирован не полностью?")
            return
        shutil.copyfile(example, env_path)
        say(WARN, "создан .env из .env.example", f"впиши свой ключ: {env_path}")

    key = model = ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("OPENROUTER_API_KEY="):
            key = line.partition("=")[2].strip()
        elif line.startswith("OPENROUTER_MODEL="):
            model = line.partition("=")[2].strip()

    if key.startswith("sk-or-v1-") and len(key) > 20:
        say(OK, "OPENROUTER_API_KEY задан")
    elif key:
        fail("OPENROUTER_API_KEY не похож на ключ OpenRouter",
             "ключи начинаются с sk-or-v1-, взять на https://openrouter.ai/settings/keys")
    else:
        fail("OPENROUTER_API_KEY не заполнен в .env",
             "ключ с https://openrouter.ai/settings/keys")

    say(OK, f"модель по умолчанию: {model}" if model
        else "модель по умолчанию: google/gemini-2.5-flash-lite (не задана в .env)")


def main() -> int:
    print(f"\nllm-mcp — проверка окружения\n{ROOT}\n")
    check_python()
    check_deps()
    check_env()

    if problems:
        print(f"\nНе готово, {len(problems)} пункт(ов):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nВсё на месте.\n\nПодключить к Claude Code:\n")
    print(f'  claude mcp add --scope user llm -- "{sys.executable}" "{ROOT / "server.py"}"\n')
    print("Напоминание из README: для обычных задач haiku-субагент из Claude проще")
    print("и умнее. Этот сервер — для массовых мелких вызовов и сторонних моделей.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
