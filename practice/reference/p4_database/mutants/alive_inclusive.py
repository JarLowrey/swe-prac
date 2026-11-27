"""MUTANT: off-by-one alive check `timestamp <= expires_at`: a field is still visible at its expiry timestamp (and saved by a backup taken exactly then)."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

# A backup maps key -> field -> (value, remaining lifetime at backup time).
Snapshot = dict[str, dict[str, tuple[str, float]]]


@dataclass
class Field:
    value: str
    expires_at: float = math.inf  # the field is alive while timestamp < expires_at


class InMemoryDB:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, Field]] = {}
        self.backups: list[tuple[int, Snapshot]] = []

    # -- helpers ------------------------------------------------------------------------
    def _live(self, timestamp: int, key: str) -> dict[str, Field]:
        """The one liveness filter: every read goes through it, nothing is purged eagerly."""
        fields = self.data.get(key, {})
        return {name: f for name, f in fields.items() if timestamp <= f.expires_at}

    def _format(self, fields: dict[str, Field]) -> str:
        return ", ".join(f"{name}({fields[name].value})" for name in sorted(fields))

    # -- Level 1 ------------------------------------------------------------------------
    def set(self, timestamp: int, key: str, field: str, value: str) -> None:
        """Set the field, creating the key if needed and overwriting any existing value."""
        self.data.setdefault(key, {})[field] = Field(value)

    def get(self, timestamp: int, key: str, field: str) -> str | None:
        """Return the field's value, or None if the key or field doesn't exist."""
        found = self._live(timestamp, key).get(field)
        return found.value if found else None

    def delete(self, timestamp: int, key: str, field: str) -> bool:
        """Remove the field; return False if it doesn't exist."""
        if field not in self._live(timestamp, key):
            return False
        fields = self.data[key]
        del fields[field]
        if not fields:
            del self.data[key]
        return True

    # -- Level 2 ------------------------------------------------------------------------
    def scan(self, timestamp: int, key: str) -> str:
        """Return the key's fields as "field1(value1), field2(value2)", sorted by field name."""
        return self._format(self._live(timestamp, key))

    def scan_by_prefix(self, timestamp: int, key: str, prefix: str) -> str:
        """Like scan, limited to fields whose names start with prefix."""
        live = self._live(timestamp, key)
        return self._format({name: f for name, f in live.items() if name.startswith(prefix)})

    # -- Level 3 ------------------------------------------------------------------------
    def set_with_ttl(self, timestamp: int, key: str, field: str, value: str, ttl: int) -> None:
        """Set a field that is alive while timestamp < set_at + ttl."""
        self.data.setdefault(key, {})[field] = Field(value, timestamp + ttl)

    # -- Level 4 ------------------------------------------------------------------------
    def backup(self, timestamp: int) -> int:
        """Save the whole database; return the number of keys with at least one live field."""
        snapshot: Snapshot = {}
        for key in self.data:
            live = self._live(timestamp, key)
            if live:
                snapshot[key] = {
                    name: (f.value, f.expires_at - timestamp) for name, f in live.items()
                }
        self.backups.append((timestamp, snapshot))
        return len(snapshot)

    def restore(self, timestamp: int, timestamp_to_restore: int) -> None:
        """Replace the database with the latest backup made at or before timestamp_to_restore."""
        i = bisect_right(self.backups, timestamp_to_restore, key=lambda b: b[0]) - 1
        _, snapshot = self.backups[i]
        # Fresh Field objects, so later writes can never reach into the stored backup.
        self.data = {
            key: {name: Field(value, timestamp + left) for name, (value, left) in fields.items()}
            for key, fields in snapshot.items()
        }
