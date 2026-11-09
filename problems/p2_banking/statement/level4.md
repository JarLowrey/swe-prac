- `merge_accounts(timestamp, target_id, source_id) -> bool` moves the source's balance, outgoing
  total, and pending scheduled payments to the target, then deletes the source. Returns `False` if
  either account is missing or they are the same. A moved payment can now only be cancelled with
  `target_id`.
- `get_balance(timestamp, account_id, time_at) -> int | None` returns the account's balance right
  after all operations at `time_at` were processed. Returns `None` if the account did not exist at
  `time_at`.

After a merge, `get_balance` for the source returns `None` for any `time_at` at or after the merge,
and its old balances for earlier times. The target's earlier balances are unchanged by the merge.

Once deleted by a merge, a source id may be re-created with `create_account` as a brand-new account
with fresh history.
