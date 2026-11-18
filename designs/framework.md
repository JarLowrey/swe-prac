A system design interview is not a test of whether you can recall how a famous app works. It is a
45-minute simulation of a design review, and you are the engineer leading it. This framework gives
you a repeatable structure so you spend your energy on the problem, not on deciding what to do
next.

## What the interviewer is grading

The interviewer writes feedback in a handful of categories, and almost every company uses some
version of these five. Your job is to give them clear evidence for each one.

| Category | What they want to see | Evidence you can hand them |
| --- | --- | --- |
| Problem navigation | You turn a vague prompt into a clear, scoped problem. | A written list of requirements, scale numbers and what's out of scope. |
| High-level design | You can lay out a working system end to end. | A diagram where every requirement maps to a component. |
| Technical depth | You know how the parts actually behave, not just their names. | Two or three deep dives with real mechanisms, numbers and failure modes. |
| Trade-offs | You choose between options for reasons, not by habit. | "I picked X over Y because of Z; if Z changes, I'd switch." |
| Communication | You lead the conversation and the interviewer can follow it. | Narrating your plan, checking in at each stage, writing things down. |

Notice that "got the right answer" is not a category. There is no single right design. Two
candidates can draw very different systems and both pass, because the grade is on how you reason,
not on matching an answer key.

The bar also moves with level. A mid-level candidate passes by producing a reasonable design with
some prompting. A senior candidate is expected to drive: pick the requirements that matter, choose
which parts to go deep on, and raise risks before the interviewer does.

## The 45-minute framework

Use the same seven steps every time. The timings are for a 45-minute design slot; scale them if
your interview is longer. Say each step out loud as you start it, so the interviewer always knows
where you are.

| Step | Time | Output on the board |
| --- | --- | --- |
| 1. Requirements | 5 min | Functional list, non-functional list, out of scope |
| 2. Estimates | 3 min | Users, QPS, storage: only the numbers that change a decision |
| 3. API | 5 min | 3–6 endpoints with inputs and outputs |
| 4. Data model | 5 min | Main entities, keys, and which store holds them |
| 5. High-level design | 10 min | Diagram covering every functional requirement |
| 6. Deep dives | 15 min | 2–3 hardest parts, designed properly |
| 7. Wrap-up | 2 min | Bottlenecks, failure modes, what you'd do next |

### 1. Requirements (5 minutes)

This is the most valuable time in the interview, exactly like the problem-clarification step in a
coding round. Build the right thing before building the thing right.

- **Functional:** the 3–5 things a user can do. Write them as verbs: "search listings," "book a
  stay," "cancel a booking."
- **Non-functional:** scale, latency, availability, consistency, durability. Ask which matters
  most; the answer shapes everything.
- **Out of scope:** say out loud what you're skipping (payments, auth, analytics). It shows
  judgment and protects your time.

End the step by reading the list back and asking: "Does this match what you had in mind?"

### 2. Estimates (3 minutes)

Use napkin math, but only as far as it changes a decision. "About 1,000 bookings per second at
peak, so one database can handle writes" is useful. Calculating storage to three digits is not. If
the numbers don't change anything, say so and move on.

### 3. API (5 minutes)

Write each endpoint with its key inputs and outputs. This forces you to pin down what the system
actually does before you draw boxes.

```
GET  /listings?location=&checkIn=&checkOut=&guests=  -> [Listing]
POST /bookings {listingId, checkIn, checkOut, idempotencyKey} -> Booking
DELETE /bookings/{id} -> 204
```

Mention pagination, idempotency keys for anything that charges money, and REST vs. GraphQL vs.
gRPC only if it matters.

### 4. Data model (5 minutes)

List the main entities, their keys, and the relationships between them. Then pick a store for each
and give one reason: "Bookings go in a relational database because I need transactions to prevent
double booking."

### 5. High-level design (10 minutes)

