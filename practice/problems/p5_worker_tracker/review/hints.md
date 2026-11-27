- Store each completed session as `(start, end, position, compensation)`, copied from the worker at
  entry time. Promotions then never need to rewrite history.
- On entry, apply the pending promotion first if `timestamp >= start_timestamp`, then open the
  session with the updated values.
- Salary over a window is a sum of clipped overlaps:
  `max(0, min(end, end_ts) - max(start, start_ts))`.
- For double time, merge the periods into non-overlapping intervals (sort by start, combine
  overlapping ones), then add one extra overlap per merged interval.
