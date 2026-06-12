---
title: Redis & Caching
bucket: tech
sources: https://redis.io/docs/, https://github.com/redis/docs
depth: deep
detailed: true
added: 2026-06-12
generated: true
---

## Core concepts

### Single-threaded event loop and latency implications (mechanism)

Redis is **single-threaded for command processing**: all commands execute atomically on a single thread in a single-threaded event loop. This is the foundation of Redis's simplicity and correctness but also its critical constraint.

- **How it works.** Commands arrive in a queue, are executed one-by-one, and the next command doesn't start until the current one completes and its response is sent. This eliminates race conditions, locks, and synchronization overhead. A command that takes 100ms blocks *every other connection* for 100 ms — no parallelism, no exceptions.
- **The cost.** Slow commands (KEYS, SCAN variants on huge sets, SORT, script evaluation with complex logic, large value serialization) tank global latency for all clients. A single 10 ms command blocks 10,000 other clients if they're pipelined. At scale, even single-digit-millisecond commands compound into tail latency problems (p99/p999).
- **The win.** Atomicity is free: SET, increment, list push, and complex Lua transactions never race — no locks, no CAS loops, no Optimistic Locking Exceptions. This is why Redis is faster than a mutex-protected in-memory hashmap for many workloads.
- **Production gotchas.** (1) **KEYS/FLUSHDB** are never acceptable in production — they scan the entire keyspace, stealing milliseconds from all clients. Use SCAN in a background job instead. (2) **Large value operations** (SET/GET on 100MB strings, HGETALL on 1M-field hashes) block the event loop; break into smaller chunks or move to sorted sets with ZRANGE windowing. (3) **Lua scripts** are atomic but count as single commands — long-running scripts block everyone. Keep Lua < 1ms; break complex work into pipelined steps. (4) **Replication write delay** — a slow replica can cause the master's event loop to block on write acknowledgments if you're using synchronous replication.

### Eviction policies and memory management (mechanism + trade-offs)

When Redis hits the `maxmemory` limit, it evicts keys according to a policy. **Choosing the wrong policy is a silent data-loss bug.**

