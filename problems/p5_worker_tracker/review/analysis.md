The crux is that pay and rankings depend on what was true during each session, so sessions must
remember the position and rate they started with. All time ranges here are half-open:
`[start_ts, end_ts)`.

Each completed session is frozen as `(start, end, position, comp)`, copied from the worker at the
moment they entered. After that, promotions, rankings and pay never need to ask "what was true back
then?": the session already says.

## Data model

`workers: dict[id, Worker(position, comp, open_since, pending, sessions)]` and a global
`double_periods: list[(start, end)]`.

## How the crux is handled

- `register` toggles on `open_since is None`. On entry, it first applies a pending promotion if
  `ts >= start_timestamp`, then opens the session. A promotion can never land mid-session because
  it is only checked on entry.
- `pending` holds at most one promotion; `promote` rejects a second until the first is applied.
- `top_n_workers` filters workers by current position, then sums only sessions whose frozen
  `position` matches. That is exactly "time spent while holding that position".
- Salary is a sum of clipped overlaps: `max(start, start_ts)` to `min(end, end_ts)` per session,
  times that session's frozen rate.
- Double time merges overlapping periods first (sort by start, extend the last one when they
  touch), so time covered twice still pays double, not triple. The bonus is then one more overlap
  sum per merged interval.

## Complexity

`register` is O(1). `get` and `top_n_workers` are O(sessions). `calc_salary` is
O(S × D + D log D) for S sessions and D double periods.

## Common mistakes

- Applying a promotion at `start_timestamp` itself, or at exit, instead of at the next entry.
- Computing salary with the worker's current rate, which misprices every session before a
  promotion.
- Counting an open session in `get`.
- Summing raw double-time overlaps without merging, which pays 3× where periods overlap.
- Using inclusive range ends, which double-counts a unit at every boundary.

## Key snippet

```python
def register(self, ts, worker_id):
    w = self.workers.get(worker_id)
    if w is None:
        return "invalid_request"
    if w.open_since is None:                    # entering
        if w.pending and ts >= w.pending[2]:
            w.position, w.comp, _ = w.pending
            w.pending = None
        w.open_since = ts
    else:                                       # leaving: freeze what was true
        w.sessions.append(Session(w.open_since, ts, w.position, w.comp))
        w.open_since = None
    return "registered"
```

Remember: snapshot the facts into each event when it happens, clip intervals to the query window,
and merge overlapping periods before summing.
