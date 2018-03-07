"""A simple time-expiring cache."""

import time


class Cache:
    def __init__(self, timeout):
        self._timeout = timeout
        # Contains key : (timeout, value)
        self._spot_cache = {}

    def value_for_key(self, key):
        """Return value for key from cache, if present and newer than timeout."""
        if key in self._spot_cache:
            cache_time, value = self._spot_cache[key]
            age = time.time() - cache_time
            if age < self._timeout:
                return value
            else:
                return None
        else:
            return None

    def set_value_for_key(self, value, key):
        self._spot_cache[key] = (time.time(), value)