Draw the simplest system that satisfies every functional requirement: clients, load balancer,
services, databases, caches, queues. Then trace one request through it out loud. If a requirement
has no box that serves it, you've found a gap.

Keep it simple on purpose. Scaling comes next, and it's easier to discuss when the base design is
clear.

### 6. Deep dives (15 minutes)

This is where you earn the grade. Pick the 2–3 hardest parts of this specific problem, say why
they're hard, and design them properly. Good candidates for a deep dive:

- The part where correctness matters most (double booking, double charging)
- The hottest path at scale (search, feed reads)
- The part most likely to fail (a third-party dependency, a hot key)

At senior level, propose the deep dives yourself: "The two hardest parts here are preventing double
bookings and keeping search fast. I'd like to start with double bookings." If the interviewer
redirects you, follow them; they're telling you what they want to grade.

### 7. Wrap-up (2 minutes)

Name the biggest remaining bottleneck, one or two failure modes and how you'd detect them, and what
you'd build next. Ending on a clear summary leaves a strong last impression.

## What makes an answer senior

The framework gets you a passing design. These habits are what move feedback from "solid" to
"senior":

- **You drive.** You propose the scope, the order, and the deep dives. The interviewer reacts to
  your plan instead of feeding you the next question.
- **Every choice has a reason and an alternative.** "I'm using a queue here instead of calling the
  email service directly, so a slow email provider can't slow down bookings."
- **You use numbers.** "A single Postgres primary handles a few thousand writes per second, and we
  need about 1,000, so no sharding yet."
- **You raise failure modes before you're asked.** What happens when the cache is down, the payment
  provider times out, or two users book the same night at the same moment?
- **You think about operating it.** How you'd roll it out (feature flags, gradual rollout), what
  you'd monitor, what alert would wake someone up.
- **You keep it as simple as the requirements allow.** Adding Kafka, microservices and sharding to
  a system with 100 requests per second is a negative signal, not a positive one. Say when you'd
  add complexity: "If writes grow 10x, I'd shard by listing ID."
- **You adapt.** When the interviewer adds a constraint ("now it must work across regions"), you
  revisit earlier choices instead of bolting something on.

## Common mistakes

| Mistake | Why it hurts | Instead |
| --- | --- | --- |
| Drawing boxes in the first minute | You design for a problem you haven't defined. | Spend the first 5 minutes on requirements, even if it feels slow. |
| Spending 15 minutes on estimates | Burns time that should go to deep dives. | Estimate only what changes a decision. |
| Naming tools instead of explaining them | "Use Kafka" shows vocabulary, not understanding. | Say what property you need: "a durable, ordered log that consumers can replay." |
| Designing for planet scale by default | Adds complexity the requirements don't need. | Start simple and say when you'd scale. |
| Going silent while thinking | The interviewer can't grade what they can't hear. | Think out loud, even when unsure. |
| Defending a choice after it's challenged | Reads as hard to work with. | "Good point. If that's a concern, I'd switch to X." |
| Never reaching deep dives | Technical depth is a whole grading category. | Watch the clock; start deep dives by minute 25. |

## Phrases that help

- To open: "Before I design anything, I'd like to spend a few minutes on requirements."
- To scope: "I'll leave payments and auth out of scope unless you'd like them in."
- To check in: "Here's the high-level design. Before I go deeper, does this cover what you
  expected?"
- To pick deep dives: "The two hardest parts here are X and Y. I'd start with X because it's where
  correctness matters most."
- To show a trade-off: "Option A is simpler; option B handles more load. Given our numbers, I'd
  pick A and move to B if writes grow 10x."
- When you don't know: "I haven't used that directly. Here's how I'd reason about it."
- To close: "The biggest remaining risk is X. I'd monitor it with Y, and the next thing I'd build
  is Z."

## Variant: product architecture interviews

Some companies let you choose this instead of classic system design. The same framework applies,
but spend more time on the API, the client–server contract, pagination and the data model, and
less on infrastructure like sharding and queues.
