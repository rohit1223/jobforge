---
title: Distributed Systems & Control Planes
bucket: tech
must: false
rank: 6
sources: https://aws.amazon.com/builders-library/
generated: true
---

## Core concepts

### Consistency models (mechanism)

A consistency model is a *safety property*: it defines the set of operation histories a system is permitted to produce ([Jepsen](https://jepsen.io/consistency)). Three points on the spectrum matter at the senior level:

- **Linearizable** — every operation appears to take effect atomically at a single instant between its invocation and its response, and the resulting total order respects *real-time* ordering: if op A completes before op B begins, A precedes B globally. This is the "single-copy, freshest-read" illusion. A linearizable read always reflects the most recently completed write. Raft, ZooKeeper, etcd, and a properly configured single-leader store give you this for reads served through the leader.
- **Sequential** — all processes observe the *same* total order, and each process's own ops appear in program order, but the order need not respect wall-clock real time. So a read can legally return a stale value as long as everyone agrees on the same history. Cheaper to achieve; weaker recency.
- **Eventual** — replicas converge *if writes stop*, with no ordering or recency guarantee in the interim. You can read your own writes out of order, see writes appear and disappear, etc. Dynamo-style stores and async replicas live here.

**Trade-offs.** Linearizability requires coordination on the critical path (a quorum round-trip or a leader hop), which costs latency and caps throughput. Sequential drops the real-time constraint to relax that. Eventual buys availability and low latency at the cost of programmer-visible anomalies you must design around (conflict resolution, CRDTs, read-repair).

**Failure modes / gotchas.** "Strong consistency" is overloaded marketing; pin people to linearizable vs serializable (serializable is a *transaction* isolation property over multiple objects; linearizable is a *single-object* recency property — they are orthogonal, and "strict serializable" is the combination). The classic gotcha: a follower read on a leader-based system is *not* linearizable unless you route through the leader or do a quorum/lease read — stale follower reads silently violate recency.

### CAP and PACELC (trade-offs)

CAP says that under a network **P**artition you must choose **A**vailability or **C**onsistency. But partitions are rare, so CAP describes only the edge case. **PACELC** (Abadi, 2010/2012, *Consistency Tradeoffs in Modern Distributed Database System Design*) extends it: **if P**artition then A-vs-C, **e**lse (normal operation) you still trade **L**atency vs **C**onsistency ([PACELC](https://en.wikipedia.org/wiki/PACELC_design_principle)). The "else" clause is the one that matters day to day, because the consistency/latency tension is present on *every* request, not just during the rare partition. Classify systems as PC/EC (e.g. a CP store: consistent during partitions, consistent-but-slower normally) vs PA/EL (Dynamo-style: available + low latency, eventually consistent).

**Gotcha.** CAP's "consistency" means linearizability specifically and "availability" means *every* non-failing node responds — much stricter than the colloquial use. Most production "AP" systems are really partition-tolerant-with-degraded-consistency, not the formal AP.

### Consensus / Raft (mechanism)

Raft provides a linearizable replicated log via a single elected leader ([Raft paper](https://raft.github.io/raft.pdf)).

- **Leader election.** Time is divided into monotonically increasing *terms*. A follower that hears no heartbeat within a randomized election timeout (e.g. 150–300 ms) becomes a candidate, increments the term, and requests votes. **Randomized timeouts** are the key trick: they make simultaneous candidacy unlikely, so one server usually times out first, wins, and sends heartbeats before others start — resolving split votes without a coordinator.
- **Log replication.** The leader appends a client command, then replicates via `AppendEntries`. An entry is **committed** once it is durably stored on a **majority**; the leader then advances its commit index and applies to the state machine. The Log Matching property guarantees that if two logs share an entry at a given index/term, all preceding entries are identical.
- **Why quorum size matters.** Commit and election both require a *majority*. Any two majorities of an N-node cluster must overlap in at least one node, so a newly elected leader is guaranteed to have seen every previously committed entry — that overlap is what prevents data loss and split-brain. With 5 nodes you tolerate 2 failures; with 3, only 1. Even-sized clusters waste a node (4 nodes still only tolerate 1 failure, same as 3) — always run odd N.

**Failure modes.** A partition can never produce two leaders in the same term because a partition cannot contain two disjoint majorities. The minority side cannot commit and stalls until it rejoins — that is consensus correctly choosing C over A. Watch for: tiny clusters losing quorum on a single double-fault; slow disks causing missed heartbeats and election churn; and the fact that consensus is expensive, so you keep the *control plane* on Raft and the *data plane* off it.

### Replication: sync vs async, leader/follower, split-brain (trade-offs)

- **Synchronous replication** waits for replica acknowledgment before acking the client → no data loss on failover (RPO≈0) but the slowest replica gates write latency and a replica outage can stall writes.
- **Asynchronous** acks the client immediately and ships in the background → low latency, high availability, but a leader failure loses the un-shipped tail (RPO > 0). Semi-sync (ack from any one replica) is the common compromise.

**Split-brain** is the canonical failure: a partition or a botched failover promotes two leaders that both accept writes, producing divergent, irreconcilable histories. Defenses: quorum/majority leadership (Raft-style), fencing tokens (monotonic epoch numbers that the storage layer rejects if stale), and STONITH. The most dangerous incidents come from *automatic* failover plus async replication: you promote a replica that was behind, lose committed-looking writes, and then the old leader rejoins and conflicts.

### Partitioning / sharding + rebalancing (mechanism)

Spread data across shards by hash (even distribution, range queries impossible) or by range (range scans cheap, hot-spot prone). **Consistent hashing** with virtual nodes minimizes key movement when the topology changes — adding a node remaps only ~1/N of keys instead of nearly all. Rebalancing must move data *without* a hot spot or a stop-the-world: throttle the move, keep the old replica serving until the new one is caught up and verified, then cut over.

**Failure modes.** Hot shards from skewed keys (a celebrity tenant), resharding storms that saturate the network, and routing-table staleness where a client sends to the old owner mid-move. Senior answer: gate cutover on a health/consistency check, never on a timer.

### Idempotency & the exactly-once illusion (mechanism + gotcha)

There is no exactly-once *delivery* over an unreliable network — only at-least-once delivery plus idempotent processing, which yields exactly-once *effects*. Implement with an idempotency key (client-supplied request ID) deduplicated at the server, or design operations to be naturally idempotent (PUT of a desired-state, not "increment"). **Gotcha:** dedup windows expire, and "idempotent" retries that carry a *new* key (because the client regenerated it on retry) silently double-apply. Effects must be idempotent end-to-end, including side effects like sending an email or charging a card.

### Retries, backoff, jitter — and the retry storm (failure mode)

Retries are "selfish": each client improves its own odds while adding load to an already-struggling dependency ([AWS Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)). Three compounding failure modes:

- **Thundering herd / retry storm.** When many clients back off to the *same* delay, they re-converge and re-congest. **Jitter** (randomizing the backoff interval) spreads them out and is the single most important fix. Apply jitter to all periodic work, not just retries.
- **Work amplification across layers.** Retrying at every layer of a 5-deep call stack with 3 attempts each multiplies load 3^5 ≈ 243×. Rule: retry at *one* layer (the highest sensible one); lower layers fail fast.
- **Retrying into an overloaded service** prevents recovery. Use a **token bucket** to cap retry budget so retries die out under sustained failure while a healthy baseline is preserved, and only retry when the dependency looks healthy.

### Timeouts & circuit breakers (mechanism + trade-offs)

Set timeouts from the downstream's observed latency distribution (e.g. p99.9) plus network margin — too high and you tie up resources waiting; too low and you abandon requests that would have succeeded and turn a slow dependency into a hard failure ([AWS Builders' Library](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)). A **circuit breaker** trips open after an error threshold so calls fail fast instead of piling onto a sick dependency, then half-opens to probe recovery. **Gotcha:** breakers add a bimodal failure mode (the "open" state) that is exercised only during chaos — AWS argues for caution here, preferring local retry-limiting (token buckets) and static stability over modes you rarely test.

### Control plane vs data plane separation (blast radius)

The **data plane** is the high-volume request path (serving traffic, reading state); the **control plane** is the lower-volume management path (provisioning, config, migrations, topology changes). Separate them so that a control-plane outage cannot take down the data plane — the data plane should keep serving on last-known-good config even when the control plane is down. This is **static stability**: avoid bimodal behavior under failure, pre-distribute the data the data plane needs so it has no hard dependency on the control plane at request time ([AWS Builders' Library: Avoiding fallback](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/)). The 2001 Amazon outage where caches failed and dumped all load onto the database is the cautionary tale: fallback paths that are never exercised become the outage.

**Blast radius** is then contained with cells/regions/phased rollout: change one cell, verify health, proceed — so a bad change can't break everything at once.

### Clock skew & ordering — logical clocks (gotcha)

Physical clocks drift and skew across machines, so you cannot order distributed events by wall-clock timestamp without risking causality violations (this is exactly how last-write-wins loses data). Use **logical clocks** — Lamport clocks give a total order consistent with causality; **vector clocks** detect concurrency (whether two events are causally ordered or genuinely concurrent). Google's Spanner instead bounds clock uncertainty with TrueTime and *waits out* the uncertainty interval to make timestamps safe. **Senior gotcha:** never gate a state-machine transition or a migration cutover on `now()` comparisons across hosts; use sequence numbers / epochs / fencing tokens.

### Safe live migration (mechanism + failure modes)

Migrating a stateful service live requires: (1) strict **sequencing** of steps so invariants hold at every intermediate state; (2) **health gating** between steps — proceed only when the target is healthy and caught up, never on a timer; (3) a **rollback** path at each step; (4) idempotent, re-runnable steps so a retry of a half-done migration is safe; (5) fencing so the old owner stops serving before the new one takes over (prevents split-brain / double-write). The dominant failure mode is cutting over while the target replica is still behind, losing writes — which is why the cutover gates on a consistency/health check, not elapsed time.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through Raft leader election. Why are randomized election timeouts essential, and what specifically prevents two leaders in the same term?</summary>

On losing heartbeats past a randomized timeout, a follower increments the term, becomes a candidate, and requests votes; it wins on a majority. The randomization is what breaks symmetry — without it, all followers would time out together, split the vote, and livelock; with it, one server almost always times out first, wins, and heartbeats before others start. Two leaders can't coexist in one term because a leader needs a majority of votes and any two majorities of N nodes must overlap in at least one node, which would have to vote twice in the same term — impossible. That overlap property is also what guarantees a new leader has seen every committed entry, preventing data loss.

</details>

<details>
<summary><strong>Q:</strong> Why must a Raft/consensus cluster have an odd number of members, and what does cluster size buy you?</summary>

Fault tolerance is "floor(N/2)" failures while retaining a majority. A 3-node cluster tolerates 1 failure; 5 tolerates 2. An even number wastes a node: 4 nodes still tolerate only 1 failure (you need 3 for majority), same as 3, but with more coordination cost and a higher chance of a tied/lost quorum. So odd N maximizes tolerance per node. Larger clusters tolerate more failures but make every commit wait on a larger quorum, raising latency — which is why control planes typically run 3 or 5, not 7+.

</details>

<details>
<summary><strong>Q:</strong> Distinguish linearizability from sequential consistency. Give a concrete case where a system is sequentially consistent but not linearizable.</summary>

Both require all processes to agree on a single total order of operations; linearizability additionally requires that order to respect real time — if A completes before B starts, A precedes B globally, so a read always sees the latest completed write. Sequential consistency drops the real-time constraint: everyone agrees on an order, but it may reorder operations that didn't overlap in wall-clock time. Concrete case: a leader-based store where reads are served from a follower that agrees on the global write order but lags the leader — clients see a consistent order yet a read can return a value older than a write that already completed elsewhere. That stale-but-consistent read is sequential, not linearizable.

</details>

<details>
<summary><strong>Q:</strong> Explain PACELC and why it's more useful than CAP for real systems.</summary>

CAP only describes behavior during a partition (P): you pick availability or consistency. But partitions are rare, so CAP says nothing about the 99.9% of time the system is healthy. PACELC adds the "else" clause: even with no partition, you trade latency (L) against consistency (C), because enforcing linearizability means coordinating (quorum round-trips, leader hops) on the request path. So a store is classified PC/EC (consistent always, slower) or PA/EL (available and fast, eventually consistent). PACELC is more useful because the latency/consistency tension is paid on every request, whereas CAP's choice only surfaces during the rare partition.

</details>

<details>
<summary><strong>Q:</strong> Sync vs async replication — how do you choose, and what's the failure mode of each?</summary>

Synchronous replication acks the client only after a replica confirms, giving RPO≈0 (no committed-write loss on failover) but the slowest replica gates write latency and a replica outage can stall writes entirely. Asynchronous acks immediately and ships in the background — low latency and high availability, but a leader crash loses the un-replicated tail. The usual compromise is semi-synchronous (wait for any one replica). The dangerous combination is async + automatic failover: you promote a replica that was behind, silently lose writes that looked committed to clients, and risk split-brain when the old leader returns. Choose sync for money/state-of-record, async for high-throughput data with a tolerable RPO.

</details>

<details>
<summary><strong>Q:</strong> A service starts cascading: latency climbs, then the whole fleet falls over. You see retries spiking. Diagnose and fix.</summary>

This is a retry storm with work amplification. A dependency slowed down, clients started retrying, and the retries added load that made it slower — a positive feedback loop. If retries exist at multiple layers of the call stack the load multiplies geometrically (3 retries × 5 layers ≈ 243×). Fixes: add jitter to backoff so clients stop re-converging on the same retry instant; cap retries with a token bucket so retry traffic dies out under sustained failure; ensure retries happen at exactly one layer; tighten timeouts off the p99.9 so doomed calls release resources fast; and add a circuit breaker to fail fast while the dependency recovers. Then load-shed at the front to let the dependency drain.

</details>

<details>
<summary><strong>Q:</strong> How do you choose a timeout value, and why is "set it high to be safe" wrong?</summary>

Derive the timeout from the downstream's observed latency distribution — typically p99.9 plus a margin for network variance — not from a round number. A too-high timeout is harmful because resources (threads, connections, memory) stay pinned while the client waits, so during a downstream slowdown you exhaust your own capacity before the timeout ever fires, turning their problem into your outage. A too-low timeout abandons requests that would have succeeded and converts a slow dependency into a hard failure. The right value fails fast enough to protect your resources while not amputating legitimately slow-but-successful calls.

</details>

<details>
<summary><strong>Q:</strong> What is split-brain, how does it cause data loss, and what mechanisms prevent it?</summary>

Split-brain is when a partition or bad failover leaves two nodes both believing they are leader and both accepting writes, producing two divergent histories that can't be cleanly merged — writes on the losing side are lost or conflict. Prevention: require majority-quorum leadership so two disjoint leaders can't both hold a majority (Raft); use fencing tokens — monotonically increasing epoch numbers that the storage layer rejects if stale, so a deposed leader's writes are refused; and STONITH to forcibly stop the old node. The subtle case is automatic failover with async replication, where you promote a lagging replica and the returning old leader then conflicts — fencing plus quorum is the durable answer.

</details>

<details>
<summary><strong>Q:</strong> Why is "exactly-once delivery" a myth, and how do you actually get exactly-once effects?</summary>

Over an unreliable network you can't distinguish a lost request from a lost ack, so the sender must retry, which means at-least-once delivery is the best primitive available; "exactly-once delivery" can't exist. You get exactly-once *effects* by making processing idempotent: a client-supplied idempotency key deduplicated at the server, or operations that are naturally idempotent (PUT desired-state rather than increment). The traps are dedup windows expiring, clients regenerating the key on retry (defeating dedup), and non-idempotent side effects like charging a card — the idempotency must cover the side effect, not just the database row.

</details>

<details>
<summary><strong>Q:</strong> Why can't you order distributed events by wall-clock timestamp, and what do you use instead?</summary>

Physical clocks drift and skew between machines, so two events with timestamps t1 < t2 may actually have happened in the reverse causal order — last-write-wins on wall-clock timestamps silently drops the "earlier" write that was really later. Use logical clocks: Lamport timestamps give a total order consistent with causality, and vector clocks let you detect whether two events are causally ordered or genuinely concurrent (so you can surface conflicts instead of guessing). Spanner takes the other route — TrueTime bounds the uncertainty and the system waits out that interval to make timestamps safe. Operationally, never gate a state transition or migration cutover on cross-host now() comparisons; use sequence numbers, epochs, or fencing tokens.

</details>

<details>
<summary><strong>Q:</strong> Why separate the control plane from the data plane, and what does "static stability" mean here?</summary>

The data plane serves high-volume request traffic; the control plane handles lower-volume management (provisioning, config, topology, migrations). You separate them so a control-plane outage can't take down request serving — the data plane keeps running on last-known-good config with no hard dependency on the control plane at request time. That's static stability: avoid bimodal behavior where the system enters a rarely-tested mode under failure. You achieve it by pre-distributing the data the data plane needs (push, don't pull-on-demand) and by avoiding fallback paths that only fire during chaos — the 2001 Amazon cache-failure outage is the canonical example of a fallback that became the outage.

</details>

<details>
<summary><strong>Q:</strong> Design a control plane for a fleet of stateful services. What are the load-bearing decisions?</summary>

Keep authoritative desired-state in a consensus-backed store (Raft/etcd-style) for linearizable, fenced writes, and keep the data plane off that hot path so control-plane unavailability degrades to "no new changes" rather than "outage." Model everything as desired-state reconciliation with idempotent, re-runnable operations so retries and partial failures self-heal. Contain blast radius with cells/regions and phased rollout — change one cell, gate on health, proceed — never fan a change out globally at once. Use fencing tokens/epochs so a stale actor can't act on old state, version the admin API so you can evolve it without breaking existing callers, and make every mutating workflow observable with explicit guardrails (health checks, automatic halt-and-rollback). The whole thing is static-stability-first: the data plane must survive the control plane being down.

</details>

<details>
<summary><strong>Q:</strong> Design a zero-downtime live migration for a stateful (e.g. Redis-backed) service. How do you sequence it and guarantee safety?</summary>

Decompose into a strict, ordered sequence where every intermediate state preserves invariants, and make each step idempotent so a re-run after a crash is safe. Stand up the target, replicate state to it, and gate the cutover on a health-and-catch-up check — proceed only when the target is verified caught up, never on a timer. Fence the old owner (stop it serving / reject its stale writes via an epoch) before the new owner takes traffic, so you never have two writers — that's the split-brain guard. Keep a rollback path at each step and bake in production guardrails: automated health checks between steps and an automatic halt if a check fails. The dominant failure mode is cutting over to a replica that's still behind and losing writes, which the catch-up gate exists to prevent.

</details>

<details>
<summary><strong>Q:</strong> You built an 8-step automated live-migration workflow for Redis-based state services. Why 8 discrete steps with health checks between them rather than one atomic operation, and where's the split-brain risk?</summary>

Stateful migration can't be atomic — you can't move live in-memory state and shift traffic in a single instant — so you decompose it into ordered steps where each intermediate state is itself valid and recoverable. Discrete steps with health gating let you verify the target is healthy and caught up before each irreversible action and roll back cleanly if a check fails, instead of discovering a half-migrated, inconsistent state. Strict sequencing is what enforces the invariant that the new owner only takes writes after the old owner has been fenced and the state verified, which is exactly the split-brain guard: without that ordering you'd have a window where both the old and new instance accept writes and diverge. The guardrails turn "hope it worked" into "proceed only on proven health, else halt and roll back."

</details>

<details>
<summary><strong>Q:</strong> Your migration cut state-tier capacity 68% (357 cores) across 34 regions in 4 phases. How did the phased rollout limit blast radius, and what would you gate phase advancement on?</summary>

Phasing is blast-radius containment: a bad change touches one phase/region group at a time, so a regression is detected and contained before it can hit all 34 regions — the opposite of a global fan-out that breaks everything at once. You advance phases on observed health and consistency signals (error rates, latency percentiles, replication catch-up, capacity headroom holding under real load), never on elapsed time, because a timer can't tell the difference between "healthy" and "quietly broken." The capacity cut is the payoff of getting the state tier right — denser, correctly-sized state with verified live migration — but the safety comes from sequencing plus per-phase health gating with an automatic halt, so the 68% reduction never trades correctness for density.

</details>

## Say it with your resume

- **Lead with the 8-step Redis live-migration.** "I built an 8-step automated live-migration workflow for Redis-based state services with strict sequencing, health checks between steps, and production guardrails." That's textbook safe stateful migration: ordered idempotent steps, health-gated (not timer-gated) cutover, fencing to prevent split-brain/double-write, and rollback at each step — the exact things a senior interviewer is probing for.
- **Frame the OCI API Gateway work as control-plane vs data-plane separation.** Building control planes for a gateway is precisely the static-stability story: the management path provisions and migrates while the data plane keeps serving on last-known-good config, so control-plane changes never put request traffic at risk.
- **Use the 34-region, 4-phase ARM rollout as blast-radius containment.** Phased, region-by-region rollout with health gating between phases is how you ship a fleet-wide change without a global outage — change a cell, verify, proceed.
- **Use the V2 admin API with parallel V1/V2 migration as a versioning + safe-evolution example.** Running V1 and V2 in parallel during migration is how you evolve a control-plane API without breaking existing callers — the API-contract analogue of zero-downtime migration.
- **Tie the 68.4% state-tier reduction (357 cores) to getting consistency and capacity right under load**, and tenancy-aware provisioning to multi-tenant blast-radius isolation (one tenant's load or failure shouldn't spill into another's).

## Sources

- [In Search of an Understandable Consensus Algorithm (Raft paper)](https://raft.github.io/raft.pdf)
- [Jepsen: Consistency Models](https://jepsen.io/consistency)
- [AWS Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [AWS Builders' Library: Avoiding fallback in distributed systems](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/)
- [PACELC design principle (Abadi, 2012)](https://en.wikipedia.org/wiki/PACELC_design_principle)
