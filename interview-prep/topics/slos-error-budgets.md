---
title: SLOs, Error Budgets & Alerting
bucket: tech
sources: https://sre.google/workbook/alerting-on-slos/, https://sre.google/workbook/implementing-slos/
depth: deep
added: 2026-06-13
generated: true
---

## Core concepts

### SLI → SLO → SLA, and why the budget is the point
- **SLI** (indicator) is a *ratio of good events to valid events* — e.g. `successful requests / total requests`, or `requests faster than 300 ms / total`. Keep it a proportion of good/valid so it's naturally 0–100%.
- **SLO** (objective) is the target the SLI must hold over a window: "99.9% of requests succeed over 28 days." Internal, aspirational-but-real.
- **SLA** (agreement) is the *externally promised* threshold with financial/contractual consequences. Your SLO should be **stricter** than your SLA so you breach the SLO (and react) before the SLA.
- The whole point of an SLO is the **error budget** it implies: `budget = 1 − SLO`. A 99.9% SLO over 30 days = **0.1% × 30 days ≈ 43 minutes** of allowable badness. The budget converts "reliability" from a vague virtue into a *spendable quantity* you can trade against feature velocity.

### Error-budget policy — the lever, not the dashboard
The number is useless without a **policy** agreed by eng + product *before* an incident: while budget remains, ship features and take risks; when the budget is exhausted, **the policy enforces a consequence** — freeze risky launches, divert to reliability work, page differently. The policy is what makes the SLO bite; without it you just have a chart.

### Burn rate — the unit that makes alerting tractable
**Burn rate** = how fast you're spending budget relative to "spend it all exactly at window end" (1×).
- 1× burn = you'll exactly exhaust the budget over the SLO window (30 days).
- For a 99.9% SLO, **1× = 0.1% error rate**; **14.4× = 1.44% error rate** and would burn the whole 30-day budget in ~50 hours.
- Handy identity: `budget_consumed = burn_rate × (alert_window / SLO_window)`. So 14.4× over 1 hour = `14.4 × (1h / 720h) = 2%` of the budget.

### Why naive threshold alerts fail
Alerting "error rate ≥ SLO over 10 min" gives fast detection but **terrible precision**: a service could fire **up to 144 pages/day**, you could ignore every one, and still meet the SLO. Stretching the window to 36 h fixes precision but gives **awful reset time** — the alert keeps firing for ~36 h *after* a fully-resolved outage. You're trapped between the four properties any alert trades off: **precision, recall, detection time, reset time.**

