# Entitlement Management Service — Interview Thought Process

## 0. Time Budget (1-Hour Interview)

This is a 1-hour slot, so every minute counts. I wouldn't freestyle it — I'd mentally allocate time before starting so I don't end up with 5 minutes left and no working code.

| Phase | Time | What I'm Doing |
|-------|------|----------------|
| Requirements & questions | ~5 min | Ask clarifying questions, confirm scope |
| Design out loud | ~5 min | Data structure, class shape, error strategy — talk before type |
| Core implementation | ~25 min | The three methods, custom exception, input validation |
| Tests | ~15 min | Happy paths first, then edge cases |
| Review & discuss | ~10 min | Walk the interviewer through the code, name trade-offs, invite feedback |

**Key discipline:** I cut scope ruthlessly to protect the coding time. If I'm still asking questions at minute 10, I'm already behind. I keep the requirements phase tight — ask only the questions that would actually change my implementation, not every possible question I could think of.

**What I deprioritize under time pressure:**
- Concurrency handling — I mention it and move on
- Persistence layer — acknowledged, not built
- A full product catalog validation — noted as a future hook
- Exhaustive input validation — I cover the obvious cases (None, empty string) and move on

**What I never cut:**
- The happy path working end-to-end
- At least one edge case per method
- Tests — if I run out of time I'd rather have fewer features with tests than more features with none

---

## 1. Initial Read & First Impressions

When I first read this prompt, three operations jump out immediately: assign, revoke, retrieve. That's a classic CRUD subset — essentially write, delete, read on a user-product mapping. Simple on the surface, but entitlement systems tend to hide real complexity in the edge cases.

Before I write a single line of code, I want to make sure I actually understand what's being asked. I'd pause here and ask the interviewer a series of questions.

---

## 2. Clarifying Questions I Would Ask

### Data Model Questions

**Q1: What is a "user"?**
Is a user identified by an integer ID, a UUID, an email address, or something else? I'll assume a string ID for now, but this affects how we validate inputs.

**Q2: What is a "product"?**
Same question — is `product_id` a string, enum, integer? Is there a fixed catalog of valid products, or can arbitrary product IDs be assigned? If there's a catalog, do we need to validate that a product exists before assigning it?

**Q3: What is an "entitlement"?**
Is an entitlement simply the relationship "user X has product Y," or does it carry additional metadata — things like:
- An expiration date (time-limited licenses)?
- A seat count (can a user have multiple seats of the same product)?
- An assigned-by field (audit trail for who granted it)?
- A status field (active, suspended, pending)?

**Q4: Can a user have the same product assigned more than once?**
This is probably the most critical data model question. If user A is assigned `AutoCAD` twice — is that two separate entitlements, or is the second assignment a no-op? This shapes whether we store a set or a list.

---

### Behavior & Business Logic Questions

**Q5: What should happen when we assign an entitlement a user already has?**
Options: (a) silently succeed (idempotent), (b) raise an error, (c) create a duplicate record. I'd lean toward idempotent by default, but I want confirmation.

**Q6: What should happen when we try to revoke an entitlement that doesn't exist?**
Options: (a) silently succeed, (b) raise a `not found` error. Both are defensible — I'd ask which behavior the platform expects.

**Q7: Are there any entitlements that cannot be revoked?**
Some systems have a "base entitlement" that every user always has. Should revoke protect against removing these?

**Q8: What should `retrieve` return when a user has no entitlements?**
An empty list is the obvious answer, but I want to confirm — and also clarify: should we distinguish between "user exists but has no entitlements" vs. "user doesn't exist in our system at all"?

---

### Scale & Context Questions

**Q9: Is this in-memory or backed by a persistent store?**
The prompt says "simple service," which suggests in-memory for now. But knowing whether this is a prototype or production code changes decisions around thread safety, persistence, and error handling.

**Q10: Is this single-threaded or do we need to handle concurrent access?**
If multiple threads or requests can modify entitlements at the same time, we need locking. An in-memory dict in Python without locks can have race conditions under concurrent writes.

**Q11: What's the expected scale?**
Hundreds of users? Millions? This affects data structure choices — a dict-of-sets works fine at small scale but wouldn't survive in production without a database.

---

## 3. Assumptions I'll State Explicitly

Since this is a coding exercise, I'll make reasonable assumptions where I can't get answers and state them clearly upfront. This shows the interviewer I know what decisions I'm making and why.

