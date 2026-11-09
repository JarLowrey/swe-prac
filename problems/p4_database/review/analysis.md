Build a nested key → field → value store. The crux is Level 4: a restore must preserve each field's remaining lifetime, not its original expiry time.

## Approach

Every field stores an absolute `expires_at` (`math.inf` when there's no TTL), and every read goes through one `_live(ts, key)` filter. Backups store remaining lifetime, which turns the hard restore rule into one subtraction and one addition.

**Data model.** `data: dict[key, dict[field, Field(value, expires_at)]]` and `backups: list[(ts, {key: {field: (value, remaining)}})]`.

## How the crux is handled

- `_live(ts, key)` returns only fields with `ts < expires_at`. `get`, `delete` and both scans use it, so expired fields are invisible everywhere at once, and nothing is ever eagerly purged.
- `set` creates a fresh `Field(value)` with infinite expiry, which is exactly "a plain set clears the TTL".
- `backup` saves `expires_at - backup_ts`. `restore` sets `expires_at = restore_ts + remaining`. `inf - ts` stays `inf`, so there is no special case for fields without a TTL.
- Expired fields are dropped at backup time, and keys left with no live fields aren't saved, which is what makes `backup` return the right count.
- Restore builds new `Field` objects from immutable tuples, so the stored backup can never be mutated by later writes. That gives deepcopy safety without calling `deepcopy`.
- The right backup is `bisect_right(backups, t, key=…) - 1`: the latest one at or before `t`.

## Complexity

`get`, `set` and `delete` are O(fields in key). Scans are O(k log k). `backup` and `restore` are O(total fields). Backup lookup is O(log B).

## Common mistakes

- Saving absolute `expires_at` in the backup. Restoring at a much later time then resurrects fields that are instantly expired.
- Purging expired fields in some methods but not others, so `scan` and `get` disagree.
- `ts <= expires_at` as the alive check.
- Restoring by reference (`self.data = snapshot`), so the next write corrupts the backup.
- Counting keys whose fields have all expired in `backup`'s return value.

## Key snippet

```python
def backup(self, ts):
    snapshot = {}
    for key in self.data:
        live = self._live(ts, key)
        if live:
            snapshot[key] = {name: (f.value, f.expires_at - ts) for name, f in live.items()}
    self.backups.append((ts, snapshot))
    return len(snapshot)

def restore(self, ts, timestamp_to_restore):
    i = bisect_right(self.backups, timestamp_to_restore, key=lambda b: b[0]) - 1
    _, snapshot = self.backups[i]
    self.data = {key: {name: Field(v, ts + rem) for name, (v, rem) in fields.items()}
                 for key, fields in snapshot.items()}
```

**Remember:** filter reads through one alive check, store remaining lifetime in snapshots, and rebuild objects on restore.
