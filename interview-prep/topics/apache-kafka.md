---
title: Apache Kafka
bucket: tech
must: false
gap: true
rank: 7
sources: https://kafka.apache.org/documentation/
generated: true
---

> **Gap focus** — Sensorfact uses **Aiven Kafka** + MQTT/EMQX for messaging. You've built distributed/stateful systems (Redis state tier) but not Kafka — learn the log/partition model; bridge from your distributed-systems experience.

## 80/20 — Core concepts

- **Topic** = a named, append-only log, split into **partitions** for parallelism. Ordering is guaranteed **only within a partition**, not across a topic.
- Each record has a sequential **offset**; consumers track position by offset, committed to an internal topic so they resume after restart.
- **Producers** choose the partition (key hash for ordering, or round-robin). **`acks`** controls durability: `0` (fire-and-forget), `1` (leader only), `all` (all in-sync replicas — strongest).
- **Consumer groups** — consumers sharing a `group.id` split partitions; each partition is consumed by exactly one consumer in the group → horizontal scaling up to the partition count. Membership changes trigger a **rebalance**. Different groups each get a full copy (pub/sub).
- **Replication** is per partition (commonly RF=3): one **leader** handles reads/writes, **followers** replicate; the caught-up set is the **ISR**. Failover promotes an ISR follower.
- **Delivery semantics** — at-least-once by default; at-most-once (commit before processing, risk loss); exactly-once via idempotent/transactional producer + read-committed consumers.

## Likely interview questions

**Q:** Why partitions, and what ordering guarantee do they give?
**A:** Partitions are the unit of parallelism/scale — more partitions = more concurrent consumers. Ordering holds only within a single partition, so messages that must stay ordered should share a partition key.

**Q:** How do consumer groups achieve scaling?
**A:** Within a group each partition goes to exactly one consumer, so throughput scales by adding consumers up to the partition count. Different groups each get an independent full copy (pub/sub). Membership changes cause a rebalance.

**Q:** Explain the three delivery semantics.
**A:** At-most-once may lose messages (commit before processing); at-least-once may duplicate (process then commit — the default); exactly-once avoids both via idempotent/transactional producers committing offsets + output atomically with read-committed isolation.

**Q:** What is ISR and how does `acks=all` relate?
**A:** ISR = replicas fully caught up to the partition leader. `acks=all` makes the producer wait until all in-sync replicas have the record, surviving a leader failure — the strongest durability.

## Say it with your resume

- **Honest bridge:** "I haven't operated Kafka, but I've built **stateful distributed systems** — an 8-step live-migration for Redis-based state services with strict sequencing, health checks, and guardrails. Concepts like partitioning for parallelism, replication/ISR for durability, and ordering guarantees are the same distributed-systems primitives I reason about."
- If they probe MQTT/EMQX: be candid it's new, but note you understand pub/sub + delivery-guarantee trade-offs (at-least-once vs exactly-once), which transfer across brokers.

## Sources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
