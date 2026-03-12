from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError

from logger import logger


_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)   # override=False: real env vars win


AI_PROVIDER: Final[str] = os.getenv("AI_PROVIDER", "openai").lower()

# OpenAI settings
_OPENAI_API_KEY: str   = os.getenv("OPENAI_API_KEY", "")
_OPENAI_MODEL: str     = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_OPENAI_BASE_URL: str  = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Shared generation settings
_TEMPERATURE: float    = float(os.getenv("AI_TEMPERATURE", "0.2"))
_MAX_TOKENS: int       = int(os.getenv("AI_MAX_TOKENS", "1024"))
_TIMEOUT: float        = float(os.getenv("AI_TIMEOUT_SECONDS", "10.0"))


def _validate_config() -> None:
    """
    Raise a clear RuntimeError at startup if critical env vars are missing.
    This surfaces misconfiguration immediately rather than at first request.
    """
    if AI_PROVIDER == "openai" and not _OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or export it as an environment variable. "
            "See README.md for setup instructions."
        )


_validate_config()
logger.info("AI client configured — provider=%s  model=%s", AI_PROVIDER, _OPENAI_MODEL)


_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        # Create httpx client without deprecated proxies parameter
        http_client = httpx.AsyncClient(timeout=_TIMEOUT)
        _openai_client = AsyncOpenAI(
            api_key=_OPENAI_API_KEY,
            http_client=http_client,
        )
    return _openai_client



# A message is a plain dict: {"role": "system"|"user"|"assistant", "content": str}
# Using a simple dict (rather than a dataclass) keeps the interface compatible
# with whatever structure ai_prompt.py will build.
Message = dict[str, str]


async def chat_completion(
    messages: list[Message],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> str:
    
    _temp    = temperature if temperature is not None else _TEMPERATURE
    _tokens  = max_tokens  if max_tokens  is not None else _MAX_TOKENS
    _tout    = timeout     if timeout     is not None else _TIMEOUT

    logger.debug(
        "chat_completion → provider=%s model=%s temp=%s max_tokens=%s messages=%d",
        AI_PROVIDER, _OPENAI_MODEL, _temp, _tokens, len(messages),
    )

    try:
        if AI_PROVIDER == "openai":
            return await _openai_chat(messages, _temp, _tokens, _tout)

        # Stub for future providers — extend here without touching routers.py
        raise AIClientError(f"Unsupported AI_PROVIDER: {AI_PROVIDER!r}")

    except (AITimeoutError, AIConnectionError, AIServiceError, AIClientError):
        raise   # re-raise our own typed exceptions untouched

    except Exception as exc:
        # Catch anything unexpected (e.g. pydantic validation inside openai SDK)
        raise AIClientError(f"Unexpected AI client error: {exc}") from exc


async def _openai_chat(
    messages: list[Message],
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    """Internal handler for OpenAI-compatible backends."""
    client = _get_openai_client()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=_OPENAI_MODEL,
                messages=messages,          # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        logger.warning("AI request timed out after %.1f s", timeout)
        raise AITimeoutError(
            f"AI service did not respond within {timeout:.0f} seconds."
        ) from exc

    except APITimeoutError as exc:
        logger.warning("OpenAI SDK timeout: %s", exc)
        raise AITimeoutError(str(exc)) from exc

    except APIConnectionError as exc:
        logger.error("OpenAI connection error: %s", exc)
        raise AIConnectionError(
            f"Could not reach the AI service. Check your network connection. ({exc})"
        ) from exc

    except APIStatusError as exc:
        logger.error("OpenAI API status error %s: %s", exc.status_code, exc.message)
        raise AIServiceError(
            f"AI service returned an error (HTTP {exc.status_code}): {exc.message}"
        ) from exc

    # Extract the text from the first choice
    content = response.choices[0].message.content or ""
    logger.debug("AI reply received — %d chars", len(content))
    return content.strip()


class AIClientError(Exception):
    """Base class for all AI client errors."""


class AITimeoutError(AIClientError):
    """LLM did not respond in time — map to HTTP 504 or a managed message."""


class AIConnectionError(AIClientError):
    """Network-level failure reaching the AI provider."""


class AIServiceError(AIClientError):
    """AI API returned a non-2xx response (rate-limit, server error, etc.)."""


async def test_connection() -> None:
    """
    Send a minimal prompt to confirm the AI connection is working.

    Run directly:
        python ai_client.py

    Expected output (when key is valid):
        [ai_client] Test prompt  : Hello AI
        [ai_client] AI responded : Hello! How can I help you today?
        [ai_client] Connection test PASSED
    """
    test_prompt = "Hello AI"
    print(f"\n[ai_client] Test prompt  : {test_prompt}")
    print(f"[ai_client] Provider     : {AI_PROVIDER}")
    print(f"[ai_client] Model        : {_OPENAI_MODEL}")
    print(f"[ai_client] Timeout      : {_TIMEOUT}s\n")

    try:
        reply = await chat_completion(
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=60,
        )
        print(f"[ai_client] AI responded : {reply}")
        print("[ai_client] Connection test PASSED\n")

    except AITimeoutError as exc:
        print(f"[ai_client] TIMEOUT  — {exc}\n")
        raise SystemExit(1)

    except AIConnectionError as exc:
        print(f"[ai_client] CONNECTION ERROR — {exc}\n")
        raise SystemExit(1)

    except AIServiceError as exc:
        print(f"[ai_client] SERVICE ERROR — {exc}\n")
        raise SystemExit(1)

    except AIClientError as exc:
        print(f"[ai_client] CLIENT ERROR — {exc}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())
