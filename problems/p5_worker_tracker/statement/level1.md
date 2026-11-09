Track employees clocking in and out of an office. All time ranges here are half-open:
`[start, end)`, so a worker who enters at 3 and leaves at 10 has a 7-unit session.

- `add_worker(timestamp, worker_id, position, compensation) -> bool` adds a worker holding
  `position`, paid `compensation` per time unit. Returns `False` if the worker exists.
- `register(timestamp, worker_id) -> str` alternates between entering and leaving the office: the
  first call enters, the next leaves, and so on. Returns `"registered"`, or `"invalid_request"` if
  the worker doesn't exist.
- `get(timestamp, worker_id) -> int | None` returns the total time across completed sessions (a
  session still open counts as 0). Returns `None` for a missing worker.
