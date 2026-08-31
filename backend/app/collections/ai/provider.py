"""LiteLLM seam: local Ollama first, cloud provider if configured, deterministic template last.

Built in Phase 6 (MASTER_PLAN.md). This module only knows how to make
ONE LLM call each way -- the fallback chain across rungs (and the
deterministic third rung itself, `ai/fallback.py`) lives in each
`ai/roles/*.py` file, since what counts as an acceptable failure differs
per role.
"""

from __future__ import annotations

import litellm

from app.collections.config import settings
from app.collections.observability import metrics


class LLMError(Exception):
    """Any failure calling an LLM -- network, timeout, empty response.
    Callers catch this and fall through to the next rung."""


def call_ollama(prompt: str, *, temperature: float = 0.0, max_tokens: int = 300) -> str:
    try:
        response = litellm.completion(
            model=f"ollama/{settings.OLLAMA_MODEL}",
            messages=[{"role": "user", "content": prompt}],
            api_base=settings.OLLAMA_API_BASE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        metrics.increment_llm_calls("ollama", "error")
        raise LLMError(str(exc)) from exc

    content = response.choices[0].message.content
    if not content or not content.strip():
        metrics.increment_llm_calls("ollama", "error")
        raise LLMError("Ollama returned an empty response.")
    metrics.increment_llm_calls("ollama", "success")
    return str(content).strip()


def call_cloud(prompt: str, *, temperature: float = 0.0, max_tokens: int = 300) -> str:
    """Only attempted if `settings.CLOUD_LLM_MODEL` is configured -- never
    required for this project to run."""
    if not settings.CLOUD_LLM_MODEL:
        raise LLMError("No cloud LLM configured (COLLECTIONS_CLOUD_LLM_MODEL unset).")
    try:
        response = litellm.completion(
            model=settings.CLOUD_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=settings.LLM_TIMEOUT_SECONDS,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        metrics.increment_llm_calls("cloud", "error")
        raise LLMError(str(exc)) from exc

    content = response.choices[0].message.content
    if not content or not content.strip():
        metrics.increment_llm_calls("cloud", "error")
        raise LLMError("Cloud LLM returned an empty response.")
    metrics.increment_llm_calls("cloud", "success")
    return str(content).strip()
