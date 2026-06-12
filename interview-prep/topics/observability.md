---
title: Observability & Monitoring
bucket: tech
sources: https://prometheus.io/docs/introduction/overview/
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism

**The three pillars and when each.** Metrics are cheap, aggregatable, bounded-cardinality numeric time series — ideal for "is the system healthy right now" and for alerting/SLOs. Logs are high-fidelity discrete events — ideal for "what exactly happened to *this* request" but expensive at scale and hard to aggregate. Traces stitch a single request across services with causal/parent-child spans — ideal for "where in the call graph did latency/errors originate." The senior mental model: alert on *metrics* (RED/USE signals), pivot to *traces* to localize the failing hop, then drop to *logs* for the line-level root cause. Don't try to make any one pillar do all three jobs (e.g., reconstructing rates from logs is slow and costly; storing per-request labels as metrics explodes cardinality).

**Prometheus data model.** Every series is uniquely identified by a metric name plus a set of key/value labels; "every unique combination of key-value label pairs represents a new time series" ([naming docs](https://prometheus.io/docs/practices/naming/)). This is the single most important fact for reasoning about both query power and cost.

**Metric types** ([understanding metric types](https://prometheus.io/docs/tutorials/understanding_metric_types)):
- **Counter** — monotonically increasing, resets to 0 on restart. Never read the raw value; always `rate()`/`increase()`. Rule of thumb: "if the value can go down, it is a gauge" ([instrumentation](https://prometheus.io/docs/practices/instrumentation/)).
- **Gauge** — point-in-time value that goes up and down (queue depth, memory, in-flight requests). Never `rate()` a gauge.
- **Histogram** — pre-bucketed cumulative counts (`_bucket{le=...}`, `_sum`, `_count`). Buckets are fixed client-side; quantiles are computed *server-side* at query time and are aggregatable across instances.
- **Summary** — client-side computed quantiles (`{quantile="0.99"}`). Cheap to read but **not aggregatable** — you cannot average two instances' p99s.

**PromQL essentials.**
- Rate of a counter: `rate(http_requests_total[5m])` (per-second average over the window, handles resets).
- Latency percentile from a histogram (correctly): `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`. The `rate()` is inside, the `sum by (le)` aggregates across instances, and `histogram_quantile` runs outermost ([histograms practices](https://prometheus.io/docs/practices/histograms)).
- Error ratio (an SLI): `sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`.

**Pull vs push.** Prometheus pulls (scrapes) by default — the server controls scrape cadence, gets target-up health for free (`up` metric), and avoids clients overwhelming it. Push (via Pushgateway) is reserved for **service-level batch jobs** that exit before they can be scraped: "the key metric of a batch job is the last time it succeeded ... these are all gauges, and should be pushed" ([instrumentation](https://prometheus.io/docs/practices/instrumentation/)). Anything running more often than ~15 min should be a daemon and scraped instead.

**RED vs USE.** RED (Rate, Errors, Duration) is request-centric — best for online services and user-facing SLOs. USE (Utilization, Saturation, Errors) is resource-centric — best for infrastructure (CPU, disk, queues) to explain *why* a service is unhealthy. Senior usage: RED tells you the service is hurting; USE tells you which resource to blame.

### Trade-offs

- **Histogram vs summary:** histograms cost more series (one per bucket) and require choosing buckets up front, but aggregate across instances and let you change the quantile at query time. Summaries are cheap and exact per-instance but un-aggregatable and lock the quantile at instrumentation time. For fleet-wide SLOs, histograms win.
- **Pull vs push:** pull gives free liveness and central control but struggles with short-lived/serverless workloads behind NAT; push handles those but loses up-detection and can become a stale single point of metric truth.
- **Cardinality vs dimensionality:** more labels = richer slice-and-dice but multiplicative series growth. Every label is a cost decision.
- **Metrics vs traces for latency:** histograms give you cheap aggregate p99 but can't tell you *which* request or *which* downstream hop; traces answer that but you can't afford 100% sampling at scale.

### Failure modes / gotchas

- **High cardinality (label explosion).** "Do not use labels to store dimensions with high cardinality ... such as user IDs, email addresses, or other unbounded sets of values" ([naming](https://prometheus.io/docs/practices/naming/)). Each unique combo is a new series; the docs suggest keeping per-metric cardinality "below 10" and investigating alternatives above 100 ([instrumentation](https://prometheus.io/docs/practices/instrumentation/)). Symptoms: TSDB head-series and memory blow up, ingestion lags, queries time out. Common culprits: putting request IDs, full URLs (with IDs), or customer emails in labels. Fix by removing/normalizing the offending label (e.g., templated route `/user/:id` not `/user/12345`), or move that dimension to logs/traces.
- **Alert fatigue / signal-to-noise.** Cause-based alerts (CPU > 80%, single host down) fire constantly without correlating to user pain. The fix is **symptom-based alerting** tied to SLOs — page on "users are experiencing errors/latency," not on every internal cause. Pages that don't require human action within minutes shouldn't page; they should ticket.
- **`rate()` on a gauge** (silently meaningless), or `histogram_quantile` without the inner `rate()` over `_bucket` (gives lifetime quantile, not recent).
- **Averaging quantiles** across instances (mathematically invalid) — a frequent summary-metric trap.
- **Dashboard sprawl** — 60-panel dashboards no one can read in an incident; they distract rather than aid. A good dashboard answers a question (is this service healthy? RED at the top); a bad one shows every metric you have.

### Tuning knobs (SLO / burn-rate)

- **SLI → SLO → error budget.** Pick SLIs that track user happiness (availability, latency). The error budget is `100% − SLO`; for 99.9% over 3M requests/4wk that's 3,000 allowable errors ([SRE: SLOs](https://sre.google/sre-book/service-level-objectives/)). The budget is what lets you ship — when it's healthy you take risk, when it's spent you freeze and stabilize ([error budget policy](https://sre.google/workbook/error-budget-policy/)).
- **Burn rate = how fast you're spending the budget relative to the SLO.** 1x burn exhausts the 30-day budget in exactly 30 days; 14.4x exhausts it in ~2 days.
- **Multi-window, multi-burn-rate alerting** ([SRE Workbook: alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)) — the recommended approach. For a 99.9% SLO: page at **14.4x burn over 1h (and 5m short window)** = 2% of budget gone fast; page at **6x over 6h (and 30m)** = 5%; ticket at **1x over 3d (6h short)** = slow burn. Requiring *both* the long and short window to exceed threshold gives precision (the long window) plus fast reset (the short window stops the page ~5 min after errors cease instead of an hour later).
- **Low-traffic caveat:** at 10 req/hr a single failure is a 10% hourly rate → a 1000x burn that pages immediately and eats 13.9% of budget. Low-QPS services need generated traffic, aggregated SLOs, or longer windows ([alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)).
- **Structured logging & levels:** log JSON with stable keys (trace_id, service, level) so logs are queryable and joinable to traces. Default to INFO in prod, reserve ERROR for actionable failures, and emit DEBUG behind a flag — log volume is a cost and a signal-to-noise lever just like alerts.

## Interview questions

<details>
<summary><strong>Q:</strong> Why is <code>histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))</code> correct, and what breaks if you reorder the operations?</summary>

You take `rate()` of the cumulative `_bucket` counters first so you're measuring *recent* request distribution, not the lifetime one; you `sum ... by (le)` to aggregate buckets across all instances (histograms are aggregatable precisely because buckets are additive); then `histogram_quantile` interpolates the percentile from those summed buckets. If you drop the inner `rate()`, you get the all-time p95 since process start, which won't reflect a recent regression. If you forget `by (le)` you collapse the buckets and the quantile is garbage. And you can't do this at all with a summary metric, because summaries compute quantiles client-side and you can't average p95s across instances.

</details>

<details>
<summary><strong>Q:</strong> Latency spiked in production, customers are complaining, but no alert fired. Walk me through why that can happen and how you'd find the p99 regression.</summary>

The usual cause is an SLO/alert that's measuring the wrong thing: averaging latency hides tail blowups, the alert is on a cause (CPU) not the symptom (user latency), the burn-rate window is too long to have triggered yet, or — classic — the histogram buckets don't have resolution near the SLO threshold so p99 reads fine even when it isn't. To find it: pull the p99 over time with `histogram_quantile(0.99, sum(rate(req_duration_bucket[5m])) by (le))`, then break it down `by (le, route)` or `by (instance)` to see if it's one endpoint or one host; cross-check against RED error rate. Then pivot from the metric to a trace sampled during the spike window to find which downstream hop added the latency, and finally to that service's logs for the root cause. The follow-up fix is usually adding finer histogram buckets around the SLO target and switching the alert to symptom-based multi-burn-rate.

</details>

<details>
<summary><strong>Q:</strong> Your Prometheus is OOMing and ingestion is lagging. What's your hypothesis and how do you confirm and fix it?</summary>

First hypothesis is cardinality explosion — head series count grew because someone added an unbounded label. Confirm with `topk(20, count by (__name__)({__name__=~".+"}))` to find the worst metrics, and `count(count by (label) (metric))` to find which label is driving series count; the docs warn to keep per-metric cardinality low and treat anything over ~100 as suspect ([instrumentation](https://prometheus.io/docs/practices/instrumentation/)). The fix is to drop or normalize the offending label at scrape time via metric_relabel_configs (e.g., strip request IDs, template URL paths to `/user/:id`), and push that high-cardinality dimension into logs or traces where it belongs. Longer term, add cardinality limits/recording rules and review new metrics in code review.

</details>

<details>
<summary><strong>Q:</strong> Explain pull vs push in Prometheus. When would you actually reach for the Pushgateway, and what do you give up?</summary>

Pull means the server scrapes targets on its schedule, which gives you free target liveness via the `up` metric, central control over cadence, and no risk of clients flooding the server. The Pushgateway exists for one narrow case: service-level batch/cron jobs that finish before they can ever be scraped — you push their "last success time" and stage durations, which are gauges ([instrumentation](https://prometheus.io/docs/practices/instrumentation/)). What you give up is liveness detection (a dead pusher just leaves stale metrics, so they look "up"), and the gateway becomes a shared mutable store you must clean up. The docs explicitly say jobs running more often than ~15 minutes should become daemons and be scraped instead.

</details>

<details>
<summary><strong>Q:</strong> RED vs USE — when do you use each, and how do they work together during an incident?</summary>

RED (Rate, Errors, Duration) is request-centric and maps directly to user experience and SLOs, so it's how I instrument services and how I alert. USE (Utilization, Saturation, Errors) is resource-centric and explains *why* — CPU saturation, disk queue depth, connection-pool exhaustion. In an incident they layer: RED tells me the checkout service is throwing 5xx and p99 is up (the symptom I page on), then USE on that service's resources tells me the DB connection pool is saturated (the cause). Alerting only on USE produces noise because high CPU doesn't always hurt users; alerting only on RED can leave you blind to the root cause, which is why I keep USE on dashboards even when I don't page on it.

</details>

<details>
<summary><strong>Q:</strong> Why prefer histograms over summaries for a fleet of service replicas, and when is a summary still the right call?</summary>

Histograms expose raw bucket counts that are additive, so I can `sum by (le)` across every replica and compute a true fleet-wide p99 at query time, and I can change which quantile I ask for without redeploying. Summaries compute the quantile client-side per instance, and you cannot average p99s across instances — there's no valid way to combine them — so a fleet p99 is impossible. The cost is histograms emit a series per bucket (cardinality) and you must pick buckets up front with resolution near your SLO. A summary is fine when you genuinely only care about a single instance and want an exact, cheap quantile with no bucket-tuning — e.g., a sidecar or a single-process tool.

</details>

<details>
<summary><strong>Q:</strong> Walk me through multi-window, multi-burn-rate alerting for a 99.9% availability SLO. Why two windows?</summary>

Burn rate is how fast you spend the error budget relative to the SLO; 1x burns it over the full 30 days, 14.4x burns it in ~2 days. The recommended config pages on a fast burn (14.4x over a 1h long window) and a medium burn (6x over 6h), and tickets on a slow 1x-over-3d burn ([SRE Workbook](https://sre.google/workbook/alerting-on-slos/)). The point of the *long* window is precision — it ignores brief blips that don't threaten the budget. The point of the paired *short* window (about 1/12 the long one, e.g. 5m) is reset time: the alert must exceed threshold on both windows, so once errors stop, the short window clears in ~5 minutes and the page resolves, instead of the long window keeping you paged for an hour after the incident ends.

</details>

<details>
<summary><strong>Q:</strong> A team wants to alert "page if CPU > 80% for 5 minutes" on every host. Push back as a senior engineer.</summary>

That's a cause-based alert and it's an alert-fatigue generator: CPU at 85% during a batch window or an autoscaling event hurts no one, so this pages people for non-problems and trains them to ignore the pager. SRE guidance is to alert on symptoms tied to user pain — page when the service's error rate or latency SLO is burning budget, not when an internal resource crosses an arbitrary line. CPU belongs on a dashboard and in USE diagnostics, and at most a low-urgency ticket if saturation is sustained. The test for any page is: does a human need to act within minutes, and does it correlate with user harm? If not, it's a ticket or a dashboard, not a page.

</details>

<details>
<summary><strong>Q:</strong> You can't afford to trace 100% of requests. How do you design sampling so traces are still useful for debugging tail latency?</summary>

Head-based sampling (decide at ingress, e.g. 1%) is cheap and gives unbiased aggregate views but will almost always miss the rare slow/error request you actually need. So I combine it with tail-based sampling — buffer spans and keep a trace if it errored or exceeded a latency threshold — so the interesting tail is over-represented while the boring bulk is downsampled. I also keep sampling decisions propagated and consistent across the whole trace (all-or-nothing per request) so traces aren't broken mid-call-graph, and I store the trace_id on logs and as an exemplar on latency histograms so I can jump metric → exemplar → full trace. The trade-off is tail-based sampling needs a collector buffering spans, which costs memory and adds a decision delay.

</details>

<details>
<summary><strong>Q:</strong> What makes a dashboard aid an on-call engineer versus distract them? Design the top of a service dashboard.</summary>

A dashboard should answer a question, not display every metric you collect; the failure mode is a 60-panel wall nobody can parse at 3am. The top of a service dashboard is RED at a glance: request rate, error rate (and error ratio vs SLO), and latency percentiles (p50/p90/p99 from histograms), with the SLO/error-budget burn front and center. Below that I'd put the top dependencies' RED and the service's USE resources for when the top row says "unhealthy" and you need "why." Everything should be on a consistent time range, ordered so the eye flows symptom → cause, and anything that's never been looked at in an incident gets deleted. Drill-down by route/region is a variable, not 40 separate panels.

</details>

<details>
<summary><strong>Q:</strong> How do you set good SLO targets and an error-budget policy that engineering and product both respect?</summary>

Start from user happiness, not from what's easy to measure — pick SLIs like availability and latency that track whether users are getting served, and set the target where the marginal reliability stops mattering to users (chasing 99.999% when 99.9% is invisibly fine just burns velocity). The error budget is `100% − SLO`, and the policy makes it actionable: while budget is healthy you ship features and take risk; when it's exhausted you freeze feature work and prioritize reliability until you're back in budget ([error budget policy](https://sre.google/workbook/error-budget-policy/)). The key is getting product and eng to agree to that policy *before* an incident, so the budget is a pre-negotiated decision rule, not an argument during an outage. I'd also pick a rolling 28/30-day window so it self-heals and one bad day doesn't punish the team for a month.

</details>

<details>
<summary><strong>Q:</strong> Design observability and alerting from scratch for a new payments API (high QPS, strict correctness). What SLOs, signals, and alerts?</summary>

SLIs: availability (non-5xx ratio) and latency (p99 under, say, 300ms) as the user-facing ones, plus a correctness SLI specific to payments — e.g., reconciliation success / no duplicate charges — because for payments "served fast" isn't enough. Targets maybe 99.95% availability given money is involved, with the error-budget policy agreed up front. Instrument RED on every endpoint with histograms bucketed tightly around the latency SLO, USE on the DB connection pool and queue depth, and traces with tail-based sampling (keep all errors and slow traces) so I can debug a stuck payment end to end. Alerting is symptom-based multi-burn-rate on the availability and latency SLOs (14.4x/1h page, 6x/6h page, 1x/3d ticket), plus a separate high-priority alert on the correctness SLI. Logs are structured JSON carrying trace_id and a payment_id (in logs, never as a metric label) so I can join a customer complaint to its trace and root cause, and I keep cardinality bounded by templating routes and never labeling by customer.

</details>

<details>
<summary><strong>Q:</strong> At Oracle you cut on-call pages from 10+/week to zero. Without seeing it, what's the playbook that produces that, and how do you prove it wasn't just suppression?</summary>

Ten pages a week is almost always cause-based, redundant, or non-actionable alerts firing — so the playbook is: audit every alert, classify each as actionable-now (page), eventually-actionable (ticket), or informational (dashboard), and delete or downgrade everything that isn't a true symptom. Then move the remaining pages to SLO-based multi-burn-rate so transient blips don't fire, add grouping/inhibition so one root cause doesn't fan out into ten pages, and automate the toil that the pages were really asking a human to do. The way you prove it's real reduction and not suppression is by watching the SLOs and incident outcomes: if pages went to zero *and* error-budget burn, MTTR, and customer-reported incidents stayed flat or improved, you removed noise, not signal. If user-impacting incidents started slipping through undetected, you over-suppressed — so I'd track "incidents detected by alert vs by customer" as the guardrail metric.

</details>

<details>
<summary><strong>Q:</strong> You enriched Jira alarm context across 2,442 tickets and improved incident resolution time ~20%. What does "context enrichment" buy you in observability terms, and what's the risk?</summary>

Resolution time is dominated by the time to *localize* a problem, not to fix it, so attaching context to an alarm — the affected service, recent deploys, linked dashboard/trace, relevant logs, and similar past incidents — collapses the "where do I even look" phase, which is exactly why it moves MTTR. In pillar terms it's pre-wiring the metric → trace → log pivot into the ticket so the on-call doesn't rebuild it by hand each time. The risk is enriching with stale or wrong context, which sends people down false trails and can *increase* MTTR, so the enrichment has to be derived from live signals (current SLO burn, the actual trace) and validated; and clustering similar incidents (as the weekly AI ops pipeline did) only helps if the clustering is accurate, otherwise you mask a novel incident as a known one. I'd guard it by measuring resolution time before/after and watching for misrouted or mis-clustered tickets.

</details>

## Say it with your resume

- **On-call pages 10+/week → 0.** Frame it as a signal-to-noise project: I audited alerts, killed cause-based and non-actionable pages, and moved the survivors toward symptom/SLO-based alerting so only user-impacting burn pages a human — the senior insight being that fewer, better alerts beat more alerts.
- **Incident resolution time +20% via Jira alarm-context enrichment (2,442 tickets, 6 teams).** This is the metric → trace → log pivot pre-wired into the ticket: enriching alarms with service, recent change, and linked diagnostics collapses the time-to-localize that dominates MTTR.
- **Weekly AI ops reporting pipeline clustering incidents (240 dev-hrs/mo across 15 teams).** Talk about it as reducing alert fatigue and surfacing patterns across teams — clustering turns a flood of individual pages into a smaller set of actionable themes, and the guardrail is cluster accuracy so novel incidents aren't masked.
- **8-step live migration with health checks.** Tie to symptom-based verification — health checks at each step are the SLI gates that let you proceed or roll back, the operational embodiment of "verify the user-facing signal, not just that the process started."
- **Grafana / Datadog / MQL / JQL.** Position Grafana/Datadog as the dashboard-and-alerting surface (RED at the top, drill-downs as variables), MQL as the query layer for SLIs/percentiles, and JQL as how the alarm-enrichment automation read and wrote ticket context at scale.

## Sources

- [Prometheus — Overview](https://prometheus.io/docs/introduction/overview/)
- [Prometheus — Understanding metric types](https://prometheus.io/docs/tutorials/understanding_metric_types)
- [Prometheus — Metric and label naming (cardinality)](https://prometheus.io/docs/practices/naming/)
- [Prometheus — Instrumentation best practices (pull/push, cardinality, counters vs gauges)](https://prometheus.io/docs/practices/instrumentation/)
- [Prometheus — Histograms and summaries](https://prometheus.io/docs/practices/histograms)
- [Google SRE Book — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook — Alerting on SLOs (multi-window multi-burn-rate)](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE Workbook — Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
