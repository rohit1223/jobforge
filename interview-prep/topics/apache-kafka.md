---
title: Apache Kafka
bucket: tech
learning: true
rank: 8
sources: https://kafka.apache.org/documentation/, https://github.com/apache/kafka
depth: deep
detailed: true
added: 2026-06-12
generated: true
---

> **Learning topic.** Your résumé doesn't yet demonstrate Kafka (you've done control planes, Terraform automation, and Redis state services — adjacent but not streaming). Sensorfact runs Aiven Kafka, so this is a JD gap worth closing. The good news: your distributed-systems fundamentals (replication, quorums, consistency) transfer directly. Frame Kafka answers as "here's how I'd reason about it from first principles," and bridge to your real replication/migration work where honest.

## Core concepts

### Prerequisites — the mental model before the details

Kafka is **not a message queue** in the RabbitMQ sense. It's a **distributed, replicated, append-only commit log** that you read by *offset*, like a file you seek into. This single idea explains almost everything:

- **Producers append; they never overwrite.** A write is appended to the end of a partition's log and gets a monotonically increasing **offset**.
- **Consumers track their own position.** Unlike a queue where the broker deletes a message after delivery, Kafka *retains* messages (by time or size) and each consumer remembers "I've read up to offset N." Two independent consumers can read the same data at different speeds. This is why Kafka is a *streaming platform*, not just a queue — replaying history is a `seek` to an older offset.
- **The log is the source of truth.** Brokers don't track per-message acknowledgments. They track committed offsets and the high watermark. That's far less bookkeeping than a queue, which is why Kafka scales to millions of messages/sec.

**Why this matters:** every senior Kafka question reduces to "it's a replicated log." Ordering, delivery semantics, consumer groups, compaction — all fall out of the log abstraction.

### Topics, partitions, offsets, and ordering (mechanism)

- **Topic** = a named stream of records (e.g., `sensor-readings`). A topic is split into **partitions** for parallelism.
- **Partition** = an ordered, immutable, append-only log. Each record in a partition has a unique **offset** (0, 1, 2, ...).
- **Ordering is guaranteed *only within a partition*, never across partitions.** This is the single most important Kafka fact. If you need all events for `device-42` in order, they must all go to the *same* partition — achieved by setting the **partition key** to `device-42` (Kafka hashes the key → partition: `hash(key) % numPartitions`).
- **Parallelism is bounded by partition count.** A topic with 10 partitions can be consumed by at most 10 consumers in a group working in parallel (an 11th sits idle). Choosing partition count is a capacity decision you can't easily undo — see the gotcha below.

**Failure modes / gotchas.** (1) **Adding partitions breaks key ordering.** `hash(key) % N` changes when `N` changes, so an existing key that mapped to partition 3 might now map to partition 7 — its history is split across two partitions and global per-key order is lost for the transition. Over-provision partitions up front instead. (2) **Hot partitions** — a skewed key (one device producing 90% of traffic) overloads one partition while others idle. No amount of consumers helps; you must re-key or sub-partition. (3) **Null key = round-robin**, which gives even distribution but *no* per-entity ordering.

### Replication, ISR, and the high watermark (mechanism + trade-offs)

A partition is replicated across brokers for durability. One replica is the **leader** (handles all reads/writes); the rest are **followers** that copy the leader's log.

- **In-Sync Replicas (ISR).** The dynamic set of replicas that are "caught up" to the leader. A write is **committed** only once all replicas *in the ISR* have it. A follower that falls behind (slow, partitioned) is dropped from the ISR; it rejoins when it catches up.
- **High watermark.** The offset up to which all ISR members have replicated. Consumers can only read up to the high watermark — never the leader's un-replicated tail. This is what prevents a consumer from reading a record that could be lost on leader failure.
- **Durability math.** With replication factor `f+1` you tolerate `f` failures without data loss, *provided* the ISR stays healthy. Kafka commits when the ISR (not a fixed majority) acks — a cheaper, more flexible quorum than Raft's strict majority, but it depends on `min.insync.replicas` being set correctly.
- **`acks` is the producer's durability dial:**
  - `acks=0` — fire-and-forget. Fastest, can lose data silently. Metrics only.
  - `acks=1` — leader acks before followers replicate. Loses data if the leader dies before a follower copies the write.
  - `acks=all` (a.k.a. `-1`) — leader waits for the *full ISR* to ack. No data loss as long as one ISR member survives. **This is the only safe setting for important data.**

