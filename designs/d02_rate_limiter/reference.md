**Requirements.** Functional: limit requests per client (user, API key, IP) by rule, such as 100 requests per minute per key and 10 per second per IP on login; reject excess with a clear response. Non-functional: adds under 5 ms per request; works across many servers; highly available (the limiter must not become the outage); rules changeable without redeploying. Clarify first: is this a library inside services, a shared service, or a gateway feature? Assume a shared component used at the [API gateway](#/design/learn/networking/api-gateway).

**Estimates.** 1M requests/s globally at peak, 50M active keys. Per-key state for a [token bucket](#/design/learn/building-blocks/token-bucket) is about 16 bytes (count + timestamp) plus key overhead, say 100 bytes: 50M × 100 B = 5 GB, which fits in one Redis shard's memory. Throughput is the constraint: 1M checks/s needs about 10–20 Redis shards at [roughly 100K ops/s each](#/design/learn/building-blocks/estimation-and-benchmarks).

**API and behavior.** Internal: `allow(key, rule) → {allowed, remaining, reset_at}`. Client-facing: [`429 Too Many Requests` with `Retry-After`](#/design/learn/networking/rate-limiting-429-and-retry-after), plus `X-RateLimit-Limit/Remaining/Reset` headers.

**Algorithm.** Token bucket: each key has a bucket of capacity B refilling at rate R per second. On each request compute `tokens = min(B, tokens + (now − last) × R)`; if `tokens ≥ 1`, subtract one and allow. It permits short bursts up to B while enforcing the long-term rate, needs two numbers per key, and is the standard answer. Mention [sliding window counter](#/design/learn/building-blocks/sliding-window-counter) as the alternative for strict per-minute quotas.

**High-level design.**

1. Request hits the API gateway.
2. The gateway extracts the key (API key, user ID, or IP) and loads the matching rule from a locally cached rules table (rules live in a config store, pushed to gateways).
3. The gateway runs an [atomic check-and-decrement](#/design/learn/data/atomic-updates-and-counters) in Redis ([a Lua script](#/design/learn/building-blocks/distributed-rate-limiting-with-redis) performing the token bucket math in one round trip).
4. Allowed requests proceed to the backend; rejected ones get `429` immediately.

```mermaid
flowchart TD
  C((Client)) --> G[API gateway<br/>extract key, match rule]
  RS[(Rules store)] -.->|"pushed, cached locally"| G
  G <-->|"one Lua call:<br/>refill, take a token"| R[(Redis cluster<br/>sharded by key)]
  G -->|allowed| B[Backend services]
  G -.->|"429, Retry-After"| C
```

Redis is sharded by key ([consistent hashing](#/design/learn/building-blocks/consistent-hashing) or hash slots), so each key lives on one shard and the Lua script makes the read-modify-write atomic, avoiding [the classic race](#/design/learn/data/check-then-act-races) where two gateways both read "one token left."

```mermaid
sequenceDiagram
  participant G1 as Gateway 1
  participant R as Redis shard
  participant G2 as Gateway 2
  Note over R: key 42 has<br/>1 token left
  G1->>R: run token_bucket(key 42)
  G2->>R: run token_bucket(key 42)
  Note over R: scripts run<br/>one at a time
  R-->>G1: allowed, 0 left
  R-->>G2: denied, refill in 600 ms
  Note over G2: replies 429<br/>Retry-After: 1
```

**Deep dives.**

1. **Latency and [hot keys](#/design/learn/data/hot-keys).** One Redis hop adds about 1 ms. A single abusive key can saturate its shard; mitigate with a small local in-memory pre-limiter on each gateway (cheap rejection of obvious floods) and per-IP limits at the edge before the call even reaches Redis.
2. **Distributed accuracy vs cost.** Exact global counting needs a central store on every request. An approximation keeps a local token budget per gateway and syncs periodically with the central count, which cuts Redis load by 10x or more at the cost of brief overshoot (up to roughly the number of gateways × local burst). State which accuracy the product needs: billing quotas want exact; abuse protection tolerates approximate.
3. **Failure behavior.** If Redis is unreachable, [fail **open**](#/design/learn/building-blocks/fail-open-or-fail-closed) for ordinary API traffic (log and alert, fall back to the local limiter) but fail **closed** for security-critical limits such as login attempts. Replicate shards ([leader + replica](#/design/learn/data/single-leader-replication)) so a failover loses at most a few seconds of counts.
4. **Multiple rule dimensions.** Check several limits per request (per user, per IP, per endpoint) in a single Lua call, rejecting if any fails. Tier plans (free vs paid) are rules keyed by the customer's plan.
5. **Rules management.** Rules stored in a database, cached at gateways with a TTL or pushed via config service; changes are [canaried like code](#/design/learn/reliability/rollout-strategies) (bad limits cause outages).

**The design after the deep dives.** Green marks what they added or changed.

```mermaid
flowchart TD
  C((Client)) --> E[Edge<br/>coarse per-IP limits]:::good
  E --> G
  subgraph GW [Each gateway]
    G[Match rules<br/>user, IP, endpoint] --> L[Local pre-limiter<br/>budget and fallback]:::good
  end
  RS[(Rules store)] -.->|"pushed, canaried"| G
  L <-->|"batched syncs, or every<br/>call for exact quotas"| R[(Redis cluster)]
  R -.->|replication| RP[(Replica per shard)]:::good
  L -->|allowed| B[Backend services]
  L -.->|"counts, drift, top keys"| M[Metrics]:::good
```

**Wrap-up.** Observability: allowed/rejected counts per rule, Redis latency, local-vs-central drift, top rejected keys. Extensions: concurrency limits (in-flight requests), quotas with durable daily/monthly counters, and adaptive limits that tighten when the backend is stressed ([load shedding](#/design/learn/reliability/load-shedding)).
