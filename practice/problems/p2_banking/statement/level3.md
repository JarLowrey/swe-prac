- `schedule_payment(timestamp, account_id, amount, delay) -> str | None` schedules a withdrawal of
  `amount` from the account to run at `timestamp + delay`. Returns a payment id `"payment1"`,
  `"payment2"`, ... from a single global counter, or `None` if the account doesn't exist.
- `cancel_payment(timestamp, account_id, payment_id) -> bool` cancels a pending payment. Returns
  `False` if the payment doesn't exist, already ran, was cancelled, or belongs to a different account.

Before processing any operation at timestamp `t`, execute every pending payment due at or before
`t`, in order of due time, then creation order. A payment that would overdraw is skipped (not
retried) and does not count as outgoing.

Changed behaviour: the totals in `top_spenders` now count outgoing money from successful transfers
sent **and** executed scheduled payments.
