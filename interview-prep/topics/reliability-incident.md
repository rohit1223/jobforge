---
title: Reliability & Incident Engineering
bucket: tech
must: false
rank: 8
sources: https://sre.google/sre-book/table-of-contents/
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism: SLI / SLO / SLA and error budgets
An **SLI** is a quantitative measurement of a user-facing property — request latency, error rate, availability, throughput — expressed as `good events / valid events`. An **SLO** is a target for that SLI ("99.9% of requests succeed over 28 days"); an **SLA** is the SLO plus a contractual consequence (refunds, penalties) for missing it. The senior framing: pick SLIs from the *user's* perspective, use percentiles (p99) not averages because the mean hides the slow tail, and keep targets simple and few. Never aim for 100% — users cannot distinguish 99.99% from 99.999% when their own network and device fail more often, and the cost curve goes vertical near the top.

The **error budget** is the inverse of the SLO: `1 − SLO`. A 99.9% monthly SLO grants ~43 minutes of allowable unreliability. This converts reliability from an argument into a *measurement*. While budget remains, the team ships freely; when it is exhausted, releases freeze and effort redirects to hardening until the budget recovers. That single mechanism dissolves the perennial product-vs-SRE fight — both sides now optimize a shared, objective number instead of negotiating risk politically.

### Trade-off: reliability vs. feature velocity
The error budget is the explicit knob between these two. A budget that is *never* spent signals the SLO is too strict and you are leaving release velocity on the table — you should loosen the target or ship faster. A budget burned to zero every month means you are too aggressive and must invest in resilience. The deeper trade-off: every nine of reliability roughly multiplies cost (redundancy, testing, on-call rigor), so the SLO should be set just above what users actually need, not maximized. SLAs are deliberately set *looser* than internal SLOs so you alarm and remediate before contractual penalties trigger.

### Failure mode: alert fatigue
Every page must be **actionable, novel, and urgent**. Alert on **symptoms** (user-visible: error ratio, latency, queue depth) not causes (CPU high). The modern discipline is **multiwindow, multi-burn-rate alerting**: burn rate = how fast you consume the error budget relative to a steady spend of 1. Google's reference config for a 99.9% SLO pages at a 14.4x burn over 1h (2% budget gone, confirmed by a 5m short window), pages at 6x over 6h (5% gone), and *tickets* (not pages) at 1x over 3 days (10% gone). The long window measures significance; the short window (≈1/12 of it) confirms the problem is still active so the alert resets within minutes. Fast-burn catches sharp outages; slow-burn catches a slow bleed before it exhausts the month. Anything not urgent becomes a ticket, not a page — this is the core lever against fatigue and burnout.

### Failure mode: cascading failure
Under overload, **throughput stays high but goodput collapses** — servers do work, then clients time out and that work is wasted, then clients retry, multiplying load. Retries amplify across layers (3 retries × 5 hops = 243x load on the database). The 2001 Amazon outage is the canonical example: caches failed, every web server hit the DB directly, and the partial degradation became a full outage. Defenses: **load shedding** (reject excess at the edge to protect goodput, prioritize health checks and completion-over-initiation), **backpressure** (bounded queues with max-wait so stale requests are dropped), **timeouts tuned to p99.9**, **exponential backoff with jitter** to de-synchronize retries, **token-bucket retry budgets** so retries are capped, **circuit breakers**, and **graceful degradation** (serve a cached/reduced response rather than failing hard).

### Practices: toil elimination, incident response, postmortems
**Toil** is operational work that is manual, repetitive, automatable, tactical, has no enduring value, and scales linearly with the service. Google caps it at **50%** of an SRE's time; the rest is engineering that reduces future toil. **Incident response** uses recursive separation of roles — **Incident Commander** (holds state, delegates, makes calls), **Ops lead** (the only one mutating the system), **Comms lead** (stakeholder updates), **Planning** (bugs, logistics, handoff) — anchored by a live incident doc and a recognized command post. **Blameless postmortems** assume everyone acted reasonably on the information they had; you fix systems, not people, because blame drives problems underground. **MTTD** (detect) drops with good symptom alerting and observability; **MTTR** (resolve) drops with runbooks, automated remediation, fast rollback, and rehearsed roles.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through how an error budget actually governs release velocity day to day. What do you do when it's healthy vs. exhausted?</summary>

