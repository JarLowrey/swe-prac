Two flavors share a core: **static places** (listings, restaurants: search by map area plus filters) and **moving objects** (drivers: find the nearest). I'll design the listing search, then show what changes for drivers.

**Requirements.** Functional: search listings by location (a city or map viewport), dates, guests, price and amenities; ranked results with pagination; listings added and edited by hosts. Non-functional: results under 300 ms; search may lag the source of truth by seconds; handles dense cities and sparse regions; high availability.

Amber marks the non-functional requirements, each beside the operation it constrains.

```mermaid
flowchart LR
  G((Guest)) --> S["Search an area by dates,<br/>guests, price, amenities"]
  G --> R["Page through<br/>ranked results"]
  H((Host)) --> E["Add and<br/>edit listings"]
  S -.- N1(["Under 300 ms,<br/>highly available"]):::warn
  S -.- N2(["Dense cities and<br/>sparse regions"]):::warn
  E -.- N3(["Shows in search<br/>within seconds"]):::warn
```

**Estimates.** 10M listings × ~2 KB of searchable fields = 20 GB of core search data, [small enough to hold in memory on every search node](#/design/learn/building-blocks/estimation-and-benchmarks), so it can be replicated; the load is the issue. 100M searches/day ≈ 1,200/s average, 5,000/s peak, which at hundreds to a few thousand queries/s per search node means several replicas. Index updates: price/availability changes and edits maybe 100/s. So: read-heavy, small data, many filters.

**API.** One read endpoint does most of the work. The app calls it every time the map moves or a filter changes, waiting about 300 ms after the map stops and cancelling the request in flight.

```text
GET /v1/search?bbox=38.69,-9.23,38.76,-9.09
      &check_in=2027-03-10&check_out=2027-03-13
      &guests=2&price_max=200&amenities=wifi,pool
      &sort=relevance&limit=20
  -> 200 {results: [ListingCard], next_cursor,
          total_estimate}
GET /v1/search?cursor=eyJxIjoi...
  -> 200 the next page of the same search
GET /v1/search/clusters?bbox=...&zoom=6&<filters>
  -> 200 {clusters: [{lat, lng, count,
                      min_price}]}
GET /v1/listings/{id}
  -> 200 Listing (every detail, for a tapped card)
```

- **Say the `bbox` order out loud:** `south,west,north,east`, in degrees. When west is greater than east, the box crosses the antimeridian and the service splits it in two (deep dive 1). A box too large to search usefully gets `400 bbox_too_large`, and the app asks for clusters instead.
- **Results are cards, not listings:** ID, title, position, one photo URL, nightly price, total for the dates and rating. That's enough for a pin and a card at about 1 KB each, so a page of 20 stays small; the full listing loads when the user taps one.
- **[Cursor pagination](#/design/learn/networking/pagination-offset-vs-cursor).** The cursor is opaque and carries the query plus a position in a ranked list kept for the session (a few minutes), so page 2 continues the same ranking even if prices change in between. A cursor replaces the other parameters; an expired one gets `400 invalid_cursor` and the app starts again at page 1.
- **`total_estimate` is approximate** ("1,000+ stays"). An exact count across every shard costs more than the page itself.
- **Validate dates and filters:** `check_out` after `check_in`, at most a year ahead, guests within limits. Unknown amenities get `400` rather than being ignored, so a typo doesn't quietly return everything.
- **Caching.** Anonymous searches with default ranking can be cached at the CDN for 30–60 s, keyed on the canonical query (deep dive 5), with `Cache-Control: public, max-age=30`. Personalized results are `private`.

**Data model.** The listing database is the source of truth. The search index holds one denormalized document per listing, built from the listing and a summary of its calendar, so a query reads one document per candidate and never joins.

```mermaid
erDiagram
  listing ||--o{ calendar : "one row per night"
  listing ||--|| search_doc : "copied into"
  calendar }o--|| search_doc : "summarized into"
  listing {
    id id PK
    id host_id
    string details "title, location, price, amenities"
  }
  calendar {
    id listing_id PK
    date night PK
    enum status
  }
  search_doc {
    id listing_id PK
    geo_point location
    list cell_ids "geohash or S2 cells"
    int price
    list amenities
    float rating
    int capacity
    bitmap free_nights "availability summary"
  }
```

**Diagram.**

1. **Source of truth:** the listing database (relational). Changes flow out through the [outbox/CDC](#/design/learn/reliability/the-outbox-pattern) to a queue.
2. **Search index:** Elasticsearch/OpenSearch (or a similar engine) holds [a denormalized document per listing](#/design/learn/reliability/read-models-and-search-indexes): location (as a geo point and as [geohash/S2 cell IDs](#/design/learn/building-blocks/geohash)), price, amenities, ratings, capacity, and a compact availability summary. Updated asynchronously by index workers; eventually consistent.
3. **Query path:** the search service turns the viewport into a geo filter (cells overlapping the bounding box, or the engine's geo-bounding-box), applies filters (price, guests, amenities) as structured filters, then ranks the candidates and returns a page.
4. **Availability:** the hard part. Dates change the result set per query. Options: (a) store a bitmap or interval list of free nights in each document and filter on it; (b) run the search ignoring dates, then check availability for the top few hundred candidates in a calendar service; (c) precompute availability per listing for the next N months. Mention (a)/(c) for speed and (b) as the simple start. Treat the result as optimistic; the booking transaction is final (see the booking question).
5. **Ranking:** a score from relevance, quality (ratings, response rate), price competitiveness, distance from the viewport center, and personalization, tuned by experiments. Start with a rule-based scorer; add a learned ranker over the top few hundred candidates later.

```mermaid
flowchart TD
  H((Host)) --> LS[Listing service]
  LS --> DB[(Listing DB<br/>source of truth)]
  DB -.->|"outbox / CDC"| Q[[Change queue]]
  Q --> IW[Index workers]
  IW --> IX[(Search index<br/>geo cells, filters,<br/>availability summary)]
  G((Guest)) -->|"GET /search?bbox=..."| SS[Search service]
  SS -->|"geo filter + filters"| IX
  SS --> RK[Ranker<br/>top few hundred]
```

**Deep dives.**

1. **[Geo indexing choices](#/design/learn/building-blocks/geospatial-indexes-compared).** Geohash or S2 cells in [an inverted index](#/design/learn/building-blocks/inverted-indexes) make "which cells overlap this box" a set of term lookups; [a quadtree](#/design/learn/building-blocks/quadtrees) adapts to density; the engine's built-in BKD-tree geo index is usually enough and avoids building your own. Pick the precision from the viewport size, [query the covering cells](#/design/learn/building-blocks/nearby-search), and filter by exact bounds. Handle viewport crossing the antimeridian and poles by splitting the box.
2. **Density skew.** Manhattan has 50,000 listings in a viewport, a rural area has 5. Don't return everything: rank and return the top N, and for map view cluster results server-side (grid or geohash prefix aggregation) into counts at low zoom levels.
3. **Sharding the index.** Shard by listing ID (even load; every query [scatter-gathers across shards](#/design/learn/data/secondary-indexes-on-sharded-data) and merges) or [by geography](#/design/learn/building-blocks/sharding-by-location) (queries touch few shards but dense cities become hot shards). Most systems shard by ID with replicas, and cache popular queries (city + default filters) for a short TTL.
4. **Freshness.** Price or availability changes should reach the index within seconds; a lag metric on the pipeline is essential. A stale "available" result costs one disappointed click, not a double booking.
5. **Caching.** Cache common queries and viewport tiles (a popular city's first page) with short TTLs; [keep keys canonical](#/design/learn/building-blocks/cache-control-headers-and-cache-keys) (rounded viewport, sorted filters) so hit rates are high.

**The design after the deep dives.** Green marks what they added or changed.

```mermaid
flowchart TD
  G((Guest)) --> SS[Search service<br/>and ranker]
  SS <--> QC[(Query cache<br/>canonical keys,<br/>short TTL)]:::good
  SS -->|"scatter-gather"| IX[(Search index<br/>sharded by listing ID,<br/>replicated)]:::good
  SS --> CL[Map clustering<br/>counts at low zoom]:::good
  DB[(Listing DB)] -.->|CDC| Q[[Change queue]]
  Q --> IW[Index workers]
  IW --> IX
  IW -.->|"index lag"| AL[Freshness alert]:::good
```

**Variant: nearest drivers (ride-hailing).** Locations change every few seconds, so a disk-backed index is the wrong tool. [Keep driver positions in memory](#/design/learn/building-blocks/moving-objects) (Redis geo, or a service holding an in-memory grid) partitioned by cell. Each driver app sends a location update every 4–5 seconds (about 1M drivers → 200,000–250,000 writes/s, a few in-memory shards at ~100K writes/s each), which overwrites the previous entry and expires with a TTL. A ride request queries the rider's cell and neighbors, filters by distance and availability, and hands candidates to a matching service. Use the same cell grid to shard the service so most queries touch one or two partitions.

The API changes too. Drivers send `{lat, lng, heading, ts}` over one long-lived connection (a WebSocket or a gRPC stream) rather than a fresh HTTPS request each time, which is far cheaper at 250,000 updates/s; the `ts` lets the server drop an update that arrives after a newer one. Riders call `POST /v1/rides {pickup, dropoff}` with an idempotency key and get `201 {ride_id, status: MATCHING}`; the matched driver is pushed to the rider's own connection when it's found.

```mermaid
flowchart TD
  D((Driver app)) -->|"position every 4 s"| LOC[Location service<br/>partitioned by cell]
  LOC --> RG[(In-memory grid<br/>entries expire in 30 s)]
  R((Rider)) -->|"request a ride"| M[Matching service]
  M -->|"rider's cell<br/>and its neighbors"| LOC
```

**Done.** Metrics: search latency p99, zero-result rate, index lag, conversion. Failure: if the search cluster degrades, [serve cached popular results](#/design/learn/reliability/graceful-degradation) and a simplified query path.
