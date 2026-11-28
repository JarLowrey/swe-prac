**Requirements.** Create and read pastes.

**Diagram.**

```mermaid
flowchart TD
  U((User)) --> API[Paste service]
  API --> DB[(Pastes)]
```

**Deep dives.** Cache hot pastes.