The error budget is `1 − SLO` measured over a rolling window — a 99.9% monthly SLO is ~43 minutes of allowable badness. While budget remains, product ships at full speed because we have objective headroom for risk; the policy is pre-agreed, not negotiated per release. When the budget is exhausted, releases freeze (except security/reliability fixes) and the team redirects to hardening — paying down the failure that burned it — until the budget recovers. The subtlety is the *other* direction: a budget that is never touched means the SLO is too conservative and we are sacrificing velocity for reliability nobody perceives, so I'd loosen the target or push the team to ship faster. The whole point is to replace political risk arguments with a shared number both product and SRE optimize.

</details>

<details>
<summary><strong>Q:</strong> Explain multiwindow multi-burn-rate alerting and why it beats a simple "error rate > X%" threshold.</summary>

Burn rate is how fast you spend the error budget relative to a steady rate of 1; a burn of 14.4 exhausts a month's budget in ~2 hours. A simple static threshold is either too twitchy (pages on transient blips) or too slow (waits for a long averaging window to reset). Multiwindow pairs a long window to confirm the burn is *significant* with a short window (~1/12 of it) to confirm it's *still happening*, so the alert clears within minutes of recovery instead of after the whole window expires. You run tiers: a fast-burn page (14.4x/1h, 2% budget) for sharp outages and a slow-burn ticket (1x/3d, 10% budget) for a slow bleed. Tiering by severity — and routing slow burns to tickets, not pages — is also the main mechanism for controlling alert fatigue.

</details>

<details>
<summary><strong>Q:</strong> A service is healthy at normal load but falls over completely the moment traffic spikes 30%. Diagnose the likely failure mode and the fixes.</summary>

This is classic overload-induced cascading failure: past a tipping point, contention (locks, GC, context switching, connection pools) makes latency climb, clients hit timeouts, the server's completed work is wasted, and clients retry — so offered load rises exactly when capacity is falling. Throughput may look fine while goodput collapses. The fix set is layered: shed load at the edge so the server protects the requests it admits, enforce timeouts tuned to p99.9, replace unbounded surge queues with bounded queues plus a max-wait so stale requests are dropped (backpressure), and cap client retries with token buckets plus exponential backoff *with jitter* to stop synchronized retry storms. Longer term I'd add circuit breakers and graceful degradation so a dependency hiccup yields a reduced response rather than a hard failure that propagates.

</details>

<details>
<summary><strong>Q:</strong> Walk an outage end to end — from page to closed postmortem — and call out where time is actually lost.</summary>

