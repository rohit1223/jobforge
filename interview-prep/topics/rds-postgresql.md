---
title: RDS PostgreSQL
bucket: tech
learning: true
rank: 9
sources: https://www.postgresql.org/docs/17/, https://docs.aws.amazon.com/AmazonRDS/
depth: standard
detailed: true
added: 2026-06-12
generated: true
---

> **Learning topic (light).** Your résumé lists **SQL** and you ran **MySQL** under the Pega/OpenShift containerization work — so relational fundamentals transfer, but PostgreSQL's MVCC/vacuum model and RDS-managed specifics (Multi-AZ, parameter groups, PITR) are new ground. Sensorfact runs **RDS PostgreSQL** as its primary database. Bridge from your SQL + infra-automation strengths; be honest where Postgres internals are the gap. Two layers here: **(a) the Postgres engine** (MVCC, indexes, planner, isolation) and **(b) RDS as a managed wrapper** (HA, backups, connection limits, tuning via parameter groups).

## Core concepts

### Prerequisites — the relational + managed-service mental model

Two things to hold in your head separately:

1. **PostgreSQL the engine** is an ACID, MVCC relational database. The defining trait vs MySQL: Postgres keeps **multiple versions of every row** and cleans them up later (VACUUM), rather than updating in place. Almost every Postgres-specific gotcha (bloat, vacuum, wraparound, long-transaction pain) descends from this one design choice.
2. **RDS** is AWS managing that engine for you: it provisions the instance, handles backups + point-in-time recovery, runs Multi-AZ failover, exposes tuning through **parameter groups** (you don't edit `postgresql.conf` directly), and meters connections/storage/IOPS. You trade `root`/superuser and OS access for not having to operate the box. The senior framing: **RDS removes ops toil but not the need to understand the engine** — a bad query plan or a vacuum stall is still your problem.

### MVCC — multi-version concurrency control (the signature concept)

PostgreSQL uses **MVCC**: readers never block writers and writers never block readers, because each transaction sees a **snapshot** of the data as it existed at a point in time, not the live state ([PG docs: MVCC](https://www.postgresql.org/docs/17/mvcc-intro.html)).

- **How it works.** Every row version (tuple) carries hidden system columns `xmin` (the transaction ID that created it) and `xmax` (the transaction that deleted/superseded it). A transaction's snapshot determines which versions are *visible*: a tuple is visible if its `xmin` committed before the snapshot and its `xmax` hasn't committed (or is null). An `UPDATE` doesn't overwrite — it writes a **new tuple** and marks the old one's `xmax`. A `DELETE` just sets `xmax`. The old versions linger until cleanup.
- **The consequence: dead tuples and bloat.** Those superseded versions are **dead tuples**. They occupy disk and index space until **VACUUM** reclaims them. A table that's heavily updated/deleted accumulates bloat; queries get slower because they scan dead rows and indexes point at them.
- **Worked example.**
  ```sql
  -- txn A
  BEGIN;
  SELECT balance FROM accounts WHERE id = 1;  -- sees 100, snapshot taken
  -- txn B (concurrent) commits:  UPDATE accounts SET balance = 50 WHERE id = 1;
  SELECT balance FROM accounts WHERE id = 1;  -- txn A STILL sees 100 (its snapshot)
  COMMIT;
  -- now a new txn sees 50; the old "100" tuple is dead, awaiting VACUUM
  ```

### VACUUM, autovacuum, and transaction ID wraparound (the operational heart)

- **VACUUM** reclaims dead tuples so their space can be reused, and updates the visibility map and statistics. **Autovacuum** (on by default) runs it automatically when a table's dead-tuple ratio crosses a threshold ([PG docs: routine vacuuming](https://www.postgresql.org/docs/17/routine-vacuuming.html)).
- **`VACUUM` vs `VACUUM FULL`.** Plain VACUUM marks space reusable *in place* (no exclusive lock, doesn't shrink the file). `VACUUM FULL` rewrites the whole table to reclaim disk back to the OS but takes an **ACCESS EXCLUSIVE lock** (blocks all reads + writes) — a production outage if run on a large hot table. Senior answer: avoid `VACUUM FULL`; use `pg_repack` for online compaction.
- **Transaction ID wraparound — the database-killer.** XIDs are 32-bit and *wrap around* at ~4 billion. To keep old rows visible forever, VACUUM **freezes** tuples (marks them as "infinitely old"). If autovacuum can't keep up and the oldest unfrozen XID approaches the wraparound limit, Postgres goes into emergency: first warnings, then it **refuses new writes** to protect data. This has taken down major sites (Sentry's famous outage). On RDS you monitor `MaximumUsedTransactionIDs` in CloudWatch.
- **What stalls autovacuum (the gotchas):** (1) **long-running transactions / idle-in-transaction** hold back the "oldest snapshot," so VACUUM can't remove tuples newer than that — bloat grows unbounded. (2) **Replication slots** that aren't consumed pin the WAL and the xmin horizon similarly. (3) Aggressive write rate outpacing autovacuum's (throttled) speed — tune `autovacuum_vacuum_cost_limit` / scale factor.

### Indexes and the query planner (mechanism + tuning)

PostgreSQL offers several index types, each tuned for a query shape ([PG docs: index types](https://www.postgresql.org/docs/17/indexes-types.html)):

- **B-tree** (default) — equality and range (`=`, `<`, `>`, `BETWEEN`, `ORDER BY`). 90% of indexes.
- **GIN** — "many values per row": full-text search, `jsonb` containment, array membership. Inverted index.
- **GiST / SP-GiST** — geometric, range types, nearest-neighbor, fuzzy search.
- **BRIN** — huge append-only tables where values correlate with physical order (time-series): tiny index, stores min/max per block range. Perfect for IoT/sensor time-series (relevant to Sensorfact).
- **Hash** — equality only; rarely worth it over B-tree.

**Specialized B-tree tricks (senior-level):**
- **Composite index column order matters.** An index on `(i1, i2, i3)` can serve a query on `i1` or `i1,i2` but **not** `i2` alone (the leading-column rule). Worked example from the docs: a query filtering on the *non-leading* columns `i2 AND i5` of a 6-column index falls back to a **350ms seq scan**, whereas separate single-column indexes let the planner combine them with **BitmapAnd in 0.05ms**. Lesson: order composite columns by the queries you actually run; sometimes several narrow indexes beat one wide one.
- **Partial index** — `CREATE INDEX ... WHERE status = 'active'` indexes only the rows you query, smaller + faster.
- **Covering index** — `INCLUDE (cols)` lets an **index-only scan** answer the query without touching the heap.

**Reading EXPLAIN (the must-have skill).** `EXPLAIN ANALYZE` shows the actual plan + timings. What to look for:
- **Seq Scan on a big table** in a selective query → missing/unusable index.
- **`rows` estimate wildly off from actual** → stale statistics; run `ANALYZE` (autovacuum also does this). Bad estimates → bad plans (wrong join order, hash vs nested loop).
- **Nested Loop with high loops count** → often a missing index on the inner side.
- **`Rows Removed by Filter` huge** → the index isn't selective enough or a partial/expression index would help.

### Transaction isolation levels (trade-offs)

The SQL standard defines four; Postgres implements three distinct behaviors (it never allows dirty reads) ([PG docs: transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html)):

- **Read Committed** (default) — each *statement* sees a fresh snapshot of committed data. Prevents dirty reads. Allows **non-repeatable reads** (re-running a SELECT in the same txn can see new committed values) and **phantoms**. Fine for most OLTP.
- **Repeatable Read** — the *whole transaction* uses one snapshot taken at first statement. Prevents non-repeatable reads and (in Postgres) phantoms. Concurrent conflicting updates fail with a **serialization error** you must retry.
- **Serializable** — strongest; via **SSI (Serializable Snapshot Isolation)** Postgres detects dangerous read/write dependency cycles and aborts one transaction so the result equals *some* serial order. No locks taken for reads, but you **must handle `40001` serialization failures with retry logic**.

**Senior point:** higher isolation pushes the burden onto your app (retry loops) and reduces concurrency. Default Read Committed + explicit row locks (`SELECT ... FOR UPDATE`) where you need them is the common pragmatic choice.

### WAL, replication, and RDS high availability (mechanism)

- **WAL (Write-Ahead Log).** Every change is written to the WAL *before* the data files — this is what makes Postgres crash-safe (replay the WAL on recovery) and is the substrate for replication, backups, and PITR.
- **Streaming (physical) replication.** A standby connects to the primary and receives WAL records as they're generated, replaying them — asynchronous by default, so a standby lags the primary by a small delay ([PG docs: streaming replication](https://www.postgresql.org/docs/17/warm-standby.html)). Monitor lag via `pg_stat_replication` (`replay_lag`, `write_lag`).
- **Logical replication.** Decodes WAL into logical change events (insert/update/delete per row) via publications/subscriptions — used for selective replication, major-version upgrades, and CDC to other systems. Requires `wal_level = logical`.

**RDS maps these to managed features:**
- **Multi-AZ (HA, not scaling).** A *synchronous* standby in another AZ. On primary failure RDS **automatically fails over** (DNS CNAME flips, typically 60–120s). The standby is **not readable** — Multi-AZ is for durability/availability, *not* read scaling. (Multi-AZ DB *cluster* with readable standbys is a newer variant.)
- **Read replicas (scaling).** *Asynchronous* replicas you can route read traffic to. They lag (monitor `ReplicaLag`), so reads can be stale — never serve read-your-own-write flows from a replica without care. Can be promoted to standalone (manual failover / region migration).
- **Backups + PITR.** Automated daily snapshots + continuous WAL archiving let you restore to any second within the retention window (point-in-time recovery). The restore creates a *new* instance — it's not an in-place rollback.

### RDS-specific operational knobs (the managed-service layer)

- **Parameter groups.** You tune Postgres via RDS parameter groups, not `postgresql.conf`. Some params are **static** (require a reboot), others **dynamic**. Key ones: `shared_buffers` (~25% of RAM, RDS sets a default), `work_mem` (per-sort/hash — *per operation per connection*, so it multiplies; too high + many connections = OOM), `max_connections` (scales with instance size).
- **Connections are scarce — use a pooler.** Each Postgres connection is a **separate OS process** with real memory overhead; a few hundred is a lot. Apps that open a connection per request exhaust `max_connections` fast. Fix: a pooler — **RDS Proxy** (managed) or **PgBouncer** — in transaction-pooling mode to multiplex many clients onto few backend connections. This is the #1 RDS Postgres scaling lesson.
- **Storage + IOPS.** RDS storage is EBS; you provision IOPS (gp3/io1) or rely on burst. Autovacuum, large index builds, and `VACUUM FULL` all generate IO that can hit the IOPS ceiling and stall everything.
- **What you give up:** no superuser, no OS shell, limited extension set (only RDS-approved extensions), and you patch on AWS's maintenance-window schedule.

---

## Interview questions

<details>
<summary><strong>Q:</strong> Explain MVCC in Postgres and why a heavily-updated table gets slow over time.</summary>

Under MVCC, an `UPDATE` doesn't overwrite a row — it writes a **new tuple** and marks the old version's `xmax` so it's invisible to new transactions. Each transaction reads from a **snapshot**, so readers and writers never block each other. The cost is **dead tuples**: every update/delete leaves a superseded version occupying heap and index space until **VACUUM** reclaims it.

A heavily-updated table accumulates these dead tuples (**bloat**). Queries slow down because sequential and index scans must wade through dead rows, indexes grow with dead pointers, and the table's physical size balloons even if the live row count is flat. The fix is healthy autovacuum; the trap is anything that stalls it — long-running transactions, idle-in-transaction sessions, or unconsumed replication slots — which pin the xmin horizon and prevent VACUUM from removing tuples, so bloat grows unbounded. The senior tell is connecting "table got slow" → "bloat" → "what's holding back the oldest snapshot."

</details>

<details>
<summary><strong>Q:</strong> Your RDS instance suddenly refuses writes with a wraparound warning. What happened and how do you recover?</summary>

Transaction ID wraparound. XIDs are 32-bit and wrap at ~4 billion. To keep old rows permanently visible, VACUUM must **freeze** old tuples (mark them as infinitely old). If autovacuum falls far enough behind that the oldest unfrozen XID approaches the wraparound limit, Postgres enters emergency mode: it warns, then **stops accepting writes** to avoid silently corrupting visibility. On RDS you'd have seen `MaximumUsedTransactionIDs` climbing in CloudWatch beforehand.

Recovery: the database is still readable; you need to let an aggressive (anti-wraparound) VACUUM complete to freeze the old tuples and advance `relfrozenxid`. Find the tables with the oldest `relfrozenxid` (`age(relfrozenxid)`) and vacuum them, ideally with more cost budget so it actually makes progress. Then root-cause *why* autovacuum fell behind — almost always a long-running/idle-in-transaction session or an abandoned replication slot pinning the xmin horizon, or autovacuum throttled too low for the write rate. The lesson: wraparound is preventable with monitoring; treat rising XID age as a sev-2 before it becomes an outage.

</details>

<details>
<summary><strong>Q:</strong> A query is doing a sequential scan on a 10M-row table despite an index existing. Walk me through diagnosis.</summary>

Run `EXPLAIN ANALYZE` and reason about *why the planner chose seq scan* — it's usually a deliberate (if wrong) cost decision, not a bug:

1. **Stale statistics** — if the planner's `rows` estimate is wildly off from `actual rows`, it's mis-costing. Run `ANALYZE` to refresh; bad stats are the #1 cause of "it ignores my index."
2. **The index can't serve the predicate** — e.g., a composite index `(a, b, c)` and the query filters only on `b` (leading-column rule), or a function/expression on the column (`WHERE lower(email) = ...`) with no matching expression index, or a type mismatch forcing a cast.
3. **Low selectivity** — if the query returns a large fraction of the table, seq scan genuinely *is* cheaper than millions of random index lookups + heap fetches. The planner is right.
4. **Cost misconfiguration** — `random_page_cost` set too high for SSD/EBS makes index scans look artificially expensive.

Quick confirmation: `SET enable_seqscan = off` for the session and re-EXPLAIN — if the index plan is now dramatically cheaper, you have a stats/cost problem; if it's similar or worse, seq scan was correct. The fix flows from the cause: ANALYZE, add the right index (partial/covering/expression), or accept the seq scan.

</details>

<details>
<summary><strong>Q:</strong> Composite index `(i1, i2, i3, i4, i5, i6)` exists, but a query on `i2 = x AND i5 = y` is slow. Why, and what do you do?</summary>

The **leading-column rule**: a B-tree composite index is sorted by `i1` first, then `i2` within equal `i1`, etc. A query that doesn't constrain the *leading* column (`i1`) can't navigate the tree — Postgres can't jump to "all rows where `i2 = x`" because those are scattered across every `i1` value. So it falls back to a **sequential scan** (the docs show exactly this: ~351ms seq scan on 10M rows).

The fix depends on access patterns. If you frequently query arbitrary subsets of those columns, **separate single-column indexes** let the planner combine them with a **BitmapAnd** — the docs show that combining `btreeidx2` and `btreeidx5` does the same query in ~0.05ms. The trade-off: more indexes = slower writes and more space. So you don't blindly index every column; you order the composite index by your real leading-column queries and add narrow indexes for the secondary access patterns that matter. This is the senior judgment call — indexes are a write-tax you pay for read speed, so index for the queries you actually run, not every column.

</details>

<details>
<summary><strong>Q:</strong> Read Committed vs Repeatable Read vs Serializable — when would you reach for each?</summary>

- **Read Committed (default):** each statement sees a fresh snapshot of committed data. Prevents dirty reads but allows non-repeatable reads and phantoms within a transaction. Right for the vast majority of OLTP — short transactions where you don't re-read the same rows expecting stability.
- **Repeatable Read:** the whole transaction uses one snapshot from its first statement, so repeated reads are stable and (in Postgres) phantoms are prevented. Use it for **reports/analytics** that run multiple queries and need a consistent view, or read-modify-write where you want to detect concurrent changes — concurrent conflicting updates raise a serialization error (`40001`) you retry.
- **Serializable:** via SSI, guarantees the outcome equals *some* serial order by detecting read/write dependency cycles and aborting a transaction. Use it when **correctness under concurrency is critical and hard to reason about with explicit locks** — e.g., invariants spanning multiple rows (double-booking, balance constraints). The cost: you **must** wrap transactions in retry logic for `40001`, and throughput drops.

The senior framing: isolation level is a trade between the database doing the work (higher isolation, more aborts/retries) and you doing it (lower isolation + explicit `SELECT ... FOR UPDATE` locks). Most teams run Read Committed and add row locks surgically rather than globally raising isolation.

</details>

<details>
<summary><strong>Q:</strong> RDS Multi-AZ vs read replicas — what's the difference and what do people get wrong?</summary>

They solve different problems. **Multi-AZ** is for **availability/durability**: RDS keeps a *synchronous* standby in another AZ and automatically fails over (DNS flip, ~60–120s) on primary failure or during maintenance. Crucially, the standby is **not readable** — you get zero read-scaling from Multi-AZ. **Read replicas** are for **read scaling**: *asynchronous* copies you route read traffic to; they lag the primary and can be promoted to standalone instances (useful for cross-region DR or major-version migration).

What people get wrong: (1) **expecting Multi-AZ to offload reads** — it doesn't; the standby just sits there for failover. (2) **Serving read-your-own-writes from an async read replica** — because of replication lag, a user can write then immediately read stale data. You either route those reads to the primary or check `ReplicaLag` and tolerate staleness. (3) Assuming read replicas give HA — they don't auto-failover like Multi-AZ; promotion is manual. The robust setup is **both**: Multi-AZ for failover + read replicas for scale. (Newer Multi-AZ DB *cluster* mode does offer readable standbys, blurring this — worth mentioning to show currency.)

</details>

<details>
<summary><strong>Q:</strong> Your app opens a database connection per request and you're hitting "too many connections" on RDS. Fix it.</summary>

The root cause is that each Postgres connection is a **separate OS process** with real per-connection memory (backend process + `work_mem` allocations), so `max_connections` is small relative to web-app concurrency — a few hundred, scaling with instance size. A connection-per-request app with any traffic exhausts it, and raising `max_connections` just trades the error for memory pressure and context-switch overhead (and can OOM the box if `work_mem` × connections exceeds RAM).

The fix is a **connection pooler** in transaction-pooling mode: **RDS Proxy** (managed, integrates with IAM/Secrets Manager, also smooths failovers) or **PgBouncer**. It multiplexes thousands of client connections onto a small pool of real backend connections, handing a backend to a client only for the duration of a transaction. Application side: use a pooled client and don't hold connections open across slow external calls. This is the single most important RDS Postgres scaling lesson — Postgres scales reads with replicas and connections with a pooler, not by cranking `max_connections`.

</details>

<details>
<summary><strong>Q:</strong> You need to store high-volume time-series sensor data. How would you index and partition it in Postgres?</summary>

*(Directly relevant to Sensorfact's IoT domain.)*

For append-mostly, time-ordered data, two moves matter. **(1) Partitioning by time** — use declarative range partitioning (`PARTITION BY RANGE (reading_time)`) into per-day or per-month child tables. This keeps each partition small, lets you **drop old data instantly** by dropping a partition (vs a slow `DELETE` that creates millions of dead tuples and vacuum load), and lets the planner **prune** partitions outside the query's time range. **(2) Indexing** — a **BRIN** index on the timestamp is ideal here: because rows are physically stored in roughly time order, BRIN stores just min/max per block range, giving a tiny index (kilobytes vs gigabytes for B-tree) that's perfect for range scans on time. Add B-tree indexes on the columns you filter equality on (device_id), or a composite `(device_id, reading_time)` if you query per-device time ranges.

Beyond core Postgres, I'd evaluate **TimescaleDB** (a Postgres extension for time-series — automatic partitioning via hypertables, compression, continuous aggregates) if RDS supports it, or note that very high-cardinality analytical workloads might belong in a columnar store like ClickHouse rather than Postgres. The senior judgment: Postgres handles time-series well *with* partitioning + BRIN, but know where it stops being the right tool.

</details>

<details>
<summary><strong>Q:</strong> What does VACUUM FULL do, and why should you almost never run it on a production table?</summary>

Plain `VACUUM` marks dead-tuple space **reusable in place** — it doesn't return disk to the OS, but it runs without blocking reads/writes. `VACUUM FULL` instead **rewrites the entire table** into a new file to physically compact it and return space to the OS — but it takes an **ACCESS EXCLUSIVE lock** for the whole duration, blocking *all* reads and writes on that table. On a large hot table that's a multi-minute-to-hour outage, plus it needs free disk equal to the table size to build the new copy.

So you almost never run it in production. If you genuinely have severe bloat to reclaim (not just reuse), use **`pg_repack`**, which compacts the table online with only a brief lock at the end. Better still, prevent the bloat: tune autovacuum to keep up, kill long-running/idle-in-transaction sessions that pin the xmin horizon, and for bulk-delete patterns use **partitioning** so you drop whole partitions instead of generating dead tuples. The senior instinct is that needing `VACUUM FULL` is usually a symptom of an autovacuum/transaction-hygiene problem to fix upstream.

</details>

<details>
<summary><strong>Q:</strong> How does Postgres survive a crash, and how does that same mechanism power replication and PITR?</summary>

It's all the **WAL (Write-Ahead Log)**. The rule is "log the change before changing the data file" — every modification is durably written to the WAL before (or independent of) the heap pages it affects. On crash recovery, Postgres replays the WAL from the last checkpoint, redoing committed changes that hadn't been flushed to data files and discarding uncommitted ones. That's the crash-safety / durability ("D" in ACID) guarantee.

The same WAL stream is the substrate for everything else: **streaming replication** ships WAL records to standbys that replay them to stay current (async by default, so small lag); **logical replication** decodes WAL into per-row change events for selective/CDC use; and **PITR** works by keeping a base backup plus the continuous WAL archive, so you can replay WAL up to any chosen point in time. On RDS, automated backups + continuous WAL archiving are exactly this — a restore replays WAL to your target second and produces a *new* instance (it's not an in-place undo). One log, four jobs: durability, replication, CDC, and time-travel recovery.

</details>

<details>
<summary><strong>Q:</strong> A read replica is lagging by 30 seconds and users report stale data. How do you diagnose and mitigate?</summary>

First quantify it: query `pg_stat_replication` on the primary (or `ReplicaLag` in CloudWatch on RDS) — look at `replay_lag` specifically, since a replica can *receive* WAL fast but be slow to *apply* it. Common causes: (1) the replica is **underpowered** and can't replay WAL as fast as the primary generates it (smaller instance, IOPS-bound on apply); (2) a **long-running query on the replica** conflicts with WAL replay — Postgres either pauses replay or cancels the query (`hot_standby_feedback` / `max_standby_streaming_delay` tuning); (3) a **burst of writes** on the primary (bulk load, index build) temporarily floods the WAL; (4) network throughput between primary and replica.

Mitigations: size the replica at least as large as the primary for apply throughput; route long analytical queries to a *dedicated* replica so they don't stall a replica serving user reads; smooth bulk operations on the primary. The application-level fix for the *symptom* (stale reads) is routing: send read-your-own-writes and freshness-sensitive reads to the **primary**, and only eventually-consistent reads to replicas — and surface lag so the app can fail over reads to the primary when lag exceeds a threshold. The principle: async replication means staleness is a property to design around, not a bug to eliminate.

</details>

<details>
<summary><strong>Q:</strong> On RDS you can't edit postgresql.conf. How do you tune Postgres, and which parameters matter most?</summary>

You tune via **RDS parameter groups** — a managed abstraction over `postgresql.conf`. You attach a custom parameter group to the instance and set values there; some parameters are **dynamic** (apply immediately) and some **static** (require a reboot, which on Multi-AZ you can do with a failover). You don't get OS or superuser access, so kernel-level and filesystem tuning is AWS's job.

The parameters that matter most: **`shared_buffers`** (Postgres's own cache, ~25% of RAM — RDS sets a sensible default keyed to instance size); **`work_mem`** (memory per sort/hash operation — the trap is it's *per operation per connection*, so `work_mem` × concurrent operations can blow up memory; set it modestly and raise per-session for heavy analytical queries); **`max_connections`** (scales with instance class — but the real answer to connection pressure is a pooler, not raising this); **`effective_cache_size`** (tells the planner how much OS cache to assume, influencing index-vs-seqscan choices); and the autovacuum knobs (`autovacuum_vacuum_cost_limit`, scale factors) when vacuum can't keep up. The senior framing: on RDS you're tuning the engine through a narrower interface, so you lean more on right-sizing the instance, parameter groups, RDS Proxy for connections, and provisioned IOPS for the IO floor.

</details>

<details>
<summary><strong>Q:</strong> (Honesty) You've used MySQL and general SQL but not Postgres/RDS in production. How would you ramp up?</summary>

*(Calibration question — answer honestly, lean on transferable fundamentals.)*

I'd be upfront: my relational experience is SQL fundamentals plus running MySQL under our Pega/OpenShift containerization, not Postgres internals or RDS operations. But a lot transfers — ACID, indexing strategy, query planning, transaction isolation, and replication trade-offs are engine-agnostic, and my infra-automation background (Terraform, repeatable provisioning) maps directly onto managing RDS as code rather than console clicks.

The Postgres-specific things I'd prioritize learning because they bite differently than MySQL: **MVCC and the vacuum model** (MySQL/InnoDB also does MVCC but Postgres's dead-tuple/bloat/wraparound behavior is more operationally visible), **EXPLAIN ANALYZE** for the Postgres planner, and the **RDS managed layer** — Multi-AZ vs read replicas, parameter groups, and especially **connection pooling** since Postgres's process-per-connection model punishes connection-per-request apps harder than MySQL. To de-risk: start by owning read queries and EXPLAIN tuning on a non-critical path, set up a sandbox RDS instance to deliberately trigger the failure modes (bloat from a long transaction, a Multi-AZ failover, replica lag under load) so I've *seen* them, and carry over my migration discipline — monitor first (XID age, replication lag, vacuum), gate changes on health checks. I'd rather show I know *what I don't know yet* and have a concrete plan than overclaim.

</details>

---

## Say it with your resume

You can claim **SQL fundamentals** and **MySQL** hands-on; bridge from there and be honest about Postgres/RDS specifics:

- **SQL + data modeling** → *"I list SQL as a core skill and built MySQL-backed containerized images. Relational fundamentals — indexing, query plans, isolation — transfer to Postgres; I'd focus on the Postgres-specific MVCC/vacuum behavior."* (Ties to: **MySQL on JBoss/Tomcat for OpenShift**, **SQL in the Backend & Platform skill line**.)
- **Infra-as-code for the data layer** → *"I replaced ticket-driven provisioning with Terraform automation. I'd manage RDS the same way — parameter groups, replicas, and backups as code, not console clicks."* (Ties to: **30 days → 8 hours via Terraform automation**.)
- **Migration / cutover discipline** → *"My live-migration work gated cutovers on health checks and guardrails. I'd apply that to RDS failovers, major-version upgrades, and replica promotion — monitor lag and XID age, verify before advancing."* (Ties to: **Redis state-tier live-migration, 68.4% capacity cut**.)
- **Honest framing** → for Postgres internals you haven't operated, reason from fundamentals and say where direct experience ends.

> See also [[distributed-systems]] (replication, consistency, isolation) and [[redis-and-caching]] (the caching tier that fronts a database like RDS). A future **SQL & Data Modeling** topic would deepen the engine-agnostic side.

---

## Sources

- [PostgreSQL 17 — Concurrency Control (MVCC)](https://www.postgresql.org/docs/17/mvcc-intro.html)
- [PostgreSQL 17 — Routine Vacuuming & TXID Wraparound](https://www.postgresql.org/docs/17/routine-vacuuming.html)
- [PostgreSQL 17 — Index Types](https://www.postgresql.org/docs/17/indexes-types.html)
- [PostgreSQL 17 — Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)
- [PostgreSQL 17 — Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html)
- [PostgreSQL 17 — Streaming Replication / Warm Standby](https://www.postgresql.org/docs/17/warm-standby.html)
- [Amazon RDS for PostgreSQL — User Guide](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
