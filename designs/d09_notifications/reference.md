**Requirements.** Functional: other services send notifications (push, SMS, email, in-app) to users; users set preferences per channel and category; templates and localization; scheduled and bulk sends (a campaign to 10M users); delivery tracking. Non-functional: reliable (a password reset or payment alert must arrive); no duplicates; low latency for transactional messages (seconds), higher tolerance for marketing; scales to bursts; respects provider limits and user quiet hours.

**Estimates.** 1B notifications/day ≈ 12,000/s average, but bursty: a campaign or breaking-news alert can send 10M in a few minutes (≈ 50,000+/s). Channels differ: push and in-app are cheap; SMS costs money per message; email has deliverability and reputation constraints.

**API.**

- `POST /notifications {user_id | audience, type, template_id, params, channels?, priority, send_at?, dedupe_key}` → `202 {notification_id}` ([async accepted](#/design/learn/networking/async-request-reply))
- `GET /notifications/{id}` status; user-facing preferences API `PUT /users/{id}/preferences`; unsubscribe endpoints and [webhook receivers](#/design/learn/networking/webhooks) for provider callbacks (delivered, bounced, opened).

**Data model.** `preferences(user_id, category, channel, enabled, quiet_hours, locale)`; `device_tokens(user_id, platform, token, last_seen)`; `notification(id, user_id, type, status, dedupe_key, created_at)`; `delivery_attempt(notification_id, channel, provider, status, attempt, at)`. Templates in a versioned store.

**High-level design (a pipeline of queues).**

1. **Ingest API** validates, [dedupes on `dedupe_key`](#/design/learn/networking/idempotency-keys), persists, and publishes to a **[priority-partitioned queue](#/design/learn/building-blocks/message-queues-and-streams)** (separate topics for transactional vs marketing [so a campaign can't starve a password reset](#/design/learn/reliability/bulkheads)).
2. **Orchestrator / routing workers** consume: look up the user's preferences and quiet hours, pick channels (fallback order, for example push, then SMS for critical), render the template in the user's locale, apply per-user frequency caps, and enqueue per-channel jobs. Large audiences are expanded here, in chunks, from a query or segment, not by the caller.
3. **Channel workers** (push, SMS, email, in-app) send through providers (APNs, FCM, SMS and email providers) with [per-provider rate limiting](#/design/learn/building-blocks/rate-limiting) and connection pooling.
4. **Provider callbacks** update delivery state (delivered, bounced, unsubscribed, invalid token), which feeds back into the user's records (remove dead device tokens, suppress bounced addresses).

**Deep dives.**

1. **Reliability and retries.** At-least-once with retries ([exponential backoff and jitter](#/design/learn/reliability/retries-with-backoff-and-jitter), capped), [a dead-letter queue](#/design/learn/reliability/dead-letter-queues) for permanent failures, and provider failover (a second SMS or email provider when the first degrades, with a [circuit breaker](#/design/learn/reliability/circuit-breakers)). Persist state before sending so a crash resumes instead of losing work.
2. **Deduplication.** Duplicate notifications annoy users (and cost money). Use `dedupe_key` plus a short-lived dedupe store; [make workers idempotent](#/design/learn/reliability/deduplicating-consumers) per (notification, channel); and remember that provider calls may succeed without us seeing the response, so the occasional duplicate is possible: for critical messages prefer a possible duplicate over a lost message, and say so.
3. **Throttling and fairness.** Per-user caps (no more than N marketing pushes per day), per-provider rate limits (APNs/FCM and SMS carriers throttle), per-tenant quotas if multi-tenant, and a smooth ramp for big campaigns (spread 10M sends over minutes rather than a single spike). [Token bucket per provider](#/design/learn/building-blocks/token-bucket) (see the rate limiter question).
4. **Prioritization.** Separate queues and worker pools by priority, so transactional traffic keeps flowing during a marketing blast; [shed or delay low priority first](#/design/learn/reliability/load-shedding) under overload.
5. **Scheduling.** Scheduled sends live in a time-indexed store (a delayed queue, or a table sharded by minute that a scheduler scans); user-local-time sends are bucketed by time zone.
6. **Preferences and compliance.** Honor opt-outs instantly (check at send time, not just at enqueue time), keep a global suppression list, respect quiet hours and regional regulations (consent, unsubscribe links), and keep audit logs.
7. **Observability.** Metrics per channel and provider: send latency, delivery rate, bounce rate, [queue depth/lag](#/design/learn/building-blocks/backpressure-and-consumer-lag), retry rate, dead-letter volume. [Alert on delivery rate drops](#/design/learn/reliability/alerting-on-symptoms), which signal provider or credential problems.

**Wrap-up.** Extensions: in-app notification feed (stored per user, read/unread state, real-time push over the chat-style WebSocket), A/B testing of content, digest batching (combine ten notifications into one summary), and analytics on opens and conversions.
