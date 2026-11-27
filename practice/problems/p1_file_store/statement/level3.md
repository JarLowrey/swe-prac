- `add_user(timestamp, user_id, capacity) -> bool` creates a user with a byte capacity. Returns `False` if the user exists.
- `add_file_by(timestamp, user_id, name, size) -> int | None` adds a file owned by that user and returns their remaining capacity. Returns `None` if the user doesn't exist, the name is taken, or the file would exceed capacity.
- `merge_user(timestamp, target_id, source_id) -> int | None` moves all of `source_id`'s files to `target_id`, adds the source's capacity to the target, deletes the source user, and returns the target's remaining capacity. Returns `None` if either user is missing or they are the same user.

Files created with Level 1 `add_file` belong to a built-in `"admin"` user with unlimited capacity.

Changed behaviour: `delete_file` must free capacity for the file's owner.