**The critical interaction — `acks=all` + `min.insync.replicas`.** `acks=all` alone is not enough. If the ISR shrinks to just the leader (all followers died), `acks=all` still acks after only the leader has it — you're back to `acks=1` durability silently. Set `min.insync.replicas=2` so that if the ISR drops below 2, the broker *rejects* writes (NotEnoughReplicas) rather than accepting un-durable ones. Replication factor 3 + `min.insync.replicas=2` + `acks=all` is the standard durable config: tolerate one broker loss, refuse writes on two.

### Delivery semantics: at-most / at-least / exactly-once (the headline trade-off)

Kafka's default is **at-least-once**. The others are deliberate choices:

- **At-most-once.** Disable producer retries; commit consumer offset *before* processing. A crash mid-processing loses the message but never duplicates it. Use for metrics/telemetry where loss is acceptable but dupes corrupt aggregates.
- **At-least-once (default).** Producer retries on failure; consumer commits offset *after* processing. A crash after processing but before commit causes reprocessing → duplicates. The standard choice — you make consumers **idempotent** to tolerate the dupes.
- **Exactly-once (EOS).** Achieved via two mechanisms working together:
  1. **Idempotent producer** (`enable.idempotence=true`) — the producer tags each record with a producer ID + sequence number, so the broker deduplicates retries. This eliminates duplicates *from producer retries* within a partition.
  2. **Transactions** (`transactional.id` set) — the producer atomically writes output records *and* the consumer's committed offset in one transaction. If the transaction aborts, both roll back: the output becomes invisible to `read_committed` consumers and the offset reverts. This gives exactly-once for the **consume → process → produce** loop (the Kafka Streams pattern).

**Gotchas.** (1) EOS is exactly-once *within Kafka* (Kafka topic → Kafka topic). The moment you write to an external system (Postgres, S3), you're back to needing idempotency or 2-phase commit at that boundary — Kafka can't make a REST call exactly-once. (2) Transactions add latency and require `read_committed` consumers, which only see committed records (they buffer until the transaction commits). (3) One producer per consumer instance is the simplest transactional setup; sharing producers across threads complicates fencing during rebalances.

### Consumer groups and rebalancing (mechanism + failure modes)

- **Consumer group** = a set of consumers that *cooperatively* divide a topic's partitions. Each partition is consumed by exactly one member of the group. Add a consumer → partitions redistribute (scale out); remove one → its partitions reassign (fault tolerance).
- **Rebalancing** is the redistribution. Triggered by: a consumer joining/leaving, a consumer timing out (missed heartbeat), or partition count changing.
- **The stop-the-world problem (eager rebalancing).** Classic rebalancing revokes *all* partitions from *all* consumers, then reassigns from scratch. During this window, **the whole group stops consuming** — a latency/throughput cliff. A flapping consumer (slow GC, deploy churn) can cause repeated rebalances that starve the group.
- **Cooperative (incremental) rebalancing** — the modern protocol (`CooperativeStickyAssignor`). Only the partitions that *need* to move are revoked; everyone else keeps consuming. This eliminates most of the stop-the-world pain and is the recommended assignor for production.
- **Offset commit.** Consumers commit their position to the internal `__consumer_offsets` topic. **Auto-commit (`enable.auto.commit=true`) is a footgun** — it commits on a timer regardless of whether you finished processing, so a crash can either lose messages (committed before processing) or the timing creates duplicates. Senior practice: **manual commit after processing**, ideally batched.

**Consumer lag** = `log-end-offset − committed-offset` per partition: how far behind the consumer is. The #1 Kafka health metric. Growing lag means consumers can't keep up — scale out consumers (up to partition count), speed up processing, or add partitions. Monitor it with `kafka-consumer-groups.sh --describe` or Burrow/exporter.

### Retention vs log compaction (mechanism + trade-offs)

Two ways Kafka reclaims space — they answer different needs:

- **Time/size retention** (`log.retention.hours`, `log.retention.bytes`). Delete whole log **segments** older than the threshold. The default. Kafka is "delete after 7 days" by default — it's an event log, not infinite storage.
- **Log compaction** (`cleanup.policy=compact`). Retain *at least the last value for each key*, deleting older values for the same key. The log becomes a **changelog / snapshot** of latest-state-per-key. Used for: restoring application state after a crash, the `__consumer_offsets` topic itself, and CDC/materialized-view use cases.
  - **Tombstones.** To *delete* a key under compaction, produce a record with that key and a **null payload**. Compaction removes all prior values for the key, then removes the tombstone itself after `delete.retention.ms`. Forget the tombstone-cleanup window and downstream caches that missed the delete never learn the key is gone.

**Gotcha.** Compaction guarantees *eventual* latest-value-per-key, not immediate — the cleaner runs in the background, so the log head (uncompacted) can still hold duplicate keys. Consumers reading from offset 0 must handle seeing multiple values per key and taking the last.

### Why Kafka is fast: zero-copy, page cache, sequential I/O (mechanism)

Senior interviewers love this because it reveals whether you understand the OS, not just the API.

- **Sequential disk I/O.** Appending to a log is sequential, which on spinning disks *and* SSDs is dramatically faster than random I/O — often faster than random *memory* access patterns. Kafka leans on this: it never updates in place.
- **Page cache, not a JVM heap cache.** Kafka stores almost nothing in the JVM heap; it lets the OS page cache hold recent data. Reads from caught-up consumers hit the page cache → no disk seek. This also means restarting a broker doesn't cold-start a cache (the OS page cache survives).
- **Zero-copy (`sendfile`).** To serve a consumer, Kafka uses `sendfile()` to copy bytes straight from the page cache to the network socket — bypassing user space entirely. Data is copied into the page cache once (on produce) and reused for every consumer with no further user-space copies. A caught-up consumer is served at near-NIC line rate with zero disk reads.
- **Batching + compression.** Producers batch records (`linger.ms` waits a few ms to fill a batch; `batch.size` caps it) and compress the whole batch (lz4/zstd/snappy). Compression is applied to the *record batch*, so it amortizes far better than per-message. The batch stays compressed on disk and over the wire — the broker doesn't decompress.

**Tuning knobs that matter.** `linger.ms` (latency vs throughput — higher fills bigger batches), `batch.size`, `compression.type` (zstd for ratio, lz4 for speed), `acks`/`min.insync.replicas` (durability), `fetch.min.bytes`/`fetch.max.wait.ms` (consumer-side batching), and partition count (parallelism ceiling).

### KRaft vs ZooKeeper (architecture, current state)

- **Old world:** Kafka used **ZooKeeper** for cluster metadata (broker membership, topic configs, controller election). A separate system to run, scale, and reason about — and a scaling bottleneck for clusters with many partitions.
- **KRaft (Kafka Raft).** Kafka 3.x+ replaced ZooKeeper with a built-in Raft-based metadata quorum (`KRaft`). Metadata lives in an internal Kafka log managed by **controller** nodes. As of Kafka 4.0, ZooKeeper is removed — KRaft is the only mode. Benefits: one system to operate, faster controller failover, and metadata that scales to millions of partitions.
- **Why it's asked:** it signals whether you've kept current. The senior point is that metadata is now *itself a replicated log* — Kafka eating its own dog food.

---

## Interview questions

<details>
<summary><strong>Q:</strong> A consumer needs all events for a given user processed in order. How do you guarantee that across a topic with 50 partitions?</summary>

Set the **partition key** to the user ID. Kafka routes records via `hash(key) % numPartitions`, so all events for one user land on the same partition, and **ordering is guaranteed within a partition**. Different users spread across partitions for parallelism.

