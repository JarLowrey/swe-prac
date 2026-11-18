Here is the framework applied to a common prompt: "Design a system that lets guests search for and
book vacation rentals." Each step is shown at the level of detail you'd actually say or write in
the interview.

**1. Requirements.** Functional: guests search by location, dates and guest count; guests book a
listing for a date range; hosts manage their calendar. Non-functional: never double-book a night
(strong consistency for bookings); search under about 300 ms; search can show slightly stale
availability for a few seconds. Out of scope: payments, reviews, messaging.

**2. Estimates.** Assume 10M listings and 1M bookings a day, which is about 12 bookings per second
on average and maybe 100 at peak. Searches run perhaps 100x that. Conclusion: writes are small
enough for one relational database; search is the part that needs scaling.

**3. API.** The three endpoints from step 3 of the framework: search, create booking (with an
idempotency key), cancel booking.

**4. Data model.** Listing (id, host, location, details) in a listings store. Booking (id, listing,
guest, check-in, check-out, status). Booked nights as one row per listing per night, with a unique
constraint on (listing, night), in a relational database. Search reads a denormalized index of
listings plus availability.

**5. High-level design.**

```
Guest app -> Load balancer -> Search service  -> Search index (listings + availability)
                           -> Booking service -> Relational DB (listings, bookings, booked nights)
Relational DB --change stream--> Indexer -> Search index
```

Search reads from the index, which an indexer keeps up to date from database change streams. That
makes search eventually consistent, which the requirements allow. Bookings write straight to the
relational database, which is the single source of truth.

**6. Deep dives.**

- *Preventing double bookings.* Insert one row per night inside a single transaction. The unique
  constraint on (listing, night) means the second of two simultaneous bookings fails, so no locks
  are needed in application code. For a checkout flow, insert rows with status "held" and an expiry
  time, and release them with a background job if payment doesn't complete.
- *Fast, fresh-enough search.* A geo index narrows listings by location; availability is stored in
  the index as booked date ranges. Stale results are acceptable because the booking transaction is
  the final check; if a listing was just taken, the guest sees a clear "no longer available"
  message.
- *Retries.* The idempotency key on create-booking means a client that times out and retries can't
  create two bookings.

**7. Wrap-up.** The biggest risk is a popular listing getting many simultaneous booking attempts;
the unique constraint handles correctness, and a per-listing rate limit protects the database. I'd
monitor booking error rates and indexer lag, and alert if lag exceeds a minute. Next I'd add the
payments flow and host calendar sync with external calendars.
