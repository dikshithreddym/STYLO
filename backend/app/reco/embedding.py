from __future__ import annotations

from threading import Lock
from typing import List, Optional
from functools import lru_cache

import os

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - runtime import error surfaced at first encode
    SentenceTransformer = None  # type: ignore


class Embedder:
    _instance: "Optional[Embedder]" = None
    _lock: Lock = Lock()

    def __init__(self, model_name: Optional[str] = None) -> None:
        name = model_name or os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed; add it to requirements.txt")
        self.model = SentenceTransformer(name)

    @classmethod
    @lru_cache(maxsize=1)
    def instance(cls) -> "Embedder":
        """Get singleton embedder instance with LRU cache."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = Embedder()
        return cls._instance

    def encode(self, texts: List[str]):
        return self.model.encode(texts, normalize_embeddings=False, convert_to_numpy=True)