- **Eviction policies (O'Reilly Redis Handbook / Redis docs):**
  - **`noeviction`** — refuse writes, error clients. Safe but causes uptime loss.
  - **`allkeys-lru`** — evict the least-recently-used key *among all keys*. Best for caches where temporal locality matters.
  - **`allkeys-lfu`** — evict the least-frequently-used key (tracks access count, decays over time). Better for skewed workloads (some keys hot, most cold).
  - **`volatile-lru`** — only evict keys that have an `EXPIRE` set. Common mistake: mixing expiring and non-expiring keys without a clear policy; eviction then becomes unpredictable.
  - **`volatile-lfu`** — LFU among keys with `EXPIRE`.
  - **`allkeys-random`** / **`volatile-random`** — dumb; rarely optimal.
  - **`volatile-ttl`** — evict keys with the shortest TTL. Useful when keys have meaningful lifespans and you want to respect those.

- **How to choose.** (1) Use `allkeys-lru` for general session/cache stores (web sessions, computed values, frequently-accessed user data). (2) Use `allkeys-lfu` for workloads with a clear hot set (commodity data, trending topics, popular items). (3) Use `volatile-lru` if you *trust* clients to set correct TTLs; often they don't. (4) **Never use `noeviction` in production** unless you want to be paged at 3 AM because a full Redis instance is refusing writes.

- **The gotcha.** Eviction is *lazy* by default: Redis only evicts when a new command arrives and memory is full. So your first large write *after* hitting the limit might suddenly evict keys and incur a latency spike. Set `maxmemory-policy` and monitor `evicted_keys` metric to catch this.

### Persistence: RDB vs AOF (mechanism + trade-offs)

Redis offers two durability modes; each trades data loss risk for performance.

- **RDB (snapshot).** Periodically writes the entire dataset to disk via `BGSAVE` (background fork). (1) **Fast recovery** — load the entire dataset in seconds. (2) **Small disk footprint** — compressed binary; 10x smaller than AOF for the same data. (3) **Problem: data loss window.** If the server crashes between snapshots, all writes since the last snapshot are lost. Default is `SAVE 3600 1` (one snapshot per hour), so you can lose up to 1 hour of data. (4) **Another problem: fork cost.** On a 50GB dataset, BGSAVE forks the process, temporarily doubling memory and potentially pausing the event loop (Linux CoW may not help if the data is heavily modified).

- **AOF (Append-Only File).** Logs every write command to a file. (1) **Data loss <= 1 second** (with `appendfsync everysec`, the default). (2) **Readable format** — you can read/audit/replay the AOF file; helps forensics. (3) **Larger disk footprint** — AOF is 5-10x bigger than RDB for the same data. (4) **Slower recovery** — replays every command sequentially; takes much longer than RDB. (5) **Blocking on fsync** — if you use `appendfsync always` (safest), every write blocks on disk I/O; throughput tanks. (6) **AOF rewrite** — periodically, Redis rewrites the AOF to remove redundant commands (e.g., if you SET key 10 times, the AOF contains 10 commands; rewrite keeps only the final value). This happens in the background and can also spike memory.

- **Hybrid in production.** (1) **RDB for baseline**, AOF for delta — load the RDB (fast), then replay the AOF tail (small window, fast). (2) **AOF appendfsync everysec** is the standard trade-off: 1-second data loss window, no blocking on writes. (3) **High-write workloads** may skip AOF entirely or use a slower fsync cadence (appendfsync no) and accept disk-level durability guarantees. (4) **Redis Sentinel / Cluster** replicate to replicas asynchronously, so durability comes from *replica+ disk*, not disk alone.

### Replication: sync vs async, leader-follower failover (mechanism + failure modes)

Redis uses a master-replica replication model. Replicas pull from the master; writes happen only on the master and fan out.

- **Asynchronous replication (standard).** Master acks the write immediately, then ships to replicas in the background. (1) **Low write latency.** (2) **Data loss on master failure** — in-flight un-replicated writes are lost. (3) **Lag.** Replicas trail behind by network/disk latency (often milliseconds, sometimes seconds on slow networks). Reads from replicas see stale data.

- **Sentinel failover (high availability).** Separate Sentinel nodes monitor the master. On master failure, Sentinel automatically promotes a replica to master and updates client configs. (1) **Automatic**, no manual intervention. (2) **Data loss** still happens if the old master had un-replicated writes. (3) **Sentinel quorum matters** — 3 or 5 Sentinels; a minority partition cannot promote (prevents split-brain). (4) **Gotcha: fast failover is not instant.** Sentinel needs time to detect the master is dead (configurable heartbeat timeout, often 30 seconds). That window, clients see the old master as alive (they'll retry and eventually timeout).

- **Redis Cluster (horizontal scaling).** Cluster shards data across nodes using **16,384 hash slots** (CRC16(key) % 16384). Each slot is served by a master and replicas. (1) **Automatic slot-based rebalancing** — add a node, it claims slots from others without downtime. (2) **Multi-master** — writes can go to any master for its slots; no single bottleneck. (3) **Cluster failover** — if a master fails, one of its replicas is promoted automatically. (4) **Gotcha: multi-key transactions are restricted** — MULTI/EXEC only works if all keys hash to the same slot. This is why many applications avoid Cluster.

### Caching patterns and stampede prevention (mechanism)

Three main patterns, each with trade-offs:

- **Cache-aside (most common).** Application checks cache (MISS), loads from primary database, writes to cache. (1) **Simple to implement.** (2) **Application controls invalidation** via TTL or explicit DELETE. (3) **Stampede risk** — on cache MISS, many concurrent requests all hit the database simultaneously, spiking load. Mitigation: **single-flight lock** (acquire a Lua-based lock on MISS, load once, then other waiters poll the cache; see official Redis docs for code). (4) **Stale reads** — if the cache TTL is long, readers see old data after writes to the database. Mitigation: explicit cache invalidation on writes (harder to maintain).

- **Write-through.** Application writes to cache first, then to database. (1) **Cache always has recent data.** (2) **Write latency = max(cache, database)** — if Redis is slower than the DB, you pay the extra latency. (3) **Complexity** — cache and database can diverge if the write to DB fails after cache succeeds. You need compensating transactions or careful error handling.

- **Write-behind (also called write-back).** Application writes to cache, which asynchronously drains to the database in batches. (1) **Fast writes** — latency is just the cache write. (2) **Complexity and data loss** — if Redis crashes before the batch drains, data is lost. Durability depends on AOF + replicas. (3) **Used for analytics, bulk updates; risky for critical writes.**

- **Cache stampede prevention — the Lua single-flight lock (critical pattern).** When a hot key expires, every request that arrives sees a MISS and tries to reload. If the database load is slow, thousands of threads hammer the DB. Solution: (1) acquire a Lua lock on MISS (`SET lock-key token NX PX 30000`); (2) the first requester holds the lock, loads the database, and writes the cache; (3) other requesters fail the lock, poll the cache until it's populated, then return the value. Code in official Redis docs. **This is the senior-level trick for cache-aside at scale.**

### Client-side caching with RESP3 and invalidation (mechanism)

Redis 6.0+ supports server-assisted client-side caching via **CLIENT TRACKING**. The client locally caches values the server has sent, and the server remembers which client holds which key. On a key modification, the server sends an invalidation message.

- **How it works.** (1) Client connects with `CLIENT TRACKING ON`. (2) When client executes a GET, the server remembers "client X has key Y". (3) When any client writes key Y, the server sends an invalidation to client X. (4) Client X evicts its cache entry and refetches. (1) **Eliminates round-trip latency for cache hits** — the value is already in the application process memory. (2) **Reduces Redis load** — fewer network round-trips. (3) **Invalidation is eventual** — there's a window where the client may have a stale value. (4) **RESP3 required** — older RESP2 clients can't receive invalidation; they fall back to Pub/Sub (higher latency, more Redis load).

- **Gotcha.** Client-side caching is opt-in and requires application code changes. Most teams skip it because the default is simpler. Use it when every millisecond of latency matters (high-frequency trading, real-time recommendations) and you can stomach the complexity.

### Distributed locks with Redlock and safety (mechanism + gotchas)

Distributed locks are infamously hard. Redis offers `SET key token NX PX ttl` as a simple lock.

- **Simple SET lock.** (1) `SET resource mytoken NX EX 30` atomically sets the key iff it doesn't exist and auto-expires in 30s. (2) To release, delete the key *only if the token matches* (use a Lua script to avoid race on check-delete). (3) **Problem: clock skew.** If the server's clock jumps (NTP correction, VM pause), locks can expire early or be held longer than expected. (4) **Problem: GC pause.** If the client hangs for 35 seconds (GC, scheduler stall), the lock expires while the client still thinks it holds it — the client might perform an action and another client simultaneously performs a conflicting action (classic split-brain).

- **Redlock (Antirez, 2014).** To be safe against clock skew and GC pauses, acquire locks on *multiple independent Redis instances* (usually 5). A lock is held if *at least 3* servers agree. (1) **Safer against single-node failures and clock skew.** (2) **Much slower** — you're writing to 3+ servers. (3) **Still not perfect.** Antirez's Redlock paper is controversial; Martin Kleppmann's critique ("How to do Distributed Locking") points out that even Redlock can't protect against client GC pauses without additional safeguards (e.g., fencing tokens from an external oracle). **Senior answer: use Redlock for "good-enough" locks (optimistic); for hard safety (e.g., financial transactions), use a lock service with monotonic counters (Chubby, Zookeeper, etcd), not Redis.**

### Hot keys and big keys — production patterns (failure modes)

- **Hot keys.** A key accessed by many clients simultaneously (e.g., a counter, a user's session, a leaderboard head). (1) **Uneven load.** Redis has no sharding within a single key, so all access goes to one node (in Cluster, one master). (2) **Network bottleneck** — the link to that node saturates. (3) **CPU spike on the node** — even simple commands on hot keys can steal CPU from other keys. (4) **Mitigations:** (a) **client-side replication** — each client caches the hot key locally and reads from cache (trade-off: staleness). (b) **replicate on followers** — use read replicas for hot reads (only works if all accesses are reads). (c) **shard manually** — split the hot key into shards (counter_0, counter_1, ... counter_15) and sum on reads. (d) **use local caches** (in-process, not Redis).

- **Big keys.** A value that's very large (100MB string, 1M-field hash, 10M-element list). (1) **Memory exhaustion** — one key consumes a huge fraction of Redis memory, triggering eviction. (2) **Latency spike on operations.** Serializing / deserializing / transferring a 100MB value blocks the event loop for 100s of milliseconds. (3) **Replication lag** — big values replicate slowly; replicas fall far behind. (4) **Mitigations:** (a) **break into smaller pieces** — store list elements in a sorted set so you can paginate with ZRANGE. (b) **compress on client side** — send gzip-compressed data, decompress in the client. (c) **use streams** if the data is temporal. (d) **don't store big values in Redis** — use an object store (S3, GCS) and keep just the reference in Redis.

---

## Interview questions

<details>
<summary><strong>Q:</strong> You hit the memory limit and eviction starts. What data do you lose first, and how do you choose the policy?</summary>

The policy depends on your use case, but most teams get it wrong:
- **If you're caching** (read-heavy, data is derived from a primary DB), use `allkeys-lru`. Least-recently-used keys are probably not needed anymore, and the DB has a fresh copy. You lose old computed values, not critical data.
- **If you're storing session state**, use `volatile-lru` *if* your sessions have TTLs set, otherwise `allkeys-lru`.
- **Never use `noeviction` in production** unless you want your Redis to refuse writes at 3 AM.
- **The gotcha:** eviction is lazy. Your first large write *after* hitting the limit might suddenly evict a batch of keys and cause a latency spike. Monitor `evicted_keys` metric to catch this.

From your resume: your live-migration work likely involved resizing state-tier capacity; eviction policy matters because if the old service is still running and writing while the new one boots, a misconfigured policy could lose session data.

</details>

<details>
<summary><strong>Q:</strong> A slow KEYS command is blocking all other clients. How do you fix this without downtime?</summary>

Never use KEYS in production. Replace it with SCAN (or its variants: HSCAN for hashes, ZSCAN for sorted sets).
- **KEYS blocks** for the entire duration of the keyspace scan.
- **SCAN** is a cursor-based iterator that yields results in chunks (configurable via COUNT). Each SCAN call is O(1) in time (it scans a bucket and returns), not O(N).
- **Migration to SCAN:** run SCAN in a background job (separate connection, low priority). Iterate with the cursor, process keys, and move on. Multiple background jobs can SCAN concurrently.
- **If KEYS is your only tool right now**, put it behind a feature flag and rate-limit it to off-peak hours, or find a secondary Redis replica dedicated to scan operations.
- **Senior pattern:** use tags or naming conventions (e.g., `user:123:*`) and SCAN with a MATCH pattern to avoid scanning the whole keyspace.

</details>

<details>
<summary><strong>Q:</strong> You have a cache-aside pattern. At 3 PM, a hot key expires and 10,000 concurrent requests all try to reload from the database. What happens?</summary>

Cache stampede (or thundering herd). The database gets hammered by 10,000 concurrent queries, your database latency spikes to seconds, and if you don't have timeouts, the entire system grinds to a halt.

**Solution: single-flight lock.**
1. First request acquires a Lua lock on MISS: `SET lock:key token NX PX 30000`. Succeeds, lock acquired.
2. First request loads from database and writes to cache.
3. Other 9,999 concurrent requests try to acquire the same lock, fail, and poll the cache (sleep 10ms, check cache, repeat) until the first request writes the cache.
4. Once the cache is populated, the polling requests return the cached value.

**Lua script example (from Redis docs):**
```lua
local acquired = redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2])
if acquired then
  -- load from DB, write cache, release lock
else
  -- poll cache until available
end
```

**Why Lua?** Atomicity — the SET check and the acquisition happen in a single command, so no race between checking "is the lock set?" and acquiring it.

</details>

<details>
<summary><strong>Q:</strong> RDB vs AOF — which do you use in production, and why?</summary>

Depends on your data loss tolerance and recovery speed requirements:

**RDB (snapshot):**
- ✅ Fast recovery (load entire dataset in seconds).
- ✅ Tiny disk footprint (10x smaller than AOF).
- ❌ Data loss window is large (default 1 hour; crash = lose 1 hour of writes).
- ❌ Fork cost on large datasets (temporarily doubles memory, potential event loop pause).

**AOF (append-only file):**
- ✅ Data loss ≤ 1 second (with `appendfsync everysec`, the default).
- ✅ Readable; helps with forensics and audits.
- ❌ Large disk footprint (5-10x bigger than RDB).
- ❌ Slower recovery (replays commands sequentially).
- ❌ AOF rewrites can spike memory.

**Production standard:** Use *both*. Load RDB on startup (fast), replay AOF tail (small, fast). Or: RDB as baseline, AOF for durability window. Set `appendfsync everysec` (trades ~1 second of data loss for non-blocking writes).

**High-write workloads** may skip AOF entirely and rely on replication for durability (write to multiple replicas, then ack). AOF is IO-bound; Cluster instances often disable it.

</details>

<details>
<summary><strong>Q:</strong> Your replica is lagging behind the master. Writes are going to master, but replicas are 30 seconds behind. How do you detect and fix this?</summary>

**Detection:**
- `INFO replication` on the master shows `slave_lag` or the replica's offset vs the master's offset. If they diverge, the replica is lagging.
- `redis-cli --latency` from the replica to the master measures round-trip time.
- Monitor `repl_backlog_size` — if it's full, the master is discarding old commands and the replica can't catch up (it falls into the "restart from RDB" case, which is expensive).

**Root causes:**
1. **Network congestion** — the replication link is slow. Use `redis-cli --stat` to measure throughput.
2. **Replica is overloaded** — it's processing commands from clients (read replicas) while replicating. Reduce read load or use a dedicated replica for writes.
3. **Master is writing huge values** — big values take time to serialize, send, and deserialize on the replica.
4. **Disk I/O on replica** (if AOF is enabled) — fsync is blocking replication progress.

**Fixes:**
1. **Increase `repl-backlog-size`** (default 1MB) so the master retains more unacknowledged commands. Replica reconnects without needing a full RDB.
2. **Increase network bandwidth** or move replicas to the same data center.
3. **Reduce read load on the replica** or use a dedicated replica that doesn't serve reads.
4. **Disable AOF on the replica** if durability comes from the master (replicas don't need AOF if the master has it).
5. **Use Redis Cluster** to shard the load across multiple masters; no single replica becomes a bottleneck.

</details>

<details>
<summary><strong>Q:</strong> You're building a distributed lock with Redis. What can go wrong?</summary>

Simple `SET key token NX EX 30` is not safe in production:

**Problem 1: clock skew.** If the server's clock jumps backward (NTP correction, VM clock adjustment), the lock's expiration time is wrong. A lock can expire early while the client still thinks it holds it, or vice versa.

**Problem 2: GC pause / scheduler stall.** Client acquires lock, gets paused for 35 seconds (Java GC, scheduler stall), the lock expires, another client acquires it, and now two clients think they hold the lock (split-brain). This is *not* prevented by SET NX.

**Problem 3: fencing.** If the lock expires and another client acquires it while the first client is still inside the critical section, you need a way to prevent the first client from writing to a shared resource. Solution: **fencing tokens** — each lock grant includes a unique, monotonically-increasing token. The resource (DB, file) rejects writes from old tokens. Redis doesn't provide this; use Zookeeper, etcd, or a lock service.

**Mitigations (escalating safety):**
1. **Simple SET lock** — acceptable for non-critical locks (rate limiting, cache lock).
2. **Redlock** (lock on 5 Redis instances, 3+ must agree) — defends against single-node failures and some clock skew, but *not* GC pauses (Kleppmann critique).
3. **Fencing tokens** — add a monotonic counter from an external oracle (Zookeeper, etcd) so resources reject out-of-order writes.

**Senior answer:** Redlock is a compromise; for hard safety (financial transactions), don't use Redis locks. Use a proper lock service.

</details>

<details>
<summary><strong>Q:</strong> You notice one Redis key is getting 10,000 requests/sec while others get 100. What's the problem and how do you fix it?</summary>

Hot key — a single key is much more popular than others. The single node (in Cluster, single master slot) that serves this key becomes a bottleneck.

**Symptoms:**
- **Network saturation** on the link to that node.
- **CPU spike** on the node serving the key.
- **Latency increase** for all commands to that key (p99 latency can grow 10x).

**Root causes:**
- A counter (page views, events) that all clients increment.
- A leaderboard that all clients read.
- A user session or cache entry that's very popular.

**Fixes (escalating):**
1. **Client-side replication** — each client caches the value locally (in-process); replicas poll Redis every few seconds. Trade-off: staleness.
2. **Read replicas** — if access is read-heavy, use replicas for reads. Master handles writes, replicas serve reads. Reduces load on master.
3. **Manual sharding** — split the hot key (counter_0, counter_1, ..., counter_15). Clients write to random shards, then sum on reads. Works for counters, less useful for leaderboards.
4. **Redis Cluster and slot distribution** — if the hot key is on a heavily-used slot, move other keys off that slot so the master's CPU is available.
5. **Local caches + eventual invalidation** — for data that's okay to be stale, use local in-process caches (e.g., Caffeine in Java) and refresh periodically or via pub/sub.

From your resume: your live-migration work likely involved understanding hot keys and rebalancing load during the migration to avoid causing a hot key spike.

</details>

<details>
<summary><strong>Q:</strong> How would you implement a leaderboard in Redis efficiently?</summary>

Use a **sorted set** (ZSET):
- `ZADD leaderboard 100 user1` — add user1 with score 100.
- `ZINCRBY leaderboard 10 user1` — increment user1's score by 10.
- `ZRANGE leaderboard 0 -1` — top N users (lowest to highest). Use `WITHSCORES` for scores.
- `ZREVRANGE leaderboard 0 -1` — reverse order (highest to lowest).
- `ZRANK leaderboard user1` — user1's rank (0-indexed).

**Trade-offs:**
- **Memory efficient** — a sorted set with 1M users + scores is compact.
- **O(log N) updates** — each ZADD/ZINCRBY is O(log N).
- **O(log N + K) to fetch top K** — ZREVRANGE 0 K.
- **No global sorting** — the sorted set maintains sorted order, so no "sort on read" overhead.

**Scaling patterns:**
1. **Leaderboard per region/game** — ZSET leaderboard:game1, leaderboard:game2.
2. **Daily reset** — at midnight, RENAME the ZSET to an archive and create a fresh one.
3. **Large leaderboards** (billions of users) — Redis can't hold billions of entries in memory. Use a database (Cassandra, ClickHouse) for bulk storage, Redis for top-1000 cache.
4. **Tied scores** — sorted sets don't break ties; add a tiebreaker (user ID) to the score: score = (points << 32) | user_id, then decode on read.

</details>

<details>
<summary><strong>Q:</strong> Your application is seeing "OOM Command not allowed when used memory > maxmemory" errors. Eviction isn't keeping up. What's happening?</summary>

Two scenarios:

**Scenario 1: eviction is slower than writes.** Writes are arriving faster than eviction can free memory. Every new write triggers eviction of an old key, but the net memory used keeps growing.

**Fixes:**
- Increase `maxmemory-samples` (default 5) — eviction policy examines more keys before deciding which to evict, so eviction is smarter but slower. This is a trade-off; you're paying CPU to be more selective.
- **Reduce write throughput** — throttle clients or add backpressure.
- **Increase maxmemory** — buy more RAM.
- **Shard across multiple Redis instances** — spread load so no single instance hits the limit.

**Scenario 2: eviction policy is wrong.** You're using `volatile-lru` but most keys don't have TTLs, so eviction has no keys to choose from and falls back to `noeviction`.

**Fix:** Check `MEMORY STATS` and the keyspace. If you're mixing expiring and non-expiring keys, switch to `allkeys-lru`.

**Senior diagnosis:**
- `INFO memory` — `used_memory` vs `maxmemory`.
- `INFO stats` — `evicted_keys` (should be 0 in steady state; if it's growing, you're perpetually evicting, a sign your `maxmemory` is too small or your TTLs are too long).
- `MEMORY DOCTOR` (Redis 4.0+) — gives recommendations.

</details>

<details>
<summary><strong>Q:</strong> A Redis snapshot (RDB) is taking 30 minutes, and it's blocking writes during that time. Why?</summary>

**Why RDB takes time:**
- Redis must fork the process (`BGSAVE` does this). On a 50GB dataset, fork is expensive (CoW page tables, etc.).
- Once forked, the child process writes the entire dataset to disk. Disk write throughput is the bottleneck.
- On some systems (especially with slow disks or network-mounted storage), even the fork + sequential write is slow.

**Why it blocks writes:**
- If the fork is slow, the event loop might be paused during fork. On Linux, fork is fast (milliseconds), but the *duration* of the fork scales with dataset size (more address space = longer page table duplication).
- More commonly, the fork succeeds but subsequent writes cause page-on-write (CoW) in the parent. The parent has to copy modified pages, which is slower than usual writes. This doesn't "block" in the sense of refusing writes, but it increases latency.
- **On some systems (Solaris, Azure VMs)**, fork is not O(1) and can stall the parent for seconds.

**Fixes:**
1. **Use AOF instead of RDB** — AOF writes incrementally (every command), no fork, no CoW spike. Trade-off: larger disk footprint, slower recovery.
2. **Use RDB + AOF hybrid** — RDB as a baseline, AOF for the delta. Recovery loads RDB (fast), replays AOF (small).
3. **Offload snapshots to replicas** — issue `BGSAVE` on a replica, not the master. The master's event loop is unaffected. Replica snapshots are laggier but don't hurt production.
4. **Increase `stop-writes-on-bgsave-error`** (default yes) — if BGSAVE fails, Redis refuses writes to prevent data loss. Set to no to allow writes but accept the risk of partial snapshots.
5. **Use Redis Cluster or managed Redis** (AWS ElastiCache, Google Memorystore) — they handle snapshotting transparently without blocking user writes.

</details>

<details>
<summary><strong>Q:</strong> You're migrating a large Redis dataset from one instance to another. What's the safest approach?</summary>

**For small datasets (< 10GB):**
1. Set the old instance to `--appendonly yes` (enable AOF).
2. Allow AOF to catch up.
3. BGSAVE on the old instance.
4. Transfer the RDB file to the new instance.
5. Start the new instance from the RDB.
6. Enable replication: new instance becomes a replica of the old. Wait for replication to catch up.
7. Failover: promote the new instance, update client configs.

**For large datasets (> 10GB) or low-downtime requirements:**
1. **Use Redis Replication + Sentinel.** Set the new instance as a replica of the old. Replication syncs the entire dataset. Wait until replica is fully caught up (check `redis-cli INFO replication` on both).
2. Once replica is caught up, use Sentinel to failover: Sentinel promotes the replica to master, updates configs, and clients reconnect.
3. Data is never lost; replication is atomic per command.

**For on-the-fly migration (zero-downtime, complex):**
1. **Use `redis-cli --rdb`** on the source to generate an RDB.
2. **Use a migration tool** (Redis Cloud, AWS DMS) that handles dual-writes: writes go to both old and new instances, reading from old. After sync, switch reads to new, then stop writing to old.
3. **Or use `MIGRATE` command** (Redis 2.6+) to move individual keys between instances. Atomic per key; client must handle retries. Slow for large datasets.

**From your resume:** Your live-migration work involved 357 cores and strict sequencing; this suggests a careful, state-aware migration (likely using replicas + health checks, not MIGRATE).

</details>

<details>
<summary><strong>Q:</strong> Explain the difference between LRU and LFU eviction. When would you use each?</summary>

**LRU (Least Recently Used):**
- Evicts the key that was *last accessed the longest time ago*.
- Example: keys A, B, C accessed at times 10, 20, 30 respectively. Evict A.
- **Assumption:** if you haven't used something recently, you won't use it again soon (temporal locality).
- **Pros:** simple, predictable, works well for caches with time-based access patterns.
- **Cons:** doesn't account for frequency. If A was accessed 1000 times before, and C once, but A wasn't accessed in the last minute while C was accessed 10 seconds ago, LRU evicts A (which is wrong).

**LFU (Least Frequently Used):**
- Evicts the key that was accessed the *least number of times* (lifetime frequency).
- Example: keys A (accessed 1000 times, not recently), B (accessed 10 times, recently), C (accessed 5 times, recently). Evict C.
- **Assumption:** if you access something a lot, it's important; keep it.
- **Pros:** captures the "hot set" — popular keys are retained even if not recently accessed.
- **Cons:** takes more memory to track frequency; frequency counts can become stale (Redis decays them over time).

**When to use:**
- **LRU:** streaming, real-time events (time-based recency matters). E.g., sessions (old sessions are inactive), caches (old computed values unlikely needed).
- **LFU:** skewed distributions, content libraries (some items are always popular). E.g., leaderboards (top users are always hot), commodity data (trending topics).

**Production guidance:** Most teams use LRU because it's well-understood. Use LFU if you notice uneven access patterns (some keys are 1000x more popular than others).

</details>

<details>
<summary><strong>Q:</strong> You're considering switching to Redis Cluster for horizontal scaling. What are the trade-offs?</summary>

**Pros of Cluster:**
- **Horizontal scaling** — shards data across multiple nodes using hash slots. No single-node bottleneck.
- **16,384 slots** — CRC16(key) % 16384 determines the slot; each node owns a range.
- **Automatic failover** — if a master fails, one of its replicas is promoted. No external Sentinel needed.
- **Rebalancing without downtime** — add a node, slots migrate without stopping writes.

**Cons (critical):**
- **Multi-key operations are restricted** — MULTI/EXEC only works if all keys hash to the same slot. This breaks many transactional patterns.
- **Client-side redirection** — client must understand the Cluster topology and redirect requests to the correct slot. Not all clients support this well (e.g., some legacy Redis libraries don't).
- **Debugging is harder** — 5 independent nodes, 5 independent event loops, rebalancing in progress. Incidents are more complex.
- **Smaller per-node dataset** — if you have 100GB of data and 10 nodes, each node holds ~10GB. Hot keys on one node are not mitigated.
- **Not suitable for small datasets** — Cluster adds 10-20% overhead for coordination. Only worth it if data grows to multi-TB.

**When to use Cluster:**
- **100GB+ of data** that doesn't fit in a single instance.
- **Throughput bottleneck on a single master** (> 100k ops/sec writes) — Cluster spreads writes.
- **Acceptable multi-key workloads** — most of your operations are single-key or keys hash to the same slot.

**Alternatives to Cluster:**
- **Sentinel + larger instances** — keep a single logical instance (master + replicas), just make it bigger. Sentinel handles failover. Simpler, works until you need > 500GB.
- **Application-level sharding** — manually shard keys across multiple Redis instances. More work but gives fine-grained control.
- **Managed Redis** (AWS ElastiCache, Google Memorystore) — they handle Cluster provisioning and operations.

</details>

<details>
<summary><strong>Q:</strong> A Lua script in your Redis pipeline is taking 100ms, and all other clients are blocked. How do you fix this?</summary>

Lua scripts are atomic — the entire script runs as a single command before the next command is processed. A slow script blocks the entire event loop.

**Root causes:**
1. **Complex computation inside Lua** (loops, sorting) that takes milliseconds.
2. **Lua script generating many Redis commands** inside a loop, amplifying the latency.
3. **Large value manipulation** (serializing/deserializing) inside the script.

**Fixes:**
1. **Move computation out of Lua.** If the script is just coordinating multiple Redis calls, do the calls separately from the client. Trade-off: lose atomicity unless you use a transaction (MULTI/EXEC).
2. **Break the script into smaller pieces.** Instead of one big script, call multiple smaller scripts. Each is fast, minimizing event loop blocking. Use client-side logic to coordinate.
3. **Keep scripts < 1ms.** Lua scripts should be fast dumb helpers (SET if not exists, increment and compare, etc.). Anything more complex doesn't belong in Lua.
4. **Use SCAN instead of KEYS in Lua.** If the script is iterating all keys, that's too slow. Do it in a background job instead.
5. **Profile with `SCRIPT DEBUG`.** Enable debug mode to see where the script is slow.

**Example anti-pattern:**
```lua
-- Bad: iterates all users in a loop
for i=1, 1000000 do
  redis.call('INCR', 'user:' .. i .. ':count')
end
```

**Better:**
```lua
-- Good: client sends a batch of incrments, Lua executes them atomically
local keys = KEYS[1]
for i, key in ipairs(keys) do
  redis.call('INCR', key)
end
```

Or just use pipelined INCR commands from the client without Lua.

</details>

<details>
<summary><strong>Q:</strong> Tell me about a time you had to debug a Redis incident in production. What did you learn?</summary>

*(This is an experience question — tie it to your resume.)*

From your resume, your live-migration work suggests you've dealt with state-tier scaling and rebalancing under production load. A likely incident pattern:

> During the migration, we were moving Redis keys from the old state service to a new one with strict sequencing. Mid-migration, one region's replication started lagging (keys weren't making it to the replica in time), and the migration script couldn't proceed to the next step because the health check failed.

**What I learned:**
1. **Replication lag is silent** — it didn't error immediately; the health check caught it (good instrumentation saves the day).
2. **Single-threaded event loop matters** — adding health checks and migration coordination *on the same instance* caused latency spikes, which in turn caused replication to lag (feedback loop).
3. **Fix:** Offload health checks and coordination to a separate, lightweight service. Let Redis focus on data movement.

*(Adapt this to your actual incident. Senior interviewers want to see systems thinking — root cause, feedback loops, instrument-first mindset — not just "I fixed a bug.")*

</details>

---

## Say it with your resume

Your resume demonstrates Redis expertise through:

1. **"Cut state-tier capacity footprint by 68.4% in OC1... by building an 8-step automated live-migration workflow for Redis-based state services with strict sequencing, health checks, and production guardrails."** — This shows you understand:
   - Replication and failover safety (strict sequencing = ordering guarantees).
   - Health checks and observability (knowing when migration is safe to proceed).
   - Production operational patterns (guardrails = explicit constraints to prevent mistakes).
   - Scaling Redis workloads (350+ cores → efficient resource usage).

2. **"REST APIs, distributed systems, control planes, Redis, SQL, infrastructure automation, reliability engineering"** — You speak the language of distributed systems. Redis is a tool in that toolkit.

**How to position in an interview:**
- When asked about caching: "I've implemented cache-aside with single-flight locks to prevent cache stampedes. We used LRU eviction for computed data and volatile-lru for sessions."
- When asked about state management: "I built an automated migration workflow for Redis state services, handling replication lag and coordinating failover across regions."
- When asked about trade-offs: "RDB is fast to load; AOF is durable. We used both — RDB for baseline, AOF for durability window, with appendfsync everysec."

---

## Sources

- [Redis Official Documentation](https://redis.io/docs/)
- [Redis Command Reference](https://github.com/redis/docs)
- [Cache-Aside Pattern with Stampede Protection](https://redis.io/docs/patterns/cache-aside/)
- [Distributed Locks with Redis](https://redis.io/docs/clients/patterns/distributed-locks/)
- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [Redis Replication](https://redis.io/docs/management/replication/)
- [Redis Cluster](https://redis.io/docs/management/cluster-tutorial/)
- [CLIENT TRACKING for Client-Side Caching](https://redis.io/docs/clients/client-side-caching/)