### Multiwindow, multi-burn-rate alerts (the recommended design)
Fire only when a **long window** (the event is sustained) *and* a **short window** (it's still burning *right now*) both exceed the burn-rate threshold. The short window (rule of thumb: **1/12 of the long window**) collapses reset time; the long window guards precision. Canonical table for a 99.9% SLO:

| Severity | Long window | Short window | Burn rate | Budget consumed |
|---|---|---|---|---|
| **Page** | 1 hour | 5 min | **14.4×** | 2% |
| **Page** | 6 hours | 30 min | **6×** | 5% |
| **Ticket** | 3 days | 6 hours | **1×** | 10% |

Fast-burn (14.4×) pages immediately on acute outages; the 3-day/1× rule is the slow-burn safety net that catches the quiet, chronic erosion a fast alert misses — and it only files a **ticket**, not a page.

### Failure modes & gotchas
- **Low-traffic services**: one failed request can be 5% error rate, wrecking precision. Mitigate with synthetic traffic, aggregating related services, or reducing per-request blast radius (client retries).
- **Too-high targets**: at 99.999%, 100% failure exhausts the budget faster than a human can respond — that reliability has to be *designed in*, not alerted on.
- **Per-service custom tuning** is a toil trap: apply **uniform** window/burn-rate parameters across services or the cognitive load won't scale.
- **Bad SLI denominators**: counting health-check or bot traffic as "valid events" silently inflates or deflates the SLI.

### Tuning knobs that matter
The window/burn-rate pairs (detection vs precision), the SLO target itself (sets budget size), the short:long ratio (reset time), and what each tier *does* (page vs ticket vs freeze). Everything else is noise.

## Interview questions

<details>
<summary><strong>Q:</strong> A team alerts whenever the 5-minute error rate exceeds their 99.9% SLO threshold. What's wrong, and what would you change?</summary>

Short-window threshold alerting has good detection but terrible precision — at 99.9% you could get up to ~144 pages/day, ignore all of them, and still meet the SLO, so the page carries no information and trains people to ignore it. I'd switch to **multiwindow multi-burn-rate**: page on a fast burn (14.4× over 1 h, confirmed by a 5-min short window = 2% budget) and 6× over 6 h, and file a *ticket* (not a page) on a slow 1× burn over 3 days. The short window kills the reset-time problem; the long window restores precision; the slow-burn ticket catches chronic erosion.

</details>

<details>
<summary><strong>Q:</strong> Define burn rate and show how you'd pick the threshold for a "page now" alert.</summary>

Burn rate is how fast you're consuming error budget relative to spending it exactly over the SLO window (1× = exhaust at window end). Using `budget_consumed = burn_rate × (alert_window / SLO_window)`: if I'm willing to spend 2% of a 30-day budget before paging, over a 1-hour window that's `0.02 = BR × (1/720)` → **BR ≈ 14.4×**. That's the canonical fast-burn page threshold — it means "at this rate the month's budget is gone in ~2 days," which is genuinely page-worthy.

</details>

<details>
<summary><strong>Q:</strong> SLI vs SLO vs SLA — and why should the SLO be tighter than the SLA?</summary>

SLI is the measured ratio of good to valid events; SLO is the internal target over a window; SLA is the externally-promised threshold with financial/contractual teeth. The SLO is set **stricter** than the SLA so you breach (and react to) the internal objective with margin to spare *before* you ever breach the customer-facing agreement — the SLO is your early-warning line, the SLA is the cliff.

</details>

<details>
<summary><strong>Q:</strong> Your service has very low traffic and the burn-rate alerts are noisy — one failure spikes the rate. How do you fix it without lowering the bar?</summary>

Low traffic destroys precision because a single failure is a huge proportion. Options: generate **synthetic/probe traffic** so the denominator is stable; **aggregate** the SLI across a group of related low-traffic services so the event count is meaningful; or reduce per-request blast radius (client-side retries, hedging) so one failure isn't one user-visible failure. I'd avoid the tempting-but-wrong fix of just widening windows until it's quiet — that trades away detection time.

</details>

<details>
<summary><strong>Q:</strong> The error budget is exhausted for the month. What actually happens — and who decided?</summary>

What happens is whatever the **error-budget policy** — agreed by eng and product *ahead of time* — says happens: typically a freeze on risky launches and a redirect of effort to reliability until the budget recovers. The key is that it was negotiated before the incident, so it's a pre-committed rule, not a heat-of-the-moment fight. If there's no policy, the SLO is decorative — the budget only has power because a consequence is wired to it.

</details>

<details>
<summary><strong>Q:</strong> How do you choose a good SLI? Give an example of a bad one.</summary>

A good SLI is a proportion of *good events / valid events* that tracks user-perceived health and moves when users hurt: e.g. `(2xx + intended 4xx) / valid requests`, or a latency SLI `requests < 300ms / total`. A bad SLI is raw CPU or a server-side 500 count with no denominator — it doesn't normalize to traffic and doesn't map to user pain. Another classic mistake is letting health-checks/bots into the denominator, which decouples the number from real experience.

</details>

<details>
<summary><strong>Q:</strong> Why page on the fast-burn alert but only ticket on the slow-burn one?</summary>

Fast burn (14.4×/6×) means the budget will be gone in hours — a human needs to act now, so it pages. Slow burn (1× over 3 days) means something is chronically wrong but you have days of runway; paging someone at 3 a.m. for it would be cruel and low-value, so it opens a ticket for normal-hours investigation. Matching alert *urgency* to budget *runway* is the whole point of tiering.

</details>

<details>
<summary><strong>Q:</strong> You're asked to set an SLO of 99.999%. What's your response?</summary>

I'd push back on alerting-my-way-there: at five-nines the budget is ~26 seconds/month, so even a brief 100% outage blows it before any human can respond — you can't *operate* your way to that number, you have to *design* it in (redundancy, graceful degradation, no single points of failure) and the SLO becomes an architecture requirement, not an on-call target. I'd also ask whether users can even perceive the difference vs 99.9%, since each nine is exponentially more expensive.

</details>

<details>
<summary><strong>Q:</strong> Connect alarm-threshold tuning to error-budget thinking. (Tie to your own work.)</summary>

They're the same problem viewed from two ends: a static alarm threshold fires on instantaneous badness regardless of budget, which is why it produces false pages. In my hot-path state-tier work I replaced static thresholds with **binomial probabilistic analysis** sized per region so the alarm fired on true-positive conditions and suppressed false positives — that's burn-rate thinking applied to a single alarm: alert on *statistically significant sustained* badness, not on one noisy sample, which cut ~13 false alarms/month.

</details>

<details>
<summary><strong>Q:</strong> What does the short window in a multiwindow alert buy you, concretely?</summary>

It fixes **reset time**. With only a long (e.g. 1 h) window, after an outage fully resolves the alert keeps firing until the bad minutes roll out of that hour. Adding a short window (~1/12 the long, so 5 min) as an *additional required condition* means the alert clears within minutes of recovery because the short window goes green fast — you keep the long window's precision but stop paging on an already-fixed problem.

</details>

## Say it with your resume
- **Binomial alarm-threshold tuning** → you've already done the "alert on significant burn, not noise" move at the single-alarm level (false alarms ↓ ~13/month) — the natural bridge into burn-rate alerting.
- **On-call 10+/week → 0** → error-budget/policy thinking as toil elimination: you removed the *class* of page, not just silenced it.
- **Ops Copilot RCA + 20% faster resolution** → detection-to-diagnosis: SLO alerts tell you *that* the budget is burning; your RCA tooling tells you *why*, fast.
- **Health-checked live migrations with guardrails** → spending budget deliberately (staged, reversible) instead of gambling it.

## Sources
- [Google SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE Workbook — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
