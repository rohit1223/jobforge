---
title: API Design & Versioning
bucket: tech
must: false
rank: 7
sources: https://cloud.google.com/apis/design
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism: resource modeling and REST maturity

The Richardson Maturity Model frames REST adoption as four levels: Level 0 is RPC-over-HTTP (one endpoint, HTTP as a dumb tunnel); Level 1 introduces individual addressable **resources**; Level 2 uses **HTTP verbs and status codes** with their real semantics (GET safe and cacheable, POST/PUT/PATCH/DELETE for state); Level 3 adds **hypermedia controls (HATEOAS)** so responses advertise the next legal transitions. Fowler is explicit that, per Fielding, only Level 3 is true REST — Levels 1-2 are pragmatic stepping stones. In practice most production APIs (Stripe, Google, Azure) live at Level 2 and skip HATEOAS because tightly-coupled SDKs and documented URI templates deliver more value than runtime link discovery for machine clients.

Sound resource modeling means nouns not verbs: a collection (`/orchestrators`) and its members (`/orchestrators/{id}`), with sub-resources nested only when ownership is real (`/orchestrators/{id}/nodes`). Google's AIP guidance ties this to a stable **resource name** that is part of the contract — "a resource must not change its name," and the same resource name must be used across major versions. Verbs that don't fit CRUD become "custom methods" (`:cancel`, `:rotate`) rather than RPC endpoints.

### Trade-offs: versioning strategy

The core split is **URI versioning** (`/v2/orchestrators`) vs **header / media-type versioning** (`Accept: application/vnd.acme.v2+json` or `api-version: 2`). Google mandates the major version as the first path segment and forbids minor/patch in the public surface — `v1`, not `v1.2.3` — because the version is part of the protobuf package and REST path, i.e. the contract. Microsoft's REST guidelines allow either a URL segment (`/v1.0/...`) or an `api-version` query/header, but require URL-path embedding when path stability across versions can't be guaranteed.

- **URI versioning** wins on cache-key clarity, log/trace readability, trivial routing, and human-debuggability (you can curl `/v2/...`). It loses on cleanliness: the version pollutes every URL and resource identity arguably shouldn't change just because representation changed.
- **Header/media-type versioning** is theoretically purer (the *resource* is constant; only its *representation* is negotiated via content negotiation) and keeps URLs stable. It loses badly on operability: caches and proxies ignore custom headers unless you set `Vary`, clients forget the header and silently get the default version, and "curl the URL" no longer reproduces the bug.

For a public management plane, URI versioning is the defensible senior default — clients and on-call engineers can see the version in every request. **V1/V2 coexistence** is the real requirement either way: Google states different versions of the same API must work simultaneously within one client app for a reasonable transition period. **Deprecation/sunset** should be machine-signaled, not just a blog post: the `Deprecation` header marks an endpoint as deprecated (boolean or timestamp), and `Sunset` (RFC 8594) gives the hard date the URI stops responding. Google suggests ~180 days notice for beta deprecations; alpha can be pulled without notice.

### Trade-offs: pagination

- **Offset/limit** (`?offset=2000&limit=50`) is trivial to implement and supports random page access, but breaks at scale and under mutation. At scale, `OFFSET 100000` forces the database to scan and discard 100k rows — cost grows linearly with page depth (deep-page latency cliff). Under mutation, if a row is inserted or deleted while a client paginates, every subsequent page **shifts**: rows get skipped or returned twice. Offset has no notion of "where I actually was," only "how many to throw away."
- **Cursor / keyset pagination** encodes the position as a token derived from a stable, ordered key (e.g. `WHERE (created_at, id) > (:last_ts, :last_id) ORDER BY created_at, id LIMIT 50`). It is O(limit) regardless of depth because it seeks via the index instead of counting, and it is stable under inserts/deletes because the cursor anchors to an actual row, not a count. Stripe implements exactly this with `starting_after`/`ending_before` (object-ID cursors, mutually exclusive) plus `has_more`. Google requires `page_size` + opaque `page_token` -> `next_page_token`, where end-of-collection is signaled *only* by an empty `next_page_token`, tokens **must** be opaque and non-parseable, and all other request params must match the call that issued the token.
- The cost of cursors: no random page jumps ("go to page 47"), and the sort key must be unique+stable (hence the `(timestamp, id)` tiebreak — `created_at` alone collides). Adding pagination to an existing non-paginated method is itself a breaking change, so design it in from the start.

### Failure modes / gotchas

