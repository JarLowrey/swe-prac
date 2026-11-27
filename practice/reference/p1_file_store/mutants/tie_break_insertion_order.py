"""Mutant: get_n_largest sorts by size only, so equal sizes keep insertion order instead of name order."""

from __future__ import annotations

import math
from dataclasses import dataclass

ADMIN = "admin"


@dataclass
class File:
    size: int
    owner: str


@dataclass
class User:
    capacity: float  # math.inf for admin
    used: int = 0


class FileStore:
    def __init__(self) -> None:
        self.files: dict[str, File] = {}
        self.users: dict[str, User] = {ADMIN: User(math.inf)}
        self.backups: dict[str, list[tuple[str, int]]] = {}

    # -- helpers: every file add and delete goes through _add / _remove, so `used` can't drift --
    def _add(self, name: str, size: int, owner: str) -> bool:
        user = self.users[owner]
        if name in self.files or user.used + size > user.capacity:
            return False
        self.files[name] = File(size, owner)
        user.used += size
        return True

    def _remove(self, name: str) -> int:
        file = self.files.pop(name)
        self.users[file.owner].used -= file.size
        return file.size

    def _owned_by(self, user_id: str) -> list[str]:
        return [name for name, file in self.files.items() if file.owner == user_id]

    def _remaining(self, user_id: str) -> int:
        user = self.users[user_id]
        return user.capacity - user.used

    # -- Level 1 ------------------------------------------------------------------------
    def add_file(self, timestamp: int, name: str, size: int) -> bool:
        """Add a file; return False if a file with that name already exists."""
        return self._add(name, size, ADMIN)

    def get_file_size(self, timestamp: int, name: str) -> int | None:
        """Return the file's size, or None if it doesn't exist."""
        file = self.files.get(name)
        return file.size if file else None

    def delete_file(self, timestamp: int, name: str) -> int | None:
        """Delete the file and return its size, or None if it doesn't exist."""
        if name not in self.files:
            return None
        return self._remove(name)

    # -- Level 2 ------------------------------------------------------------------------
    def get_n_largest(self, timestamp: int, prefix: str, n: int) -> str:
        """Return the n largest files starting with prefix as "name(size), ...", or "" if none."""
        matching = [(name, f.size) for name, f in self.files.items() if name.startswith(prefix)]
        matching.sort(key=lambda item: -item[1])
        return ", ".join(f"{name}({size})" for name, size in matching[:n])

    # -- Level 3 ------------------------------------------------------------------------
    def add_user(self, timestamp: int, user_id: str, capacity: int) -> bool:
        """Create a user with a byte capacity; return False if the user exists."""
        if user_id in self.users:
            return False
        self.users[user_id] = User(capacity)
        return True

    def add_file_by(self, timestamp: int, user_id: str, name: str, size: int) -> int | None:
        """Add a file owned by user_id and return their remaining capacity, or None."""
        if user_id not in self.users or not self._add(name, size, user_id):
            return None
        return self._remaining(user_id)

    def merge_user(self, timestamp: int, target_id: str, source_id: str) -> int | None:
        """Move source's files and capacity to target, delete source, return target's remaining."""
        if target_id == source_id or target_id not in self.users or source_id not in self.users:
            return None
        self.users[target_id].capacity += self.users[source_id].capacity
        for name in self._owned_by(source_id):
            # Always succeeds: the name was just freed and the capacity was added above.
            self._add(name, self._remove(name), target_id)
        del self.users[source_id]
        self.backups.pop(source_id, None)  # a merge doesn't carry the source's backup over
        return self._remaining(target_id)

    # -- Level 4 ------------------------------------------------------------------------
    def backup_user(self, timestamp: int, user_id: str) -> int | None:
        """Snapshot the user's files, replacing any earlier backup; return the file count."""
        if user_id not in self.users:
            return None
        self.backups[user_id] = [(name, self.files[name].size) for name in self._owned_by(user_id)]
        return len(self.backups[user_id])

    def restore_user(self, timestamp: int, user_id: str) -> int | None:
        """Replace the user's files with their latest backup; return the number restored."""
        if user_id not in self.users:
            return None
        for name in self._owned_by(user_id):
            self._remove(name)  # frees the user's own names first
        return sum(self._add(name, size, user_id) for name, size in self.backups.get(user_id, []))
