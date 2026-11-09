- `top_n_workers(timestamp, n, position) -> str` lists the top `n` workers (or all of them, if
  fewer) whose current position is `position`, ranked by time spent in completed sessions while
  holding that position, formatted `"w1(20), w2(10)"`.
  - Sort by time descending, then id ascending.
  - Include workers with 0.
  - Returns `""` if none hold the position.
