The twist arrives in Levels 3 and 4: ownership and capacity, then snapshots, both of which punish a flat `dict[name, size]` design.

The whole solution rests on two decisions made at Level 1: every file records its `owner`, and `"admin"` is a real user with infinite capacity. With those, Levels 3 and 4 add methods without changing any existing ones.

## Data model

- `files: dict[name, File(size, owner)]`
- `users: dict[id, User(capacity, used)]`
- `backups: dict[user_id, list[(name, size)]]`

## How the crux is handled

- `_add` and `_remove` are the only code that touches `files` or `used`. `delete_file`, `merge_user` and `restore_user` all go through them, so capacity can't drift.
- `merge_user` re-points each file's `owner` to the target. A later `delete_file` then frees the target's capacity, which is what the Level 3 self-check test at timestamp 9 checks.
- `restore_user` deletes first, then re-adds. Deleting frees the user's own names, so `_add`'s duplicate check only rejects names owned by someone else. The skip rule needs no special code.
- Backups are lists of `(name, size)` tuples. Tuples are immutable, so the snapshot can't be corrupted by later edits and no `deepcopy` is needed.

## Complexity

Lookups and adds are O(1). `get_n_largest` is O(F log F). `merge_user`, `backup_user` and `restore_user` scan all files, O(F). At scale, an owner → names index would make those O(files owned).

O(F) per call is the right call here: inputs are small, and a linear scan has nothing to keep in sync.

## Common mistakes

- Storing files per user (`users[id].files`) and a global name set separately. Merges then have to update both, and one usually gets missed.
- Restoring before deleting, so the user's own backed-up names look taken and get skipped.
- Letting Level 1 `add_file` bypass the owner model, which breaks `delete_file` capacity accounting at Level 3.

## Key snippet

All mutations go through two helpers, and restore is just delete-then-add:

```python
def _add(self, name, size, owner) -> bool:
    user = self.users[owner]
    if name in self.files or user.used + size > user.capacity:
        return False
    self.files[name] = File(size, owner)
    user.used += size
    return True

def restore_user(self, ts, user_id):
    if user_id not in self.users:
        return None
    for name in [n for n, f in self.files.items() if f.owner == user_id]:
        self._remove(name)  # frees the user's own names first
    return sum(self._add(n, s, user_id) for n, s in self.backups.get(user_id, []))
```

**Remember:** add `owner` on day one, make admin a normal user, and let one helper own every capacity change.
