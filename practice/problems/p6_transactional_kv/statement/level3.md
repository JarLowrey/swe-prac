- `begin(timestamp) -> None` opens a transaction. Transactions can nest.
- `commit(timestamp) -> bool` merges the innermost transaction's changes into its parent (or into permanent storage if it is the outermost) and returns `True`. Returns `False` if no transaction is open.
- `rollback(timestamp) -> bool` discards the innermost transaction's changes and returns `True`. Returns `False` if no transaction is open.

While a transaction is open, `set` and `delete` make their changes in the innermost transaction.

Changed behaviour: every Level 1 and 2 method sees the innermost view: permanent storage plus all open transactions' changes, inner layers winning.
