- `backup(timestamp) -> int` saves the whole database and returns the number of keys that have at least one live field.
- `restore(timestamp, timestamp_to_restore) -> None` replaces the database with the latest backup made at or before `timestamp_to_restore`. One is guaranteed to exist.

A restored field with a TTL keeps the remaining lifetime it had at backup time: its new expiry is `timestamp + (expires_at - backup_ts)`, where `timestamp` is the restore call's timestamp and `backup_ts` is the backup's. Fields expired at backup time are not saved.

Backups stay available after a restore, so a later restore can still use any of them.
