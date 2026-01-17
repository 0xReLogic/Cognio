from src.config import settings
from src.engram import EngramIndex


def test_engram_buckets_for_text():
    index = EngramIndex()
    buckets = index.buckets_for_text("Hello world from Cognio")
    assert buckets
    assert all(isinstance(bucket, int) for bucket in buckets)


def test_engram_bucket_limit():
    index = EngramIndex()
    original_limit = settings.engram_query_bucket_limit
    try:
        settings.engram_query_bucket_limit = 1
        buckets = index.buckets_for_query("hello world from cognio")
        assert len(buckets) <= 1
    finally:
        settings.engram_query_bucket_limit = original_limit
