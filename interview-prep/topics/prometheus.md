---
title: Prometheus & Observability
bucket: tech
must: true
gap: true
rank: 5
sources: https://prometheus.io/docs/introduction/overview/
generated: true
---

> **Gap focus** — you have **Grafana + Datadog + MQL**; Sensorfact's stack is **Prometheus/Loki/Tempo**. Prometheus is the metrics engine *behind* the Grafana dashboards you've used — frame it that way.

## 80/20 — Core concepts

- **Data model** — each time series = a **metric name** + key/value **labels**, e.g. `http_requests_total{method="post",code="200"}`. Labels enable multidimensional slicing.
- **Four metric types** — **Counter** (monotonic, use `rate()`), **Gauge** (up/down), **Histogram** (bucketed `_bucket`/`_sum`/`_count` → percentiles via `histogram_quantile`), **Summary** (client-side quantiles).
- **Pull-based scraping** — Prometheus scrapes HTTP `/metrics` endpoints on `scrape_interval` (via `scrape_configs` + service discovery). Target health is visible via the `up` metric.
- **Exporters** expose metrics from systems that don't speak Prometheus natively (e.g. node_exporter); apps expose directly via client libraries.
- **PromQL** — `rate(http_requests_total[5m])` for per-second rate; `sum by (code)(...)` for aggregation; `histogram_quantile(0.95, rate(..._bucket[5m]))` for p95.
- **Alerting** — rules (`expr`, `for`, `labels`, `annotations`) fire when a condition holds for a duration; Prometheus pushes to **Alertmanager**, which dedups, groups, silences, and routes.
- **Loki = logs, Tempo = traces** — same label-based model; together with Prometheus metrics they form the three pillars in Grafana.

## Likely interview questions

**Q:** Counter vs. Gauge vs. Histogram?
**A:** Counter only increases (query `rate()` for throughput); Gauge rises/falls (current value like queue depth); Histogram buckets observations to compute latency percentiles. Choose by whether the value is cumulative, instantaneous, or a distribution.

**Q:** Push vs. pull — how does Prometheus collect data?
**A:** It pulls by scraping targets' `/metrics` on an interval — making target health visible (`up`) and simplifying discovery. The Pushgateway exists only for short-lived batch jobs.

**Q:** How do you compute a request rate or p95 latency?
**A:** `rate(metric_total[5m])` for per-second rate of a counter; `histogram_quantile(0.95, rate(metric_bucket[5m]))` for p95 from a histogram.

**Q:** How does alerting work end to end?
**A:** Prometheus evaluates rules; an alert is Pending until true for the `for` duration, then Firing. It pushes firing alerts to Alertmanager, which groups, dedups, silences, and routes to receivers (PagerDuty/Slack/email).

## Say it with your resume

- **Bridge:** "I've run production monitoring with **Grafana and Datadog** and used query languages (**MQL/JQL**) day to day — Prometheus is the metrics backend that feeds exactly those dashboards, so PromQL and the metric types are a short hop."
- Anchor it in impact: "I improved incident resolution time **20%** and cut on-call pages **10+/week → 0** — I know what *good* alerting and signal-vs-noise look like, which is the harder half of observability."

## Sources

- [Prometheus Overview](https://prometheus.io/docs/introduction/overview/)