The trap is that ordering is *only* per-partition — there is no global order across the topic. And if you later **add partitions**, `hash(key) % N` changes: a user that mapped to partition 12 may now map to 30, splitting their history. So you over-provision partitions up front (you can't easily reduce them either). If a single user is a hot key (90% of traffic), even one partition becomes a bottleneck — then you re-key (e.g., `userId:bucket`) and accept ordering only within a sub-stream, or redesign so strict ordering isn't required.

</details>

<details>
<summary><strong>Q:</strong> Walk me through what "exactly-once" actually means in Kafka, and where it breaks.</summary>

It's two mechanisms. **(1) Idempotent producer** (`enable.idempotence=true`): each record carries a producer ID + sequence number, so the broker dedupes producer *retries* within a partition — this kills duplicates from "I sent, didn't get the ack, resent." **(2) Transactions** (`transactional.id`): the producer atomically writes output records *and* the source consumer's committed offset in one transaction. On abort, both roll back — the output is invisible to `read_committed` consumers and the offset reverts. Together they give exactly-once for the **consume→process→produce** loop, which is what Kafka Streams uses.

Where it breaks: it's exactly-once *within Kafka* (topic→topic). The instant you write to an external system — Postgres, S3, a REST API — Kafka can't make that side effect transactional. You're back to needing an idempotent write (upsert by key, dedup table) or a transactional outbox at that boundary. EOS also costs latency and forces `read_committed` consumers, which buffer until commit. So "exactly-once" is real but narrowly scoped — most production pipelines run **at-least-once + idempotent consumers** because it's simpler and the external boundary needs idempotency anyway.

</details>

<details>
<summary><strong>Q:</strong> `acks=all` is set but you still lost data on a broker failure. How is that possible?</summary>

`acks=all` waits for the full **ISR** (in-sync replicas) to ack — but if the ISR has shrunk to *just the leader* (all followers fell behind or died), then "all of the ISR" is one node, and you're getting `acks=1` durability silently. The leader acks, then dies before any follower catches up, and the write is gone.

The fix is `min.insync.replicas`. Set it to 2 (with replication factor 3): if the ISR drops below 2, the broker **rejects** the write with `NotEnoughReplicas` instead of accepting an un-durable one. That converts a silent data-loss window into a loud, visible produce failure you can handle (retry, backpressure). The canonical durable config is **RF=3, min.insync.replicas=2, acks=all** — survive one broker loss, refuse writes on two. The lesson: `acks=all` is necessary but not sufficient; durability is `acks` *and* the ISR floor together.

</details>

<details>
<summary><strong>Q:</strong> Your consumer group's lag is climbing steadily. Walk me through diagnosis and remediation.</summary>

Lag = `log-end-offset − committed-offset` per partition — the consumer is falling behind producers. First, **locate it**: `kafka-consumer-groups.sh --describe --group X` shows lag per partition. Is it *all* partitions (global under-provisioning) or *one* (hot partition / stuck consumer)?

Causes and fixes:
- **Under-provisioned consumers** — add consumers, but only up to the partition count (an 11th consumer on a 10-partition topic idles). If already at the ceiling, you must add partitions (and accept the key-rebalance cost).
- **Slow processing** — the consumer's per-record work (a slow DB write, an external API) is the bottleneck. Batch the writes, parallelize processing off the poll thread, or async the downstream.
- **Hot partition** — one partition has far more data (skewed key). Re-key to spread load.
- **Rebalance storms** — a flapping consumer triggers repeated rebalances that stall the group. Check for GC pauses / deploy churn; raise `session.timeout.ms`, switch to cooperative rebalancing.
- **A poison message** — one record throws repeatedly, the consumer never commits, lag on that partition grows unbounded. Add a dead-letter topic and skip-after-N-retries.

The senior move is to alert on lag *trend*, not absolute value — steady-state lag is fine; *growing* lag means capacity is losing the race.

</details>

<details>
<summary><strong>Q:</strong> What's the difference between a rebalance that stops the world and one that doesn't?</summary>

**Eager rebalancing** (the old default) revokes *all* partitions from *all* consumers, then reassigns from scratch. During that window the entire group stops consuming — a throughput cliff. If a consumer flaps (slow GC, rolling deploy), you get repeated eager rebalances and the group spends more time rebalancing than working.

**Cooperative (incremental) rebalancing** (`CooperativeStickyAssignor`) only revokes the *specific* partitions that need to move; every consumer keeps processing the partitions it's retaining. A single consumer joining might move just 2 of 50 partitions, and the other 48 never pause. It's the recommended assignor for production. The trade-off is it may take two rebalance rounds to converge (revoke, then assign), but it trades a small coordination delay for eliminating the global stall. The deeper lesson: rebalances are unavoidable, so you minimize their *blast radius*, and you keep consumers from flapping (tune `session.timeout.ms`, `max.poll.interval.ms`, fix GC).

</details>

<details>
<summary><strong>Q:</strong> Explain log compaction. When would you use it instead of normal retention, and what's the tombstone gotcha?</summary>

Normal retention deletes whole segments older than a time/size threshold — Kafka as a 7-day event log. **Compaction** (`cleanup.policy=compact`) instead retains *at least the last value for each key*, deleting older values for the same key. The log becomes a **changelog / snapshot of latest-state-per-key** rather than a time window.

Use it when the log represents *current state*, not a sequence of events: rebuilding a cache or materialized view from the topic, the `__consumer_offsets` topic itself, CDC streams where you only need the latest row version. A new consumer can replay from offset 0 and reconstruct the full current state, with old versions already pruned.

The tombstone gotcha: to *delete* a key you produce a record with that key and a **null payload** — a tombstone. Compaction removes all prior values for the key, then removes the tombstone *itself* after `delete.retention.ms`. If a downstream consumer is offline longer than that window, it can miss the tombstone entirely and never learn the key was deleted — its cache keeps a ghost entry. So `delete.retention.ms` must exceed your worst-case consumer downtime. Also, compaction is eventual: the uncompacted log head can still hold duplicate keys, so consumers must take the *last* value per key, not assume uniqueness.

</details>

<details>
<summary><strong>Q:</strong> Why is Kafka so fast? Explain it at the OS level.</summary>

Three things, all OS-level:

**(1) Sequential I/O.** Kafka only ever *appends* to a log — never random writes. Sequential disk access (even on SSD) is orders of magnitude faster than random, so Kafka turns the disk's worst case into its best case.

**(2) Page cache instead of a heap cache.** Kafka keeps almost nothing in the JVM heap; it relies on the OS page cache to hold recent log data. Caught-up consumers read from the page cache, not disk — and the cache survives a broker process restart, so there's no cold-start. It also sidesteps JVM GC pressure from a giant on-heap cache.

**(3) Zero-copy via `sendfile()`.** To serve a consumer, Kafka tells the kernel to copy bytes directly from the page cache to the network socket, bypassing user space — no copy into the JVM, no copy back out. Data is paged in once on produce and reused for every consumer at near-NIC line rate. Add producer-side **batching + batch compression** (lz4/zstd applied to the whole record batch, stored and shipped compressed without broker decompression) and you have a system whose throughput is bounded by the network, not the CPU or disk.

</details>

<details>
<summary><strong>Q:</strong> A team wants to use Kafka as a request/response RPC mechanism. Talk them out of it (or into it).</summary>

Kafka is a poor fit for synchronous request/response. It's a *log*: optimized for high-throughput, ordered, replayable streaming with consumers tracking offsets — not for low-latency point-to-point correlation. To do RPC you'd need a reply topic, a correlation ID per request, and a consumer scanning for *your* response among everyone's — you've rebuilt a worse message bus with higher latency (batching's `linger.ms`, consumer poll loops) and no natural request timeout.

When Kafka *is* right: the interaction is genuinely event-driven — fire an event, one or many consumers react asynchronously, and you don't need an immediate correlated reply. Order processing, audit logs, CDC, metrics pipelines, fan-out to multiple independent consumers (each with its own offset). The tell is whether the producer needs to *block on a specific reply* (use gRPC/HTTP + a queue like SQS/RabbitMQ for work distribution) versus *emit a fact others consume* (Kafka). For Sensorfact's IoT readings — high-volume, multiple consumers, replayable — Kafka fits; for "create user and tell me the ID," it doesn't.

</details>

<details>
<summary><strong>Q:</strong> How does Kafka decide a write is "committed," and how does that compare to Raft's majority quorum?</summary>

Kafka commits a write once **all replicas in the ISR** (in-sync replicas) have appended it — and consumers can only read up to the **high watermark**, the offset all ISR members have reached. The ISR is *dynamic*: a follower that falls behind is ejected and rejoins when caught up. So the "quorum" isn't a fixed majority — it's whoever is currently in sync, floored by `min.insync.replicas`.

Versus Raft: Raft commits when a **strict majority** (⌊N/2⌋+1) acks, and any majority overlaps any other majority, which is what guarantees a new leader has all committed entries. Kafka's ISR model is more flexible and can be cheaper (you might commit with fewer than a majority if the ISR is small, or wait for more than a majority if all replicas are in sync), but it shifts the safety burden onto `min.insync.replicas`: set it too low (or leave it at 1) and the ISR can shrink to a single node, breaking the durability you thought RF gave you. Raft bakes the quorum into the protocol; Kafka makes it a tunable, which is more powerful and more foot-gun-prone. (Notably, Kafka's *own* metadata layer, KRaft, uses actual Raft — so it runs both models.)

</details>

<details>
<summary><strong>Q:</strong> You set `enable.auto.commit=true` and now you're seeing both duplicate processing AND occasional lost messages. Why?</summary>

Auto-commit commits the consumer's offset on a **timer** (`auto.commit.interval.ms`, default 5s), decoupled from whether you actually finished processing. That creates two opposite failures depending on timing:

- **Lost messages:** the timer fires and commits offset N right after `poll()` returns records up to N but *before* you've processed them. The consumer crashes mid-processing — on restart it resumes from N, skipping the un-processed records. They're gone.
- **Duplicates:** you process records up to N, but the consumer crashes *before* the next auto-commit tick. On restart it resumes from the last committed offset (< N) and reprocesses everything since.

The fix is **manual commit after processing** (`enable.auto.commit=false`, then `commitSync()`/`commitAsync()` once the work is durably done). That converts the semantics to clean at-least-once: you only ever reprocess (duplicates), never skip (loss) — and you make consumers idempotent to absorb the duplicates. Auto-commit's convenience is exactly what makes it unsafe: it commits *time*, not *progress*.

</details>

<details>
<summary><strong>Q:</strong> How do you choose the number of partitions for a topic, and why is it hard to change later?</summary>

Partition count is your **parallelism ceiling**: a consumer group can have at most one consumer per partition doing useful work, so 10 partitions caps you at 10 parallel consumers. You size it from target throughput: estimate per-partition throughput (producer batching, consumer processing speed) and divide your peak target by it, then add headroom. More partitions also means more open file handles, more replication overhead, and longer leader-election/rebalance times — so it's not free to over-provision wildly.

It's hard to change because **increasing partitions changes `hash(key) % N`**, which re-routes existing keys to different partitions. Per-key ordering breaks across the change, and Kafka doesn't redistribute existing data — old records stay where they were. *Decreasing* partitions isn't supported at all (you'd lose data / order). So the practical guidance: over-provision moderately at creation (it's the cheap direction), pick a count with growth headroom for a couple of years, and if you truly must grow, do it during a maintenance window with awareness that in-flight per-key ordering is sacrificed for the transition.

</details>

<details>
<summary><strong>Q:</strong> What is ISR shrinking, what causes it, and why should you care?</summary>

The ISR (in-sync replica set) shrinks when a follower can't keep up with the leader — it's missed replicating for longer than `replica.lag.time.max.ms`, so the leader ejects it. The partition keeps working (the leader and remaining ISR members still serve), but your effective replication factor just dropped. If the ISR shrinks to 1 (just the leader), you've silently lost redundancy: an `acks=all` write now commits with only the leader, and a leader failure = data loss.

Causes: a slow/overloaded follower broker (disk saturation, GC), network issues between brokers, or the leader producing faster than followers can fetch (under-provisioned cluster). Why care: ISR shrink is the leading indicator of a durability incident. You monitor `UnderReplicatedPartitions` and `IsrShrinksPerSec` — a sustained nonzero value means writes are at risk. Combined with `min.insync.replicas=2`, a shrink below 2 starts *rejecting* writes, which is loud and recoverable; without that floor, the shrink is silent and you only find out when a broker dies and data is gone.

</details>

<details>
<summary><strong>Q:</strong> Compare Kafka to a traditional message queue (RabbitMQ/SQS). When would you pick each?</summary>

The core difference: a queue **deletes** a message once it's delivered/acked (the broker tracks per-message state), while Kafka **retains** the log and consumers track their own offset. That single distinction drives everything.

Pick **Kafka** when: you need high throughput (millions/sec), multiple independent consumers of the same stream (each at its own position), replay/reprocessing (rewind to an old offset), ordered per-key streams, or a durable event log that's the source of truth. IoT telemetry, CDC, event sourcing, analytics pipelines.

Pick a **queue** when: you need competing-consumers work distribution with per-message ack/redelivery, complex routing (RabbitMQ exchanges/bindings), priority queues, per-message TTL, or low-latency request/response-ish task dispatch. A job queue where each task is consumed once and then gone, and you want dead-letter + redelivery semantics out of the box. Queues also handle "I need to delete/nack a specific message" naturally, which Kafka can't — Kafka only moves offsets. For Sensorfact, the high-volume replayable sensor stream is Kafka's wheelhouse; a "send this email" task queue would be better on SQS/RabbitMQ.

</details>

<details>
<summary><strong>Q:</strong> (Experience) You haven't run Kafka in production. How would you ramp up and de-risk adopting it?</summary>

*(Honesty question — interviewers respect a calibrated answer over bluffing.)*

I'd be straight that my streaming exposure is adjacent, not direct: I've built replicated state services (Redis live-migration with strict sequencing, health checks, and guardrails) and control planes, so the *distributed-systems* reasoning — replication, quorums, leader election, durability vs latency trade-offs — transfers directly. Kafka's ISR/high-watermark model is a variation on the replication problems I've already operated.

To de-risk adoption: (1) start as a *consumer* on a non-critical topic to learn the operational surface — lag monitoring, rebalance behavior, offset management — before owning a producer path. (2) Lean on managed Kafka (Sensorfact uses Aiven) so I'm not running brokers/KRaft myself on day one, and focus on getting `acks`/`min.insync.replicas`/idempotency right at the application layer, which is where most data-loss bugs actually live. (3) Build a small spike: produce with `acks=all`, consume with manual commits, deliberately kill a broker and a consumer to *see* the failure modes (ISR shrink, rebalance stall, duplicate on replay) rather than read about them. The principle I'd carry over from the migration work: instrument first, gate cutovers on health checks, and make the consumer idempotent so at-least-once is safe by construction.

</details>

---

## Say it with your resume

You can't claim Kafka experience — instead, **bridge from adjacent strengths** and be honest about the gap:

- **Replication & durability reasoning** → *"I've operated replicated state services and reasoned about sync-vs-async replication and failover safety. Kafka's ISR + high-watermark model is the same problem space — committed-once-replicated, read-only-up-to-the-watermark — so `acks=all` + `min.insync.replicas` maps onto durability trade-offs I've made before."* (Ties to: **Redis-based state services, 8-step live-migration with strict sequencing and health checks**.)
- **Migration/cutover discipline** → *"My migration work gated every cutover on health checks rather than timers, with production guardrails. I'd apply the same to consumer cutovers and partition changes — instrument lag, verify before advancing."* (Ties to: **68.4% capacity cut via sequenced live-migration**.)
- **Automation over tickets** → *"I replaced ticket-driven dependencies with Terraform automation. I'd treat Kafka topic/ACL/partition config as code, not console clicks."* (Ties to: **30 days → 8 hours API Gateway build via Terraform automation**.)
- **Honest framing** → for any Kafka question you can't answer from experience, reason from first principles ("it's a replicated log") and say where your direct knowledge ends. Senior interviewers test calibration, not bluffing.

> See also [[distributed-systems]] (replication, quorums, consistency) and [[reliability-incident]] for the operational mindset, and [[redis-and-caching]] for the state-service work you'll bridge from.

---

## Sources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Kafka Design: Replication, ISR, Delivery Semantics](https://kafka.apache.org/documentation/#design)
- [Message Delivery Semantics & Exactly-Once](https://kafka.apache.org/documentation/#semantics)
- [Log Compaction](https://kafka.apache.org/documentation/#compaction)
- [Consumer Groups & Rebalancing](https://kafka.apache.org/documentation/#impl_consumer)
- [Basic Kafka Operations (consumer-groups, partitions)](https://github.com/apache/kafka/blob/trunk/docs/operations/basic-kafka-operations.md)
- [KRaft / Eligible Leader Replicas](https://github.com/apache/kafka/blob/trunk/docs/operations/eligible-leader-replicas.md)
