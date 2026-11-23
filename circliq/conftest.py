import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    """Rate-limit counters live in the cache; make every test start clean."""
    cache.clear()
    yield
    cache.clear()
