"""Reference solution for Problem 6: Transactional key-value store."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from operator import itemgetter

# Design in brief
# ---------------
# - `base` is permanent storage. Each open transaction is a dict "layer" stacked on top of it,
#   and a nested transaction is another layer on top of that.
# - A read looks through the layers from the innermost outwards and takes the first layer that
#   mentions the key. The base is the fallback.
# - Deleting inside a transaction cannot simply remove the key, because the key may exist in a
#   layer or in the base below. So the layer records a tombstone instead.
# - Only changes to `base` are logged in `history`, which makes get_at a binary search.
#   Whatever happens inside a transaction is invisible to get_at until the outermost commit.

# Marks a key deleted inside a transaction. It equals nothing else, so it can never be
# confused with a real value or with "this layer doesn't mention the key".
_TOMBSTONE = object()


class TransactionalKV:
    def __init__(self) -> None:
        self.base: dict[str, str] = {}  # what exists once every open transaction has committed
        self.layers: list[dict[str, object]] = []  # open transactions, innermost last
        # key -> [(timestamp, value or None)] in time order, for permanent changes only.
        # None records a deletion.
        self.history: defaultdict[str, list[tuple[int, str | None]]] = defaultdict(list)

    # -- helpers: reads go through _get/_view, writes through _write -------------------
    def _get(self, key: str) -> str | None:
        for layer in reversed(self.layers):
            # `key in layer`, not layer.get(key): a tombstone must END the search, so that a
            # value in a lower layer can never show through a deletion above it.
            if key in layer:
                value = layer[key]
                return None if value is _TOMBSTONE else value
        return self.base.get(key)

    def _view(self) -> dict[str, str]:
        # Everything visible right now. Start from the base, then apply the layers from the
        # outermost to the innermost, so inner layers override outer ones. Tombstones are
        # filtered out LAST: dropping them earlier would let a lower value survive a deletion.
        # count and list_keys both use this one view, so they cannot disagree with get.
        merged: dict[str, object] = dict(self.base)
        for layer in self.layers:
            merged.update(layer)
        return {key: value for key, value in merged.items() if value is not _TOMBSTONE}

    def _write(self, timestamp: int, key: str, value: str | None) -> None:
        """Set (value) or delete (None) in the innermost layer, or permanently if none is open."""
        if self.layers:
            # Inside a transaction a delete is recorded as a tombstone, not by removing the key.
            self.layers[-1][key] = _TOMBSTONE if value is None else value
        else:
            self._apply_to_base(timestamp, key, value)

    def _apply_to_base(self, timestamp: int, key: str, value: str | None) -> None:
        # The only code that touches permanent storage, so also the only code that logs history.
        # pop(key, None) tolerates a key that is not in the base: for example a key that was
        # created and deleted inside the same transaction still arrives here as a tombstone.
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
        # None means "missing or already deleted at this nesting depth". It is a safe signal
        # because stored values are always strings.
        if self._get(key) is None:
            return False
        self._write(timestamp, key, None)
        return True

    # -- Level 2 ------------------------------------------------------------------------
    def count(self, timestamp: int, value: str) -> int:
        """Return how many keys currently hold value."""
        # Each comparison is a bool and True counts as 1, so sum() is the number of matches.
        return sum(held == value for held in self._view().values())

    def list_keys(self, timestamp: int, prefix: str) -> str:
        """Return the keys starting with prefix, sorted ascending, as "k1, k2" ("" if none)."""
        return ", ".join(sorted(key for key in self._view() if key.startswith(prefix)))

    # -- Level 3 ------------------------------------------------------------------------
    def begin(self, timestamp: int) -> None:
        """Open a transaction; transactions can nest."""
        # A new, empty layer. Nothing is copied, so begin is cheap however large the store is.
        self.layers.append({})

    def commit(self, timestamp: int) -> bool:
        """Merge the innermost transaction into its parent (or permanent storage); False if none."""
        if not self.layers:
            return False
        top = self.layers.pop()
        if self.layers:
            # Inner commit: merge into the parent layer. Tombstones are merged too, so a delete
            # made here still hides the parent's value. Nothing is permanent yet.
            self.layers[-1].update(top)  # inner: merge down, tombstones included
        else:
            # Outermost commit: the changes become permanent. Each one is logged at the COMMIT
            # timestamp, not at the time of the original set or delete.
            for key, value in top.items():  # outermost: permanent, logged at commit ts
                self._apply_to_base(timestamp, key, None if value is _TOMBSTONE else value)
        return True

    def rollback(self, timestamp: int) -> bool:
        """Discard the innermost transaction's changes; return False if none is open."""
        if not self.layers:
            return False
        # Dropping the layer discards its sets and deletes. Nothing from it ever reached the
        # base or the history, so there is nothing else to undo.
        self.layers.pop()
        return True

    # -- Level 4 ------------------------------------------------------------------------
    def get_at(self, timestamp: int, key: str, time_at: int) -> str | None:
        """Return the key's value in permanent storage right after all operations at time_at."""
        entries = self.history.get(key, [])
        # bisect_right returns the position after the last entry with ts <= time_at, so
        # entries[index - 1] is the latest change at or before time_at. Index 0 means nothing
        # had happened to this key yet, so None. A recorded deletion is also None.
        index = bisect_right(entries, time_at, key=itemgetter(0))
        return entries[index - 1][1] if index else None
