"""Reference solution for Problem 1: In-memory file store."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Design in brief
# ---------------
# All state lives in two dicts: `files` (name -> File, with size and owner) and `users`
# (user id -> User, with capacity and bytes used). The admin is a real user with infinite
# capacity from Level 1, so a plain add_file is just "add on behalf of admin". Level 3's
# per-user capacity then needs no special cases and no rewrite of Level 1 and 2.
# Every change to the set of files goes through _add / _remove, which keep each user's `used`
# total in step with `files`. Merge and restore are then simple loops over those two helpers.

# The owner of files added with plain add_file. It has no capacity limit.
ADMIN = "admin"


@dataclass
class File:
    size: int  # in bytes
    owner: str  # a key of FileStore.users


@dataclass
class User:
    capacity: float  # math.inf for admin
    used: int = 0  # total size of this user's files; only _add / _remove change it


class FileStore:
    def __init__(self) -> None:
        # name -> File. Names are unique across ALL users, not just within one user.
        self.files: dict[str, File] = {}
        # The admin exists from the start, so there is never a "no owner" case to handle.
        self.users: dict[str, User] = {ADMIN: User(math.inf)}
        # user id -> [(name, size)]: that user's latest backup. At most one per user.
        self.backups: dict[str, list[tuple[str, int]]] = {}

    # -- helpers: every file add and delete goes through _add / _remove, so `used` can't drift --
    def _add(self, name: str, size: int, owner: str) -> bool:
        user = self.users[owner]
        # Refuse a name that is already taken or a file that would not fit. The limit is
        # inclusive: using exactly `capacity` bytes is fine, one byte more is not.
        if name in self.files or user.used + size > user.capacity:
            return False
        # Both checks passed, so only now change any state: a refusal leaves everything as it was.
        self.files[name] = File(size, owner)
        user.used += size
        return True

    def _remove(self, name: str) -> int:
        # Callers check that the file exists. Returning the size lets delete_file report it
        # and lets merge_user re-add the file under its new owner.
        file = self.files.pop(name)
        self.users[file.owner].used -= file.size
        return file.size

    def _owned_by(self, user_id: str) -> list[str]:
        # Returns a new list, so callers can add and remove files while looping over it.
        return [name for name, file in self.files.items() if file.owner == user_id]

    def _remaining(self, user_id: str) -> int:
        # Bytes the user can still add.
        user = self.users[user_id]
        return user.capacity - user.used

    # -- Level 1 ------------------------------------------------------------------------
    def add_file(self, timestamp: int, name: str, size: int) -> bool:
        """Add a file; return False if a file with that name already exists."""
        # Same code path as Level 3's add_file_by, with the owner fixed to the admin.
        return self._add(name, size, ADMIN)

    def get_file_size(self, timestamp: int, name: str) -> int | None:
        """Return the file's size, or None if it doesn't exist."""
        file = self.files.get(name)
        # A File object is always truthy, even when its size is 0, so this really tests "exists".
        return file.size if file else None

    def delete_file(self, timestamp: int, name: str) -> int | None:
        """Delete the file and return its size, or None if it doesn't exist."""
        if name not in self.files:  # check first: _remove assumes the file exists
            return None
        return self._remove(name)

    # -- Level 2 ------------------------------------------------------------------------
    def get_n_largest(self, timestamp: int, prefix: str, n: int) -> str:
        """Return the n largest files starting with prefix as "name(size), ...", or "" if none."""
        matching = [(name, f.size) for name, f in self.files.items() if name.startswith(prefix)]
        # Size descending, then name ascending. Negating the size lets one ascending sort do both.
        matching.sort(key=lambda item: (-item[1], item[0]))
        # The slice copes with n larger than the match count, and joining nothing gives "".
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
        # None covers every failure: unknown user, name already taken, or not enough capacity.
        # `and` short-circuits, so _add is never called for an unknown user.
        if user_id not in self.users or not self._add(name, size, user_id):
            return None
        return self._remaining(user_id)

    def merge_user(self, timestamp: int, target_id: str, source_id: str) -> int | None:
        """Move source's files and capacity to target, delete source, return target's remaining."""
        if target_id == source_id or target_id not in self.users or source_id not in self.users:
            return None
        # Add the capacity first, so every file below is guaranteed to fit.
        self.users[target_id].capacity += self.users[source_id].capacity
        # _owned_by returns a snapshot list, so removing files while looping over it is safe.
        for name in self._owned_by(source_id):
            # Remove and re-add, rather than just relabelling the owner, so _remove and _add
            # update BOTH users' `used` totals.
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
        # Store plain (name, size) tuples, not File objects: files deleted or added later must
        # not change the backup. Assigning replaces any earlier backup.
        self.backups[user_id] = [(name, self.files[name].size) for name in self._owned_by(user_id)]
        return len(self.backups[user_id])

    def restore_user(self, timestamp: int, user_id: str) -> int | None:
        """Replace the user's files with their latest backup; return the number restored."""
        if user_id not in self.users:
            return None
        # Two phases. First delete ALL of the user's current files: that frees their capacity,
        # and frees names that are about to come back from the backup.
        for name in self._owned_by(user_id):
            self._remove(name)  # frees the user's own names first
        # Then re-add from the backup. _add can still refuse a file, for example when another
        # user has taken its name since; True counts as 1, so sum() is the number restored.
        # With no backup this just empties the user's files and returns 0.
        return sum(self._add(name, size, user_id) for name, size in self.backups.get(user_id, []))
