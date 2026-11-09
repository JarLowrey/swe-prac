Build a key-value store with nested transactions. The crux is Level 3's deletes: a delete inside a transaction must hide a value that still exists in an outer layer. Level 4 adds a second trap: changes reach permanent storage at commit time, not when they were made.

## Approach

Open transactions are a stack of dicts on top of the permanent dict. A read walks the stack from the top down; a delete inside a transaction writes a tombstone sentinel. All writes go through one `_write` helper that decides between "current layer" and "permanent storage plus history".

**Data model.** `base: dict[key, value]`, `layers: list[dict[key, value | TOMBSTONE]]`, and `history: dict[key, list[(ts, value | None)]]` for permanent changes only.

This uses two of the patterns every problem in the set shares:

- **Mutation helpers.** `_write` and `_apply_to_base` are the only code that changes the layers or permanent storage.
- **Append-only history + `bisect_right`.** Log `(ts, value)` on every permanent change, then look up the last entry at or before `t` in `get_at`.

## How the crux is handled

- The tombstone is `_TOMBSTONE = object()`, a value nothing else can equal. In a layer, a missing key means "ask the layer below"; a tombstone means "deleted, stop looking". That distinction is the whole Level 3 crux.
- `count` and `list_keys` are built from one `_view()` that applies layers bottom up and drops tombstones, so they can never disagree with `get`.
- Inner `commit` is just `layers[-1].update(top)`. Tombstones carry down like any value. Only the outermost commit touches `base`.
- History is written only in `_apply_to_base`, with the timestamp passed in. Direct writes pass their own `ts`; the outermost commit passes the commit `ts`. Rolled-back changes never reach it.
- `get_at` reads `self.history.get(key, [])`, not `self.history[key]`, so lookups of unknown keys don't add empty entries to the `defaultdict`.

## Complexity

`get` is O(depth). `set`, `delete`, `begin`, `rollback` are O(1). `count`, `list_keys` and commits are O(total keys in play). `get_at` is O(log H).

O(n) per call is the right call here: inputs are small, and a linear scan has nothing to keep in sync.

## Common mistakes

- Deleting from the top layer with `del` or `pop` instead of writing a tombstone. The outer value then shows through.
- Committing inner transactions straight to `base`, which makes a later outer rollback impossible.
- Recording history when the change is made instead of when it reaches permanent storage.
- `delete` returning `True` for a key that's missing in the merged view but present in a lower layer as a tombstone. Checking `_get(key) is None` handles it.
- Using `None` as the tombstone, then confusing it with "key not present".

## Key snippet

```python
def _get(self, key):
    for layer in reversed(self.layers):
        if key in layer:
            v = layer[key]
            return None if v is _TOMBSTONE else v
    return self.base.get(key)

def commit(self, ts):
    if not self.layers:
        return False
    top = self.layers.pop()
    if self.layers:
        self.layers[-1].update(top)               # inner: merge down, tombstones included
    else:
        for key, v in top.items():                # outermost: permanent, logged at commit ts
            self._apply_to_base(ts, key, None if v is _TOMBSTONE else v)
    return True
```

**Remember:** "absent" and "deleted" are different states, derive every query from one merged view, and timestamp changes when they become permanent.