Page fires from a symptom-based burn-rate alert; the on-call acks, declares an incident, and (if it's non-trivial) someone takes the Incident Commander role with separate Ops and Comms leads so there's one decision-maker and one source of truth. MTTD was already spent before the page — good symptom alerting and observability shrink it. Inside MTTR, the biggest losses are usually *diagnosis* and *coordination*, not the fix itself, so I bias toward fast mitigation (roll back, shift traffic, flip a flag) before root-causing, and keep a live incident doc to avoid re-deriving state at handoffs. Comms sends regular stakeholder updates so engineers aren't interrupted. After mitigation we run a blameless postmortem with a timeline, contributing factors, and prioritized action items with owners — and crucially track those items to completion, because an outage that recurs means the postmortem failed.

</details>

<details>
<summary><strong>Q:</strong> What separates a genuinely blameless postmortem from one that's blameless in name only? Why does it matter operationally?</summary>

A real blameless postmortem assumes everyone acted reasonably given the information and tools they had, and asks why the *system* let a reasonable action cause harm — bad defaults, missing guardrails, confusing dashboards, a deploy with no canary. The tell of a fake one is action items that read "Bob will be more careful" instead of "add a confirmation guard / a canary stage / an automated rollback." It matters because you cannot fix people but you can fix systems, and the moment people fear punishment they stop reporting near-misses and start hiding mistakes — which raises your real risk and starves you of the weak-signal data that prevents the next outage. The discipline borrows directly from aviation and healthcare, where every mistake is treated as a chance to strengthen the system.

</details>

<details>
<summary><strong>Q:</strong> Define toil precisely and tell me how you'd decide what to automate first when everything feels like toil.</summary>

Toil is operational work that is manual, repetitive, automatable, tactical, produces no enduring value, and scales linearly with the service — note that "important work" isn't toil even if it's annoying. Google caps it at 50% of an SRE's time so the other half buys down future toil. To prioritize I'd quantify: frequency × time-per-occurrence × number of people affected gives total hours, and I'd weight by toil that *scales with growth* because that's the work that will eventually consume the team. I also separate "eliminate the need" (design the task away) from "automate the task," preferring the former. The trap is automating a fragile process — automate a flaky runbook and you've built a faster way to cause incidents, so I'd stabilize and document before encoding it.

</details>

<details>
<summary><strong>Q:</strong> How do you choose SLIs and set SLO targets for a new service, and where do teams usually get this wrong?</summary>

Start from the user journey, not from what's easy to scrape: for a request/response service the SLIs are availability (success ratio of valid requests) and latency at a percentile, plus correctness/freshness where relevant. Express each as good/valid events so it's interpretable as a budget. For the target I avoid two mistakes: copying current performance (which bakes in whatever you happen to do today) and chasing nines past user perception (each nine roughly multiplies cost for value users can't detect). I keep SLOs few and simple, set the SLA looser than the internal SLO so I remediate before penalties hit, and treat the target as revisable — start conservative, tighten as the budget data comes in. The most common failure is measuring the average instead of the tail, which hides the slow requests that actually drive users away.

</details>

<details>
<summary><strong>Q:</strong> Design an on-call and alerting system for a 6-team org to drive page volume down without missing real incidents.</summary>

The governing principle is that every page must be actionable, novel, and urgent — anything else is a ticket or a dashboard. I'd build SLOs per service and drive all paging off symptom-based, multiwindow burn-rate alerts (fast-burn pages, slow-burn tickets), then audit cause-based alerts (CPU, disk) and either delete them or downgrade to tickets. Operationally: a primary/secondary rotation with a hard cap on pages per shift, clear escalation and IC/Comms/Ops roles, and runbooks linked directly from each alert to cut MTTR. I'd instrument the alerting itself — page volume per shift, ack and resolution times, and a recurring review where any alert that fired without action gets tuned or killed. The strongest single move is often removing a *dependency* that generates pages rather than tuning the alert: when I replaced tunnel-based access with secure public management APIs, the right fix was eliminating the failure source, which took a rotation from 10+ pages a week to zero.

</details>

<details>
<summary><strong>Q:</strong> What concrete levers reduce MTTD and MTTR, and which usually moves the needle most?</summary>

MTTD shrinks with symptom-based alerting tied to SLOs, good distributed tracing/logging, and synthetic probes so you detect before users report. MTTR decomposes into detect-to-diagnose-to-mitigate-to-resolve, and in practice the diagnosis and coordination phases dominate — so the highest-leverage moves are fast, safe mitigation paths (one-click rollback, traffic shifting, feature flags), rehearsed incident roles so nobody is improvising org structure mid-outage, and runbooks/automation that turn known failures into a button press. I deliberately mitigate before root-causing. The single biggest win I've seen is reducing *time-to-context*: enriching alerts with the diagnostic data the responder needs inline — when I enriched incident tickets with alarm context across six teams, resolution time improved about 20% purely by collapsing the "what is even happening" phase.

</details>

<details>
<summary><strong>Q:</strong> Compare load shedding, backpressure, and circuit breakers. When do you reach for each?</summary>

They attack overload at different points. **Load shedding** is the server rejecting excess work at admission so it protects goodput for the requests it admits — you prioritize (health checks, completion over initiation) and reject cheaply at the edge; reach for it when *your* service is the bottleneck. **Backpressure** is signaling upstream to slow down — bounded queues with a max-wait that drop stale requests, or flow-control that propagates "I'm full" — reach for it to keep the pressure from converting into a silent latency cliff. **Circuit breakers** sit on the *client* side of a dependency: after a failure threshold they open and fail fast instead of piling timeouts onto a struggling downstream, then half-open to probe recovery — reach for it to stop a sick dependency from taking you down too. In a real architecture you layer all three plus retry budgets and jitter; no single one is sufficient.

</details>

<details>
<summary><strong>Q:</strong> Why can a fallback path make an outage worse, and how do you make fallbacks trustworthy?</summary>

Fallbacks are dangerous because they almost never run, so they're under-tested and carry latent bugs that only surface under the exact stress where you most need them — and they place unpredictable load on a system already failing, which is how a partial outage cascades into a full one. There's also a logical tell: if the fallback were genuinely better, it would be the primary path. The trustworthy approach is to make the alternate path a real *failover* you exercise constantly in production so both paths are equally proven, or eliminate the fallback by pushing critical data locally ahead of time, or lean on hedged/proactive redundancy that runs continuously rather than reactive error-handling that spikes load. If you must keep a reactive fallback, it has to be load-tested and continuously exercised, not assumed.

</details>

<details>
<summary><strong>Q:</strong> How do you do production change safely under live traffic — canaries, guardrails, progressive rollout?</summary>

The model is to expose change to a small, observable blast radius and let data gate promotion. A canary takes a small traffic slice, compares its SLIs against the baseline, and auto-rolls-back on regression; progressive/percentage rollouts widen the slice in stages with bake time between them so slow-burn problems surface before full exposure. Guardrails are the automated stops — health checks at each step, error-budget-aware deploy gates, and a fast rollback path that's as rehearsed as the deploy. For stateful or migration work this is even more critical: I ran an 8-step live migration with health checks and production guardrails at each step so any step could halt and roll back without taking down live traffic, and feature flags let me decouple deploy from release so I could dark-launch and flip exposure independently of the binary push.

</details>

<details>
<summary><strong>Q:</strong> How do you keep an on-call rotation sustainable, and how would you measure whether it's healthy?</summary>

Sustainability starts with the page budget: cap pages per shift, and treat a rotation that exceeds it as a reliability bug to be engineered away, not endured. I'd measure page volume per shift, the actionable-page ratio (pages that led to a real action vs. noise), after-hours page count, ack/resolve times, and toil percentage, and review them on a cadence where any noisy alert gets tuned or deleted. Compensate on-call, ensure follow-the-sun coverage so no one carries nights indefinitely, and protect the 50% engineering time so the rotation can actually fix the things paging it. The deepest lever is eliminating page *sources* — removing a fragile dependency or auto-remediating a known failure removes the page permanently, which is how I took a UK-India rotation from 10+ pages a week to zero rather than just getting better at responding to them.

</details>

<details>
<summary><strong>Q:</strong> You're asked to raise an SLO from 99.9% to 99.99%. How do you reason about whether that's the right call?</summary>

First I'd ask whether users can perceive the difference and whether anything contractual depends on it — going from ~43 min/month to ~4 min/month of allowed downtime is real money in redundancy, testing rigor, and on-call load, and it's wasted if the user's own network fails more often than that. I'd look at the current budget burn: if we routinely finish the month with budget to spare, the existing SLO already isn't constraining us and tightening it just slows releases; if we burn it consistently, we can't even hold 99.9% yet so promising 99.99% is fiction. I'd also check architectural feasibility — single points of failure, dependency SLOs (you can't be more available than your hard dependencies), and deploy/rollback speed. The honest answer is often "no, and here's the cost," because each nine roughly multiplies cost for value that may be invisible to users.

</details>

## Say it with your resume

- **On-call 10+ pages/week → 0:** Frame this as eliminating the *failure source*, not tuning alerts. Replacing tunnel dependencies with secure public management APIs (RBAC, IP restrictions, mTLS) removed the class of failures that generated UK-India shift pages — the SRE-correct move: kill the toil/page source rather than respond faster.
- **Incident resolution +20% via alarm-context enrichment:** This is MTTR reduction by collapsing the diagnose phase — enriching 2,442 Jira tickets across 6 teams with inline alarm context cut "time-to-context," which is where MTTR is usually actually lost.
- **8-step live migration with health checks + production guardrails:** A textbook progressive-rollout-with-guardrails story — each step gated by health checks with a halt/rollback path, protecting live traffic with bounded blast radius.
- **Weekly AI ops reporting pipeline clustering incidents (240 dev-hrs/mo, 15 teams):** Toil elimination plus postmortem signal — clustering incidents surfaces recurring contributing factors and reclaims engineering time that would otherwise be linear-scaling operational work.
- **Avoided 300+ security tickets:** Designing the failure away (the strongest form of toil elimination) rather than processing the tickets — ties to the "fix the system, not the symptom" reliability mindset.

## Sources

- [Google SRE Book — Embracing Risk (error budgets)](https://sre.google/sre-book/embracing-risk/)
- [Google SRE Book — Service Level Objectives (SLI/SLO/SLA)](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook — Alerting on SLOs (burn-rate alerting)](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE Book — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [Google SRE Book — Managing Incidents (IC/Ops/Comms roles)](https://sre.google/sre-book/managing-incidents/)
- [Google SRE Book — Postmortem Culture: Learning from Failure](https://sre.google/sre-book/postmortem-culture/)
- [AWS Builders' Library — Using load shedding to avoid overload](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/)
- [AWS Builders' Library — Avoiding fallback in distributed systems](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/)
- [AWS Builders' Library — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
