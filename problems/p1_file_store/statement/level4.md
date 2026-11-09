- `backup_user(timestamp, user_id) -> int | None` snapshots the user's current files (names and sizes), replacing any earlier backup. Returns the number of files saved, or `None` if the user doesn't exist.
- `restore_user(timestamp, user_id) -> int | None` deletes all of the user's current files, then re-creates the files from their latest backup. Returns the number of files restored, or `None` if the user doesn't exist.

A backed-up file whose name is now owned by a different user is skipped and doesn't count. If the user has no backup, restore just deletes their files and returns `0`.

A user's capacity is never changed by restore. A merge does not carry the source user's backup over; the target keeps its own.