| # | Assumption | Reasoning |
|---|------------|-----------|
| A1 | User IDs and product IDs are non-empty strings | Simple, flexible, doesn't over-constrain |
| A2 | A user can only hold one instance of a given product (set semantics) | Most entitlement systems work this way; prevents duplicates |
| A3 | Assigning an already-held entitlement is a no-op (idempotent) | Safer default; prevents confusing errors on retry |
| A4 | Revoking a non-existent entitlement raises a descriptive error | Makes bugs visible rather than silently swallowing them |
| A5 | Retrieving entitlements for an unknown user returns an empty list | A user with no history is equivalent to one with no entitlements |
| A6 | This is in-memory, single-threaded for now | Prompt says "simple"; I'll note where concurrency hooks would go |
| A7 | No persistence layer needed | Same as above — prototype scope |
| A8 | There is no product catalog to validate against | We trust the caller to pass valid product IDs |

---

## 4. Edge Cases I'd Cover

Even in a simple system, these are the cases that separate a junior answer from a strong one:

### Input Validation
- `user_id` is `None`, empty string, or not a string
- `product_id` is `None`, empty string, or not a string
- Inputs with leading/trailing whitespace — should `"AutoCAD"` and `" AutoCAD"` be treated the same?

### Assign
- Assigning a product the user already has → idempotent, no error
- Assigning to a brand-new user who has never been seen before → should auto-initialize their record

### Revoke
- Revoking a product a user doesn't have → raise a clear error
- Revoking from a user who has never been seen before → same error path as above
- After revoking all products, does the user's record remain or get cleaned up? (Minor, but good to consider)

### Retrieve
- User with no entitlements → empty list (not None, not an error)
- User who has never been seen → empty list
- Return type: should this be a list or a set? (I'd return a sorted list for deterministic output — easier to test and reason about)

### Concurrency (noted, not necessarily implemented)
- Two threads assigning the same product to the same user simultaneously
- A thread reading while another is writing
- I'd flag that in production this needs a lock or a transactional database

---

## 5. How I'd Structure the Solution (Before Writing Code)

I'd describe my design in plain English first, then code it:

**Core data structure:**
A dictionary mapping `user_id → set of product_ids`. A `set` gives O(1) assign, revoke, and membership check. A `dict` gives O(1) user lookup.

```
{
  "user_123": {"AutoCAD", "Revit", "Fusion360"},
  "user_456": {"BIM360"}
}
```

**Class design:**
A single `EntitlementService` class with three public methods:
- `assign_entitlement(user_id, product_id) -> None`
- `revoke_entitlement(user_id, product_id) -> None`
- `get_entitlements(user_id) -> list[str]`

**Error handling:**
A custom exception class — e.g., `EntitlementError` — so callers can catch domain errors specifically rather than catching generic `ValueError` or `KeyError`.

**Extensibility hooks I'd mention but not over-engineer:**
- A persistent store could swap in by changing the internal storage to a DB client
- Concurrency could be added with a `threading.Lock` around mutations
- A product catalog could validate IDs at the boundary without changing the core logic

---

## 6. How I'd Approach Testing

I'd think about tests before writing implementation (or at least in parallel). The test cases I'd write:

1. **Happy path — assign and retrieve:** Assign one product, confirm it appears in retrieve.
2. **Happy path — revoke:** Assign then revoke, confirm it no longer appears.
3. **Happy path — multiple products:** Assign several, retrieve all.
4. **Idempotent assign:** Assign same product twice, confirm no duplicate in retrieve.
5. **Revoke non-existent entitlement:** Expect a specific error.
6. **Retrieve for unknown user:** Expect empty list.
7. **Input validation:** Empty strings, None values → expect errors.
8. **Order of operations:** Assign, revoke, re-assign — confirm state is correct.

---

## 7. What I'd Communicate to the Interviewer Throughout

- **State assumptions out loud** as I make them, so they can redirect me if I'm wrong.
- **Talk before I type** — describe the data structure and method signatures before opening an editor.
- **Name trade-offs** — e.g., "I'm using a set here for O(1) lookups; if we needed to track assignment history we'd switch to a list of records."
- **Ask 'does this match your expectations?'** after sketching the design, before going deep on implementation.
- **Don't over-engineer** — the prompt says "simple," so I won't add caching layers, event buses, or database ORM models unless asked.

---

## 8. Red Flags I'm Actively Avoiding

- Jumping straight to code without clarifying questions — shows poor requirements analysis.
- Returning `None` from retrieve instead of an empty list — callers have to null-check everything.
- Using a list instead of a set — O(n) duplicate check on every assign, easy to fix, signals inattention.
- Swallowing errors silently — e.g., revoking something that doesn't exist and saying nothing.
- Over-engineering — adding features the prompt didn't ask for wastes time and signals poor scope management.
- Forgetting to validate inputs — passing `None` as a user ID should fail loudly, not produce confusing behavior later.
