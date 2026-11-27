Build a simplified cloud file store. Files are identified by their name and have a size.

- `add_file(timestamp, name, size) -> bool` adds a file. Returns `False` if a file with that name already exists.
- `get_file_size(timestamp, name) -> int | None` returns the size, or `None` if the file doesn't exist.
- `delete_file(timestamp, name) -> int | None` deletes the file and returns its size, or `None` if it doesn't exist.
