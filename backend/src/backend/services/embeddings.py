from __future__ import annotations

from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

from backend.core.config import get_settings


def resolve_embedding_device() -> str:
    settings = get_settings()
    requested_device = settings.local_embedding_device.strip().lower()

    if requested_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"

    if requested_device == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"

    return requested_device or "cpu"


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    device = resolve_embedding_device()
    return SentenceTransformer(
        settings.local_embedding_model,
        cache_folder=settings.model_cache_dir.as_posix(),
        device=device,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=settings.local_embedding_batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()
