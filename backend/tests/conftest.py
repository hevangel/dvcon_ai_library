"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    """Reset module-level caches between tests for isolation.

    Several services cache singletons (the chat OpenAI client, the Chroma
    collection, the embedding model) via @lru_cache. Without clearing them, a
    monkeypatched fake installed by one test would leak into the next. This
    autouse fixture clears them before every test.
    """
    from backend.services import chat, indexer

    chat._get_chat_client.cache_clear()
    indexer._cached_chroma_client.cache_clear()
    indexer._cached_chroma_collection.cache_clear()
    indexer._desired_embedding_model.cache_clear()
    yield
