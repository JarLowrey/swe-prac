"""Reference solution for Problem 6: Transactional key-value store."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from operator import itemgetter

# Marks a key deleted inside a transaction. It equals nothing else, so it can never be
# confused with a real value or with "this layer doesn't mention the key".
_TOMBSTONE = object()


class TransactionalKV:
    def __init__(self) -> None:
        self.base: dict[str, str] = {}
        self.layers: list[dict[str, object]] = []  # open transactions, innermost last
        self.history: defaultdict[str, list[tuple[int, str | None]]] = defaultdict(list)

    # -- helpers: reads go through _get/_view, writes through _write -------------------
    def _get(self, key: str) -> str | None:
        for layer in reversed(self.layers):
            if key in layer:
                value = layer[key]
                return None if value is _TOMBSTONE else value
        return self.base.get(key)

    def _view(self) -> dict[str, str]:
        merged: dict[str, object] = dict(self.base)
        for layer in self.layers:
            merged.update(layer)
        return {key: value for key, value in merged.items() if value is not _TOMBSTONE}

    def _write(self, timestamp: int, key: str, value: str | None) -> None:
        """Set (value) or delete (None) in the innermost layer, or permanently if none is open."""
        if self.layers:
            self.layers[-1][key] = _TOMBSTONE if value is None else value
        else:
            self._apply_to_base(timestamp, key, value)

    def _apply_to_base(self, timestamp: int, key: str, value: str | None) -> None:
        if value is None:
            self.base.pop(key, None)
        else:
            self.base[key] = value
        self.history[key].append((timestamp, value))

    # -- Level 1 ------------------------------------------------------------------------
    def set(self, timestamp: int, key: str, value: str) -> None:
        """Set or overwrite a key."""
        self._write(timestamp, key, value)

    def get(self, timestamp: int, key: str) -> str | None:
        """Return the key's value, or None if it is missing."""
        return self._get(key)

    def delete(self, timestamp: int, key: str) -> bool:
        """Remove the key; return False if it doesn't exist."""
        if self._get(key) is None:
            return False
        self._write(timestamp, key, None)
        return True

    # -- Level 2 ------------------------------------------------------------------------
    def count(self, timestamp: int, value: str) -> int:
        """Return how many keys currently hold value."""
        return sum(held == value for held in self._view().values())

    def list_keys(self, timestamp: int, prefix: str) -> str:
        """Return the keys starting with prefix, sorted ascending, as "k1, k2" ("" if none)."""
        return ", ".join(sorted(key for key in self._view() if key.startswith(prefix)))

    # -- Level 3 ------------------------------------------------------------------------
    def begin(self, timestamp: int) -> None:
        """Open a transaction; transactions can nest."""
        self.layers.append({})

    def commit(self, timestamp: int) -> bool:
        """Merge the innermost transaction into its parent (or permanent storage); False if none."""
        if not self.layers:
            return False
        top = self.layers.pop()
        if self.layers:
            self.layers[-1].update(top)  # inner: merge down, tombstones included
        else:
            for key, value in top.items():  # outermost: permanent, logged at commit ts
                self._apply_to_base(timestamp, key, None if value is _TOMBSTONE else value)
        return True

    def rollback(self, timestamp: int) -> bool:
        """Discard the innermost transaction's changes; return False if none is open."""
        if not self.layers:
            return False
        self.layers.pop()
        return True

    # -- Level 4 ------------------------------------------------------------------------
    def get_at(self, timestamp: int, key: str, time_at: int) -> str | None:
        """Return the key's value in permanent storage right after all operations at time_at."""
        entries = self.history.get(key, [])
        index = bisect_right(entries, time_at, key=itemgetter(0))
        return entries[index - 1][1] if index else None
