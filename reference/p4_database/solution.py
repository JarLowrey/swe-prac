"""Reference solution for Problem 4: In-memory database."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

# Design in brief
# ---------------
# - data[key][field] -> Field(value, expires_at). Expiry is stored as an absolute time, with
#   math.inf meaning "no TTL". Nothing is ever purged: an expired field stays in the dict and
#   is simply ignored by _live. One liveness rule, used by every read, means reads and backups
#   can never disagree about what exists.
# - A backup stores each field's REMAINING lifetime instead of its absolute expiry. Restoring
#   then restarts that remaining time from the restore moment, as the problem requires.

# A backup maps key -> field -> (value, remaining lifetime at backup time).
# The lifetime is a float because math.inf - timestamp is still math.inf: fields without a TTL
# stay without a TTL through a backup and a restore.
Snapshot = dict[str, dict[str, tuple[str, float]]]


@dataclass
class Field:
    value: str
    # The field is alive while timestamp < expires_at. A field set at 10 with ttl 5 has
    # expires_at 15, so it is alive at 14 and gone at 15.
    expires_at: float = math.inf


class InMemoryDB:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, Field]] = {}
        # (timestamp, snapshot) in call order. Timestamps strictly increase, so this list is
        # already sorted by time and can be searched with bisect. Restores never remove backups.
        self.backups: list[tuple[int, Snapshot]] = []

    # -- helpers ------------------------------------------------------------------------
    def _live(self, timestamp: int, key: str) -> dict[str, Field]:
        """The one liveness filter: every read goes through it, nothing is purged eagerly."""
        fields = self.data.get(key, {})
        # A filtered copy: callers can loop over it freely, but to change data they must go
        # through self.data.
        return {name: f for name, f in fields.items() if timestamp < f.expires_at}

    def _format(self, fields: dict[str, Field]) -> str:
        # "name(value), ..." sorted by field name. An empty dict joins to "".
        return ", ".join(f"{name}({fields[name].value})" for name in sorted(fields))

    # -- Level 1 ------------------------------------------------------------------------
    def set(self, timestamp: int, key: str, field: str, value: str) -> None:
        """Set the field, creating the key if needed and overwriting any existing value."""
        # A brand-new Field replaces the old one completely, so a plain set also clears any
        # earlier TTL: the new Field has expires_at = math.inf.
        self.data.setdefault(key, {})[field] = Field(value)

    def get(self, timestamp: int, key: str, field: str) -> str | None:
        """Return the field's value, or None if the key or field doesn't exist."""
        # An expired field is just absent from _live, so it reads as missing.
        found = self._live(timestamp, key).get(field)
        return found.value if found else None

    def delete(self, timestamp: int, key: str, field: str) -> bool:
        """Remove the field; return False if it doesn't exist."""
        # Test against _live, not self.data: an expired field already counts as gone.
        if field not in self._live(timestamp, key):
            return False
        fields = self.data[key]
        del fields[field]
        if not fields:  # drop the key with its last field, so empty keys don't pile up
            del self.data[key]
        return True

    # -- Level 2 ------------------------------------------------------------------------
    def scan(self, timestamp: int, key: str) -> str:
        """Return the key's fields as "field1(value1), field2(value2)", sorted by field name."""
        return self._format(self._live(timestamp, key))

    def scan_by_prefix(self, timestamp: int, key: str, prefix: str) -> str:
        """Like scan, limited to fields whose names start with prefix."""
        live = self._live(timestamp, key)  # filter for liveness first, then for the prefix
        return self._format({name: f for name, f in live.items() if name.startswith(prefix)})

    # -- Level 3 ------------------------------------------------------------------------
    def set_with_ttl(self, timestamp: int, key: str, field: str, value: str, ttl: int) -> None:
        """Set a field that is alive while timestamp < set_at + ttl."""
        # Same as set, plus an absolute expiry. Nothing else in the class needs to change:
        # _live already honours expires_at everywhere.
        self.data.setdefault(key, {})[field] = Field(value, timestamp + ttl)

    # -- Level 4 ------------------------------------------------------------------------
    def backup(self, timestamp: int) -> int:
        """Save the whole database; return the number of keys with at least one live field."""
        snapshot: Snapshot = {}
        for key in self.data:
            live = self._live(timestamp, key)
            # Keys whose fields have all expired are neither saved nor counted.
            if live:
                # Remaining lifetime = expires_at - now. Plain tuples, not Field objects, so
                # nothing in a snapshot can be changed by later writes to the live database.
                snapshot[key] = {
                    name: (f.value, f.expires_at - timestamp) for name, f in live.items()
                }
        self.backups.append((timestamp, snapshot))
        return len(snapshot)

    def restore(self, timestamp: int, timestamp_to_restore: int) -> None:
        """Replace the database with the latest backup made at or before timestamp_to_restore."""
        # bisect_right gives the position after the last backup with ts <= timestamp_to_restore,
        # so the one before it is the latest such backup. The problem guarantees one exists.
        i = bisect_right(self.backups, timestamp_to_restore, key=lambda b: b[0]) - 1
        _, snapshot = self.backups[i]
        # Fresh Field objects, so later writes can never reach into the stored backup.
        # Each field's expiry is rebuilt from the RESTORE call's timestamp plus the remaining
        # lifetime it had at backup time. Everything written since the backup is replaced.
        self.data = {
            key: {name: Field(value, timestamp + left) for name, (value, left) in fields.items()}
            for key, fields in snapshot.items()
        }
