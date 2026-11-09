Build a bank that processes deposits and transfers. Each account has a string id and an integer
balance, which starts at `0` when the account is created.

- `create_account(timestamp, account_id) -> bool` creates a new account. Returns `False` if the
  account already exists.
- `deposit(timestamp, account_id, amount) -> int | None` adds `amount` to the account and returns the
  new balance, or `None` if the account doesn't exist.
- `transfer(timestamp, from_id, to_id, amount) -> int | None` moves `amount` from `from_id` to `to_id`
  and returns the sender's new balance. Returns `None` if either account is missing,
  `from_id == to_id`, or the sender has insufficient funds.
