from src.nodes.cache_node import MESICache


def test_cache_put_get_and_update():
    cache = MESICache(capacity=2)
    entry = cache.put_local("a", {"value": 1})
    assert entry.state.value == "M"
    assert cache.get("a")["hit"] is True

    cache.receive_update("a", {"value": 2}, version=2)
    result = cache.get("a")
    assert result["value"] == {"value": 2}
    assert result["state"] == "S"


def test_lru_eviction():
    cache = MESICache(capacity=2, policy="LRU")
    cache.put_local("a", {"value": 1})
    cache.put_local("b", {"value": 2})
    cache.get("a")
    cache.put_local("c", {"value": 3})
    assert cache.get("a")["hit"] is True
    assert cache.get("b")["hit"] is False
