"""Stub module for deleted cache_kv — prevents ImportError in legacy pipeline files."""


class CacheKV:
    """No-op stub. Legacy caching layer removed in production refactor."""
    def __init__(self, *args, **kwargs): pass
    def get(self, key, default=None): return default
    def set(self, key, value, **kwargs): pass
    def delete(self, key): pass
    def __contains__(self, key): return False


class CacheUtils:
    """No-op stub with decorator support."""
    def __init__(self, *args, **kwargs): pass

    @staticmethod
    def cache_method_output(*args, **kwargs):
        """No-op decorator stub."""
        def decorator(func):
            return func
        # Called as @CacheUtils.cache_method_output or @CacheUtils.cache_method_output(...)
        if len(args) == 1 and callable(args[0]):
            return args[0]   # bare @decorator
        return decorator      # @decorator(...)

    def __getattr__(self, name):
        return lambda *a, **kw: None