- **The breaking-change ship.** Removing or renaming a field, changing a field's type (even to a wire-compatible one), tightening validation, adding a *required* request param, changing a default value, or changing the meaning/format of an existing field are all breaking per Google AIP-180 and Microsoft's guidelines — even though some "feel" additive. The subtle killers: adding a new enum value the client's switch doesn't handle, and clients that depend on the presence/absence of a default-valued field. The lesson: the *consumer's* tolerance defines breaking, not your intuition.
- **Idempotency on retries.** Network retries on non-idempotent POSTs cause double charges / duplicate resources. Stripe's fix: an `Idempotency-Key` (recommend a V4 UUID) on POSTs; Stripe saves the **status code and body of the first request — success or failure, including 500s** — and replays it for any repeat of that key. Concurrent requests with the same key, or requests that fail validation, are *not* saved and may be retried. Keys expire after 24h. Gotcha: reusing a key with *different* parameters errors out (prevents accidental reuse); and keys belong on POST only — GET/DELETE are idempotent by definition.
- **Leaky error contracts.** Ad-hoc `{"error": "..."}` strings force clients to string-match. Use RFC 9457 `application/problem+json` with stable machine-readable `type` (a URI), `title`, `status`, `detail`, `instance`, plus extension members — and clients **must ignore unknown extensions** so the contract can evolve.
- **DTO/persistence coupling.** Serializing ORM entities straight to JSON leaks DB columns into the public contract: a schema migration (rename a column, split a table) silently breaks clients, and you can't add a column without exposing it. A **DTO layer** decouples the wire contract from persistence so each evolves independently.
- **Rate-limit confusion.** 429s must carry `Retry-After` and must NOT be counted as service faults (Microsoft) — otherwise throttled clients blow your error-rate SLO and hammer you in a retry storm. Pair with sane pagination `page_size` caps (Google coerces oversized requests down to the max).

### Design rules (senior defaults)

- Additive-only within a major version: add optional fields/methods, never remove/rename/retype/re-default.
- Version the major in the URI; keep resource names stable across versions.
- Cursor/keyset pagination with opaque tokens; cap and coerce `page_size`; never offset for unbounded data.
- Idempotency keys for all unsafe retried mutations; persist first result keyed by the idempotency key.
- `problem+json` errors with stable `type` codes; clients ignore unknown fields (Postel/tolerant reader).
- DTO boundary between contract and persistence.
- Signal deprecation with `Deprecation` + `Sunset` headers and a published window; keep N-1 running for the transition.
- Defend the contract with consumer-driven contract tests in CI.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through URI versioning vs header/media-type versioning. When would you actually choose header-based, and what operational cost are you signing up for?</summary>

URI versioning (`/v2/...`) puts the major version in the path; header/media-type versioning negotiates the representation via `Accept: application/vnd.x.v2+json` while keeping URLs stable. I default to URI versioning for public and management-plane APIs because the version is visible in every log line, trace, and curl, caches key on it for free, and routing is trivial — on-call can reproduce a bug from the URL alone. I'd only reach for header versioning when I genuinely believe resource identity should be constant and only representation changes, and even then I'm signing up for `Vary` correctness so proxies don't serve the wrong version, plus the silent-default trap where a client that forgets the header gets v1 behavior unknowingly. Google encodes the major version in the path/package and bans minor/patch in the surface; Microsoft allows URL segment or `api-version`, but requires URL embedding when path stability isn't guaranteed. The deciding factor is operability, not theoretical REST purity.

</details>

<details>
<summary><strong>Q:</strong> Why does offset pagination break under mutation and at scale, and how exactly does keyset/cursor pagination fix both?</summary>

Offset says "skip N, take M" — it has no memory of which row you were actually on. Under mutation, if rows are inserted or deleted ahead of your position between page fetches, the whole window shifts, so you skip rows or see duplicates. At scale, `OFFSET 100000` makes the database scan and discard 100k rows before returning yours, so deep-page latency grows linearly with depth. Keyset pagination instead carries a cursor derived from a stable ordered key — `WHERE (created_at, id) > (:last_ts, :last_id) ORDER BY created_at, id LIMIT 50` — which seeks through the index in O(limit) regardless of depth and anchors to a real row, so concurrent inserts/deletes don't shift the window. The cost is no random page jumps and a strictly unique sort key (hence the `(timestamp, id)` tiebreak, since timestamps collide). Stripe ships this as `starting_after`/`ending_before` + `has_more`; Google as opaque `page_token`/`next_page_token`.

