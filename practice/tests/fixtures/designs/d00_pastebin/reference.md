**Requirements.** Create and read pastes.

**High-level design.**

```mermaid
flowchart TD
  U((User)) --> API[Paste service]
  API --> DB[(Pastes)]
```

**Deep dives.** Cache hot pastes.
