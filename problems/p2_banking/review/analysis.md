This is one of the most common problems in this format. Level 3 adds time-triggered events and Level 4
asks for historical balances, so how you store state over time decides how painful the last hour is.

## Approach

The solution separates an account's public id from the account object, and gives every object an
append-only balance history. Scheduled payments live in a heap and run lazily at the top of every
method.

**Data model.**

- `accounts: dict[id, Account]` holds live accounts.
- `incarnations: dict[id, list[Account]]` holds every account that ever used an id, so a re-created
  id gets a fresh object and the old history survives.
- Each `Account` has `created_at`, `deleted_at`, `balance`, `outgoing` and
  `history: list[(ts, balance)]`.
- Payments are `@dataclass(order=True)` objects ordered by `(due, seq)`, with the rest of their
  fields marked `compare=False`.

## How the crux is handled

- `_advance(ts)` pops every payment due at or before `ts`, in `(due, seq)` order. It logs the
  balance change at `p.due`, not at `ts`. That one argument is what makes `get_balance(…, 16)`
  return 140 rather than missing the payment at 15.
- Cancellation is lazy: set `status = "cancelled"` and skip it when popped. A `payments` dict gives
  O(1) lookup by id.
- A payment points at an `Account` object, not an id string. Merging re-points pending payments to
  the target object, so `cancel_payment` with the source id fails naturally (`p.account is not acc`).
- `get_balance` walks the id's incarnations newest first, picks the one alive at `time_at`
  (`created_at <= time_at < deleted_at`), then does `bisect_right(...) - 1` on its history.
  `bisect_right` returns the state after all operations at `time_at`.
- Two changes at the same timestamp both get logged. `bisect_right` lands on the later one, which is
  the correct end-of-timestamp state.

## Complexity

Deposits and transfers are O(1) amortized plus heap work: each payment is pushed and popped once,
O(log P). `top_spenders` is O(A log A). `merge_accounts` scans payments, O(P). `get_balance` is
O(log H).

## Common mistakes

- Logging the executed payment at the current call's `ts`. History tests at timestamps between the
  due time and the next call then fail.
- Forgetting `_advance` in read-only methods like `top_spenders` or `get_balance`, so due payments
  aren't counted yet.
- Removing cancelled payments from the heap directly. It's O(P), and it breaks the heap invariant if
  done with `list.remove`.
- Keying history by public id. A re-created account then inherits the deleted account's balances.
- Counting a skipped payment as outgoing.

## Key snippet

The time engine, called first in every public method:

```python
def _advance(self, ts):
    while self.queue and self.queue[0].due <= ts:
        p = heapq.heappop(self.queue)
        if p.status != "pending":
            continue                      # cancelled: lazy deletion
        if p.account.balance >= p.amount:
            self._set_balance(p.account, p.due, p.account.balance - p.amount)  # at DUE time
            p.account.outgoing += p.amount
            p.status = "done"
        else:
            p.status = "skipped"
```

**Remember:** `_advance` on every method including reads, log effects at the due time, and separate
account objects from their public ids.
