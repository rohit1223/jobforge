---
title: Example Topic (SLOs & Error Budgets)
bucket: domain
learning: false
depth: standard
sources: https://sre.google/workbook/implementing-slos/
added: 2026-01-01
generated: true
---

> This is an example topic showing the deep-content format the `interview-prep`
> skill generates. Real topics are derived from your resume + job gap reports and
> live in `interview-prep/topics/` (gitignored). Delete this once you have your own.

## Core concepts
Senior mental-model, cited throughout. Cover, with real depth:

- **How it actually works** — an SLO is a target on an SLI (a ratio of good to
  valid events); the error budget is `1 - SLO` over a window, the amount of
  unreliability you're allowed to spend.
- **Key trade-offs** — tight SLOs slow feature velocity; loose ones erode trust.
  Burn-rate alerting (multi-window) trades alert speed against false positives.
- **Failure modes & gotchas** — measuring availability at the load balancer hides
  partial outages; averaging latency hides tail pain (alert on percentiles).
- **Tuning knobs** — SLO target, measurement window, burn-rate thresholds, and
  which SLI actually reflects user happiness.

## Interview questions
10–15 questions calibrated for 9+ years (NO "what is X" recall). Each as a
click-to-reveal self-quiz block:

<details>
<summary><strong>Q:</strong> Your error budget is exhausted mid-quarter. What changes, concretely?</summary>

Feature releases pause; the team redirects to reliability work until the budget
recovers over the rolling window. The policy must be agreed in advance so it's a
mechanical trigger, not a negotiation. The point is to make reliability and
velocity trade off explicitly rather than implicitly.

</details>

<details>
<summary><strong>Q:</strong> Why alert on burn rate over multiple windows instead of a single threshold?</summary>

A fast-burn window (e.g. 1h at 14.4×) catches acute outages quickly; a slow-burn
window (e.g. 6h at 6×) catches sustained low-grade errors a single threshold
would miss. Requiring both a short and long window to fire cuts false positives
from brief spikes while still paging fast on real incidents.

</details>

## Say it with your resume
- Tie a real achievement (paraphrased from your `master/resume.tex`) to this topic
  so you can pivot any question into evidence from your own work.

## Sources
- [Google SRE Workbook — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
