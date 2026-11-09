Build a nested key → field → value store. Each key holds named fields, and each field holds a string value.

- `set(timestamp, key, field, value) -> None` sets a field, creating the key if needed and overwriting any existing value.
- `get(timestamp, key, field) -> str | None` returns the value, or `None` if the key or field doesn't exist.
- `delete(timestamp, key, field) -> bool` removes the field and returns `True`. Returns `False` if it doesn't exist.

A key with no fields left is treated as missing.
