- `top_spenders(timestamp, n) -> str` returns the top `n` accounts by total outgoing money
  (successful transfers sent), formatted `"acc1(total1), acc2(total2)"`.
  - Sort by total descending, then account id ascending.
  - Include accounts with zero outgoing if fewer than `n` have spent.
  - If there are fewer than `n` accounts, return all of them.
