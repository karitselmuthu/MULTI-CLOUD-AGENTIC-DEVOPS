"""Compatibility import; disposable cache lives under data.redis."""

from data.redis.cache import RedisContextCache

__all__ = ["RedisContextCache"]
