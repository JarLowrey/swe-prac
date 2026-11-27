"""Random operation sequences for p1_file_store (see reference/AUTHORING.md)."""

from __future__ import annotations

import random

L1_NAMES = ["/a", "/b", "/c", "/a/x"]
NAMES = ["/a", "/b", "/c", "/a/x", "/a/y", "/b/z"]
PREFIXES = ["", "/", "/a", "/a/", "/b", "/c", "/q"]
L3_USERS = ["u1", "u2", "u3", "u4"]
MISSING = "ghost"  # never created

WEIGHTS = {
    1: {"add_file": 45, "get_file_size": 25, "delete_file": 30},
    2: {"add_file": 40, "get_file_size": 10, "delete_file": 22, "get_n_largest": 28},
    3: {"add_file": 10, "get_file_size": 8, "delete_file": 14, "get_n_largest": 8,
        "add_user": 14, "add_file_by": 36, "merge_user": 10},
    4: {"add_file": 6, "get_file_size": 5, "delete_file": 11, "get_n_largest": 5,
        "add_user": 9, "add_file_by": 30, "merge_user": 6, "backup_user": 14,
        "restore_user": 14},
}
# Multiples of 5 so that files often fill a user's capacity exactly.
CAPACITIES = [10, 20, 30, 40, 50]
USER_FILE_SIZES = [5, 10, 15, 20]


class _Users:
    """Tracks which user ids exist, so Level 4 never re-creates a merged-away id.

    Re-creating a merged-away id is well defined at Level 3, but at Level 4 the spec does not
    say whether the new user inherits the old user's backup, so the generator avoids it there.
    """

    def __init__(self, level: int, rng: random.Random) -> None:
        self.level = level
        self.rng = rng
        self.alive: set[str] = set()
        self.dead: set[str] = set()  # merged away
        self.pool = L3_USERS if level == 3 else [f"u{i}" for i in range(1, 200)]

    def _window(self) -> list[str]:
        if self.level == 3:
            return self.pool
        return [u for u in self.pool if u not in self.dead][:4]

    def for_add(self) -> str:
        return self.rng.choice(self._window())

    def any(self) -> str:
        roll = self.rng.random()
        if roll < 0.04:
            return MISSING
        if roll < 0.12 and self.dead:
            return self.rng.choice(sorted(self.dead))
        return self.rng.choice(self._window())

    def added(self, user: str) -> None:
        self.alive.add(user)
        self.dead.discard(user)

    def merged(self, target: str, source: str) -> None:
        if target != source and target in self.alive and source in self.alive:
            self.alive.remove(source)
            self.dead.add(source)


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    names = L1_NAMES if level == 1 else NAMES
    max_size = 30 if level == 1 else 8  # small sizes from Level 2 on, so get_n_largest sees ties
    weights = WEIGHTS[level]
    ops, op_weights = list(weights), list(weights.values())
    users = _Users(level, rng)
    lines: list[str] = []
    ts = 0
    for _ in range(n):
        ts += rng.randint(1, 3)
        op = rng.choices(ops, op_weights)[0]
        if op == "add_file":
            lines.append(f"add_file({ts}, {rng.choice(names)!r}, {rng.randint(1, max_size)})")
        elif op in ("get_file_size", "delete_file"):
            lines.append(f"{op}({ts}, {rng.choice(names)!r})")
        elif op == "get_n_largest":
            lines.append(f"get_n_largest({ts}, {rng.choice(PREFIXES)!r}, {rng.randint(1, 5)})")
        elif op == "add_user":
            user = users.for_add()
            users.added(user)
            lines.append(f"add_user({ts}, {user!r}, {rng.choice(CAPACITIES)})")
        elif op == "add_file_by":
            user, name, size = users.any(), rng.choice(names), rng.choice(USER_FILE_SIZES)
            lines.append(f"add_file_by({ts}, {user!r}, {name!r}, {size})")
        elif op == "merge_user":
            target, source = users.any(), users.any()
            users.merged(target, source)
            lines.append(f"merge_user({ts}, {target!r}, {source!r})")
        else:  # backup_user / restore_user
            lines.append(f"{op}({ts}, {users.any()!r})")
    return lines
