Build an in-memory key-value store. Keys and values are strings.

- `set(timestamp, key, value) -> None` sets or overwrites a key.
- `get(timestamp, key) -> str | None` returns the value, or `None` if the key is missing.
- `delete(timestamp, key) -> bool` removes the key and returns `True`. Returns `False` if it doesn't exist.
