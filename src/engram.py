"""Engram: hashed N-gram retrieval index for Cognio."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

from .config import settings

logger = logging.getLogger(__name__)


class EngramIndex:
    """Hashed N-gram index for O(1)-style candidate retrieval."""

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []
        return re.findall(r"[a-z0-9]+", normalized)

    def _parse_ngram_sizes(self) -> list[int]:
        raw = getattr(settings, "engram_ngram_sizes", "2,3")
        sizes: list[int] = []
        if isinstance(raw, str):
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    sizes.append(int(part))
                except ValueError:
                    continue
        elif isinstance(raw, Iterable):
            for item in raw:
                try:
                    sizes.append(int(item))
                except (TypeError, ValueError):
                    continue
        sizes = sorted({s for s in sizes if s > 0})
        return sizes or [2, 3]

    def _num_heads(self) -> int:
        return max(1, int(getattr(settings, "engram_num_heads", 4)))

    def _num_buckets(self) -> int:
        return max(1024, int(getattr(settings, "engram_num_buckets", 1000003)))

    def _bucket_limit(self) -> int:
        return max(0, int(getattr(settings, "engram_query_bucket_limit", 500)))

    def _hash_ngram(self, ngram: list[str], head: int, num_buckets: int) -> int:
        key = f"{head}|{' '.join(ngram)}"
        digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % num_buckets

    def buckets_for_text(self, text: str) -> list[int]:
        tokens = self._tokenize(text)
        if not tokens:
            return []
        ngram_sizes = self._parse_ngram_sizes()
        num_heads = self._num_heads()
        num_buckets = self._num_buckets()

        buckets: list[int] = []
        for idx in range(len(tokens)):
            for n in ngram_sizes:
                if idx + 1 < n:
                    continue
                ngram = tokens[idx - n + 1 : idx + 1]
                for head in range(num_heads):
                    buckets.append(self._hash_ngram(ngram, head, num_buckets))
        return buckets

    def bucket_counts(self, text: str) -> Counter[int]:
        return Counter(self.buckets_for_text(text))

    def buckets_for_query(self, query: str) -> list[int]:
        buckets = list(dict.fromkeys(self.buckets_for_text(query)))
        limit = self._bucket_limit()
        if limit and len(buckets) > limit:
            buckets = buckets[:limit]
        return buckets


engram_index = EngramIndex()
