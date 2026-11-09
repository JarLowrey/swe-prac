- Call one `_process_due_payments(timestamp)` helper as the first line of every public method.
  Keep pending payments sorted by `(due, seq)`, for example in a `heapq`.
- Record an append-only `(timestamp, balance)` history on every balance change, including executed
  payments at their **due** time. `get_balance` is then a binary search (`bisect_right`) for the
  last entry `<= time_at`.
- Give each account an internal object separate from its public id, with `created_at` and
  `deleted_at`. Re-creation after a merge then can't corrupt the old history.
