import pytest

from app.collections.ai import provider
from app.collections.tests.ai.conftest import requires_ollama


@requires_ollama
def test_call_ollama_returns_nonempty_text() -> None:
    text = provider.call_ollama("Reply with exactly one word: hello")
    assert text.strip()


def test_call_cloud_raises_when_unconfigured() -> None:
    """No COLLECTIONS_CLOUD_LLM_MODEL set -- never required to run this project."""
    with pytest.raises(provider.LLMError):
        provider.call_cloud("irrelevant")
