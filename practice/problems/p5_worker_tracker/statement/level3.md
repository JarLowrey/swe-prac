- `promote(timestamp, worker_id, new_position, new_compensation, start_timestamp) -> str` schedules
  a promotion to `new_position`, paid `new_compensation`. It takes effect at the worker's first
  entry at or after `start_timestamp`, never in the middle of a session. Returns `"success"`, or
  `"invalid_request"` if the worker doesn't exist or already has a promotion that hasn't taken
  effect.
- `calc_salary(timestamp, worker_id, start_ts, end_ts) -> int | None` returns pay for the parts of
  completed sessions that fall inside `[start_ts, end_ts)`, each at the compensation in effect for
  that session. Returns `None` for a missing worker.

Changed behaviour: after a promotion, `top_n_workers` for the new position counts only time spent
in sessions held under that position.
