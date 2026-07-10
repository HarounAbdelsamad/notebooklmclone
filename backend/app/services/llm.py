"""LLM client for OpenRouter (OpenAI-compatible). Open models: Llama 3.3 / Qwen 2.5."""

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

Message = dict[str, str]


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        # OpenRouter attribution headers (optional but recommended).
        "HTTP-Referer": "https://notebooklm-clone.local",
        "X-Title": "NotebookLM Clone",
    }


async def stream_chat(
    messages: list[Message],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> AsyncIterator[str]:
    """Yield content deltas from a streamed chat completion."""
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=120.0) as client:
        async with client.stream(
            "POST", "/chat/completions", json=payload, headers=_headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content


async def complete(
    messages: list[Message],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Non-streaming completion (used by memory jobs and output generation)."""
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=120.0) as client:
        resp = await client.post("/chat/completions", json=payload, headers=_headers())
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
