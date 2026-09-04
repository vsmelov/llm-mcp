# llm-mcp

MCP-сервер для дешёвых LLM через [OpenRouter](https://openrouter.ai). Два инструмента:
`llm` (один запрос: prompt → текст + usage/стоимость) и `llm_models` (список моделей с ценами).

## ⚠️ Когда пользоваться (редко!)

Для большинства задач **проще и лучше запустить haiku-субагента прямо из Claude**
(Agent tool, `model: "haiku"`): у субагента есть тулзы, доступ к файлам и контекст сессии,
а оплата идёт из подписки. OpenRouter уместен только когда:

- нужно массово прогнать сотни/тысячи мелких независимых запросов из **скрипта** (см. ниже);
- нужна конкретная сторонняя модель (DeepSeek, Gemini, Llama, ...);
- нужно сравнить ответы разных моделей.

Гонять тулзу `llm` в цикле из Claude — антипаттерн: каждый вызов стоит полный
inference-круг. Для массовых задач — прямые запросы из питона.

## Где лежат ключи

Ключ OpenRouter лежит в **`.env` в корне этой репы** (`llm-mcp/.env`, в гит не коммитится):

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.5-flash-lite   # дефолтная модель (опционально)
```

Путь передаётся через `load_dotenv()` относительно корня репы (см. `server.py`).

## Прямые запросы из своих скриптов (минуя MCP)

```python
import os, httpx
from dotenv import load_dotenv
load_dotenv(r"C:\path\to\llm-mcp\.env")

r = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
    json={
        "model": "google/gemini-2.5-flash-lite",
        "messages": [{"role": "user", "content": "Привет!"}],
        "usage": {"include": True},   # вернёт точную стоимость запроса
    },
    timeout=180,
)
print(r.json()["choices"][0]["message"]["content"])
print(r.json()["usage"])  # prompt_tokens, completion_tokens, cost ($)
```

API совместим с OpenAI chat/completions — работает и `openai`-клиент с
`base_url="https://openrouter.ai/api/v1"`.

## Установка и запуск

```bash
pip install -r requirements.txt
python server.py   # stdio MCP
```

## Регистрация в Claude Code

```bash
claude mcp add --scope user llm -- python C:\path\to\llm-mcp\server.py
```
