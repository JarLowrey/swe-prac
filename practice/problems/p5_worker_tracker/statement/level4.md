- `set_double_time(timestamp, start_ts, end_ts) -> None` makes every unit of time inside
  `[start_ts, end_ts)` pay double, for all workers, past and future sessions alike.

Double-time periods may overlap. Time covered by several periods still pays exactly double, never
more.

Changed behaviour: `calc_salary` now includes the double-time bonus. `get` and `top_n_workers` are
unaffected.