</details>

<details>
<summary><strong>Q:</strong> Design an idempotency mechanism for a POST that creates a billable resource. What's stored, what's keyed, and what are the edge cases?</summary>

The client sends an `Idempotency-Key` header (a V4 UUID or similarly high-entropy random string) on the POST. Server-side I persist, keyed by that idempotency key, the first request's outcome — status code and response body — whether it succeeded or failed, including 500s, so any retry of the same key replays the stored result rather than re-executing. Edge cases that matter: a request still in flight with the same key must be rejected/serialized rather than double-executed (concurrency); a key reused with *different* parameters must error to catch accidental reuse; requests that fail input validation aren't saved (nothing executed, safe to retry); and keys should expire (Stripe uses 24h) after which reuse generates a fresh request. I'd scope keys per-account to avoid cross-tenant collisions and only accept them on unsafe verbs — GET/DELETE are idempotent already.

</details>

<details>
<summary><strong>Q:</strong> What concretely counts as a breaking change? Give me the non-obvious ones that engineers ship by accident.</summary>

The obvious ones are removing or renaming a field/endpoint/parameter and changing a field's type. The non-obvious ones that ship "by accident": tightening validation on an existing field, adding a *required* request parameter (existing clients don't send it), changing a default value, changing the format/algorithm used to construct an existing field's value, and adding a new enum value that older clients' switch/case don't handle gracefully. Even type changes that are wire-compatible are breaking per Google AIP-180. And subtly, changing whether a default-valued field is serialized can break clients that treat presence/absence as semantically meaningful. The rule of thumb: the *consumer's* tolerance defines breaking, not whether the change looks additive to me.

</details>

<details>
<summary><strong>Q:</strong> A breaking change shipped to a public API and clients started erroring in production. Walk me through containment and how you prevent a recurrence.</summary>

Containment first: identify the change via the deploy/trace correlation, and roll back or feature-flag it off — for a public API I'd treat the contract as immutable and revert rather than ask clients to adapt mid-incident. Then quantify blast radius from request logs (which clients, which fields) and communicate. Prevention is process, not heroics: introduce consumer-driven contract tests (Pact-style) so every consumer's expectations run against the provider in CI and a removed/retyped field fails the build before merge; add schema-diff linting (e.g. OpenAPI/proto breaking-change detectors) as a required gate; and codify the additive-only rule for within-major changes. Anything truly incompatible goes to a new major version with V1/V2 coexistence and `Deprecation`/`Sunset` headers, never an in-place mutation. The deeper fix is a DTO boundary so a persistence change can't leak into the contract unnoticed.

</details>

<details>
<summary><strong>Q:</strong> Design how you'd version a public API to introduce a redesigned resource model without breaking existing clients. Cover coexistence and decommissioning.</summary>

I'd stand up V2 as a parallel surface (`/v2/...`) that coexists with V1 — Google's guidance is explicit that both majors must work simultaneously within one client app for the transition. Internally I'd route both versions through a shared domain/service layer and map each to version-specific DTOs, so the new contract isn't tied to a data-model migration — V1 and V2 can sit on the same persistence. I'd publish a migration guide, then begin signaling: `Deprecation` header on V1 endpoints (with the announcement timestamp) and a `Sunset` header (RFC 8594) carrying the hard cutoff date, with a generous window (Google suggests ~180 days for beta). I'd instrument per-version, per-client usage so I know who's still on V1 before pulling it, and only decommission once usage drains or the sunset date passes. Resource names stay stable across versions per AIP, so the same entity is identifiable in both.

</details>

<details>
<summary><strong>Q:</strong> Design a pagination contract for a high-traffic list endpoint over a mutating dataset. What goes in the request, the response, and the token?</summary>

Request: `page_size` (optional, with a documented default and a hard max that the server coerces down to, rejecting negatives with `INVALID_ARGUMENT`) and an opaque `page_token`. Response: the items plus `next_page_token`, where end-of-collection is signaled *only* by an empty token — no separate "isLast" flag to get out of sync. The token is an opaque, URL-safe, non-parseable string (base64 of a transparent payload is not sufficient obfuscation per Google) that encodes the keyset cursor — the `(sort_key, id)` of the last row — plus enough to detect tampering. Behind it I run keyset pagination so it's O(limit) at any depth and stable under inserts/deletes. I'd also pin the query parameters: all other params on a follow-up request must match the call that issued the token, so filters can't change mid-iteration. No random page access by design — that's the trade for stability and performance.

</details>

