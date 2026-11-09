- `set_with_ttl(timestamp, key, field, value, ttl) -> None` sets a field that is alive while `timestamp < set_at + ttl`, where `set_at` is the timestamp of this call.

Changed behaviour: expired fields are invisible everywhere. `get` returns `None`, scans skip them, and `delete` returns `False`.

A plain `set` on a field clears any TTL, so the field never expires. A `set_with_ttl` on an existing field replaces both value and TTL.
