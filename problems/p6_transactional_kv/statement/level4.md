- `get_at(timestamp, key, time_at) -> str | None` returns the key's value in permanent storage right after all operations at `time_at`, or `None` if it had no value then. Open transactions are ignored.

A change made outside any transaction is recorded at its own timestamp. A change made inside transactions is recorded at the timestamp of the outermost `commit` that writes it to permanent storage. Rolled-back changes never appear.