<details>
<summary><strong>Q:</strong> How do you design the error contract for a public API, and why does RFC 9457 problem+json beat a homegrown error shape?</summary>

I'd return `application/problem+json` (RFC 9457) with a stable, documented `type` URI as the machine-readable error code, plus `title`, `status`, `detail`, and `instance`, and domain-specific data in extension members (e.g. `tenant_id`, `violations[]`). The reason it beats a homegrown `{"error":"..."}` string is twofold: clients branch on the stable `type` URI instead of brittle string-matching on a human message, and the spec mandates that clients ignore unrecognized extension members — so I can add fields later without breaking anyone, which is exactly the forward-compatibility property you want in a contract. I keep `title` stable per type (localizing only the `detail`), map `status` to the real HTTP code, and never leak stack traces or internal identifiers into `detail`.

</details>

<details>
<summary><strong>Q:</strong> Why decouple the API contract from the persistence model with a DTO layer? What concretely goes wrong without it?</summary>

Serializing ORM entities directly fuses two things that change at different rates and for different reasons: the public wire contract and the database schema. Without a DTO boundary, a routine migration — renaming a column, splitting a table, changing a type — silently mutates the public response and breaks clients; conversely you can't add a column without exposing it, and you leak internal fields (soft-delete flags, FK ids) you never meant to publish. A DTO layer lets the contract stay additive-only and stable while persistence evolves freely, lets one persistence model back two API versions (V1 and V2 DTOs over the same tables), and gives you a single place to enforce field-level redaction and shaping. The cost is mapping code and the discipline to keep it, which is cheap relative to a contract break.

</details>

<details>
<summary><strong>Q:</strong> How do rate limiting and pagination limits interact with retry behavior, and what's the failure mode if you get the 429 contract wrong?</summary>

A 429 must carry `Retry-After` (seconds or an HTTP date) and, critically, must not be counted as a service fault — Microsoft's guidance is explicit. If you classify throttling as 5xx-style faults, two things break: your error-rate SLO/error budget gets blown by intentional throttling, and clients with naive retry-on-error logic interpret it as a transient server failure and retry immediately without backoff, producing a retry storm that deepens the overload. The correct contract is 429 + `Retry-After` + a distinct machine-readable error type so clients back off deterministically. Pagination limits are the other half: capping and coercing `page_size` down to a max stops a single client from pulling unbounded result sets that themselves act as an availability attack.

</details>

<details>
<summary><strong>Q:</strong> Where does HATEOAS / Richardson Level 3 actually pay off, and why do Stripe and Google effectively stop at Level 2?</summary>

Level 3 (hypermedia controls) makes responses self-describing — the server advertises the legal next transitions as links, so clients discover actions at runtime instead of hardcoding URI templates, which decouples clients from URL structure and is genuinely useful for long-lived, loosely-coupled or human-browsable surfaces. The reason most machine-facing APIs (Stripe, Google) live at Level 2 is that their clients are versioned SDKs against documented, stable URIs: the runtime link-following indirection buys little when the URL scheme is already a published contract and the SDK is regenerated per version, and it adds payload and client complexity. Fowler notes that, strictly per Fielding, only Level 3 is "true" REST — but pragmatically, Level 2 with strong verb/status-code discipline and stable resource modeling is what ships. I treat HATEOAS as a tool for specific cases (workflow state machines, pageable `nextLink`), not a blanket requirement.

</details>

<details>
<summary><strong>Q:</strong> For a public management API, how do you layer authentication and authorization — OAuth2, RBAC, mTLS, tenant isolation, IP restrictions? What's each defending against?</summary>

These are layers at different trust boundaries, not alternatives. mTLS at ingress authenticates the *client/workload* at the transport layer — it defends the public endpoint against unauthenticated callers and is appropriate for a management plane where callers are known systems, not anonymous browsers. OAuth2 handles *delegated identity and scopes* — the bearer token proves who the principal is and what coarse scopes they hold. RBAC then does *fine-grained authorization* on top of that identity — mapping roles to allowed operations on specific resources. Tenant validation is the isolation boundary that ensures an authenticated, authorized principal can only touch resources within its own tenant — it defends against the classic broken-object-level-authorization (IDOR) class where a valid token reaches another tenant's resource id. IP allowlisting is defense-in-depth narrowing the network surface so even a leaked credential is only usable from sanctioned networks. The order matters: terminate mTLS, validate the token, resolve tenant, enforce RBAC, then check IP — failing fast and cheaply first.

</details>

<details>
<summary><strong>Q (resume):</strong> You re-architected an admin plane into a V2 API spanning 16 named resources with a DTO layer and parallel V1/V2 migration. Walk me through the design decisions that made the migration non-breaking.</summary>

The non-breaking property came from two deliberate decisions. First, I introduced a DTO layer that decoupled the API contracts from persistence, so V1 and V2 could expose different contract shapes over the *same* data model — that's what let me run a parallel V1/V2 migration without any data-model changes, which is the part that usually forces a risky big-bang. Second, I modeled V2 as a stable set of 16 named resources (nouns with consistent collection/member URIs) rather than RPC-style endpoints, and stood it up alongside V1 so existing clients kept working while new clients adopted V2 at their own pace. I also modernized pagination and query behavior in V2 so the new surface didn't inherit V1's scaling limits. Concretely, the DTO boundary is the linchpin: it absorbed contract evolution and version divergence so neither version constrained the other and persistence stayed untouched during cutover.

</details>

<details>
<summary><strong>Q (resume):</strong> You modernized pagination in the V2 admin API. What was wrong with the old behavior and what did the new contract look like?</summary>

The motivation for modernizing pagination on an admin plane is that admin resources are listed frequently, mutate while being browsed, and can grow large — the regime where offset/limit hurts most. Offset degrades on deep pages because the database scans and discards rows, and it's unstable under concurrent mutation, returning skipped or duplicated rows as the dataset shifts. The modern contract replaces that with cursor/keyset semantics: an opaque continuation token anchored to a stable ordered key so listing is O(page_size) at any depth and stable under inserts/deletes, with a capped, coerced page size to bound load, and end-of-results signaled by an absent token rather than a separate flag. Because this lives behind the DTO/contract layer, V2 got the new behavior while V1 kept its old contract — the modernization was scoped to the new version, not forced retroactively onto existing clients.

</details>

<details>
<summary><strong>Q (resume):</strong> Your public management APIs enforce tenant validation, RBAC, IP restrictions and mTLS ingress. How did you reason about where each control sits and what gap each one closes?</summary>

I reasoned about it as concentric trust boundaries, terminating the cheapest/broadest checks first. mTLS at ingress is the network/transport gate — it ensures only mutually-authenticated clients even reach the management plane, which is appropriate because the callers are known systems, not the public internet. Once past ingress, RBAC enforces what an authenticated principal is allowed to do at the operation level. Tenant validation is the isolation control I weighted most heavily, because the highest-severity gap for a multi-tenant management API is broken object-level authorization — a perfectly valid, authorized principal reaching another tenant's resource by id — so every resource access is scoped to the caller's tenant rather than trusting the id in the path. IP restrictions are defense-in-depth that shrink the usable surface of any leaked credential. The design intent was that no single control failing — a leaked token, a misconfigured role — collapses isolation on its own.

</details>

## Say it with your resume

- I re-architected the Orchestrator admin plane into a production-ready **V2 API surface spanning 16 named resources**, modeling stable noun-based resources rather than RPC endpoints — a Level-2 REST design with consistent collection/member semantics.
- I **decoupled API contracts from persistence via a DTO layer**, which is precisely what let two API versions evolve independently over one data model and kept schema changes from leaking into the public contract.
- That DTO boundary is what enabled a **parallel V1/V2 migration with no data-model changes** — V1 kept working for existing clients while V2 rolled out, exactly the coexistence pattern Google's versioning guidance calls for.
- I **modernized pagination and query behavior** in V2, moving off the offset model that degrades on deep pages and is unstable under mutation, toward cursor/keyset-style semantics scoped to the new version.
- I exposed **secure public management APIs** layering mTLS ingress, OAuth2/RBAC, tenant validation, and IP restrictions as concentric trust boundaries — with tenant isolation as the control closing the highest-severity (cross-tenant object-level) gap.

## Sources

- [Google API Improvement Proposals — Versioning (AIP-185)](https://google.aip.dev/185)
- [Google AIP-180 — Backwards compatibility](https://google.aip.dev/180)
- [Google AIP-158 — Pagination](https://google.aip.dev/158)
- [Google Cloud API Design Guide](https://cloud.google.com/apis/design)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/graph/Guidelines-deprecated.md)
- [Stripe API — Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [Stripe API — Pagination](https://docs.stripe.com/api/pagination)
- [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [RFC 8594 — The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html)
- [Martin Fowler — Richardson Maturity Model](https://martinfowler.com/articles/richardsonMaturityModel.html)
