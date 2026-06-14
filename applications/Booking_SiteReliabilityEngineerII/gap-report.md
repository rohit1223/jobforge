# Gap Report — Booking.com Site Reliability Engineer II

> **Re-tailored 2026-06-13** against the updated master + bullet bank. Score rose
> 87 → **91** after pulling SRE-specific evidence from the bank (autonomous SRE
> agent, alarm-threshold tuning, RCA) and naming SLOs on the page. The skills line
> was also corrected — speculative Prometheus / Elasticsearch / Kibana were removed
> (unsourced); only the real Grafana / Datadog stack remains. See "Re-tailor update."

## Weighted match score: **91 / 100** — excellent fit, apply

This is the strongest alignment of any role you've tailored for. The JD's
premise — "treat operational issues as a software problem, code solutions for
availability/scalability/latency, prevent recurrence with automation" — is
almost a paraphrase of your Oracle work. On-call reduction, incident tooling,
multi-region reliability, capacity testing, and IaC automation are all directly
evidenced. The role is *mid-level* (SRE II), so your 9+ years over-clear the bar
— the framing job is to make sure the resume reads as **SRE-first**, not
"software engineer who also did infra."

### Per-bucket coverage

| Bucket | Coverage | Notes |
|---|---|---|
| Experience (HA prod, on-call, incidents, multi-region) | 97% | Your single strongest area — near-verbatim matches; now + autonomous SRE agent & RCA |
| Tech — distributed systems / automation / IaC / cloud / Linux | 90% | Java/Python, Terraform, OCI/AWS, Linux all present |
| Incident mgmt — RCA / alerting / prevention | 95% | Ops Copilot RCA, Jira Severity Controller, binomial alarm tuning |
| Tech — observability tools | 50% | Grafana ✅ Datadog ✅ (honest); Prometheus/Kibana/Graphite/ES ❌ — all *nice* only |
| Tech — orchestration | 70% | Kubernetes ✅; OpenStack ❌ |
| Soft / interpersonal | 95% | Multi-team enablement, onboarding, AI-adoption workshops |
| SLA/SLO literacy | 90% | "SLOs" now named in summary + skills; alerting/threshold work backs it |
| Algorithmic problem solving | 90% | Binomial probabilistic threshold analysis now on the page (was only implied) |

## Strengths to surface (already true)

1. **On-call → 0.** "Cut access- and setup-related on-call pages from 10+ per
   week per UK–India shift to 0" is a textbook SRE win — toil eliminated by
   software. Keep it prominent; it answers "share the on-call rotation" and
   "build automation to prevent recurrence" at once.
2. **Incident tooling + faster resolution.** "Saved 203.5 engineering hours…
   improved incident resolution time by 20% by automating Jira alarm-context
   enrichment across 2,442 tickets" maps to "handle outages / build monitoring."
3. **Multi-region reliability.** Region/realm builds (30d→8h) and the 34-region
   ARM rollout map to "design systems to work across multinational data centers."
4. **Prevention automation + guardrails.** The 8-step live-migration workflow
   with health checks and sequencing is exactly "build solutions and automation
   to prevent problems from happening again."
5. **Capacity testing.** Performance testing, shard sizing, staged rollout map
   to "build and run capacity tests to handle growth."
6. **Deploy tooling for product teams.** Internal developer platform, self-service
   management APIs map to "develop tools to assist product teams deploying 1000s
   of change sets/day."

## Re-tailor update — bank lines pulled in (2026-06-13)

Three SRE-specific bullets were added from `master/bullet-bank.md` (all sourced,
no fabrication), and the Oracle block re-ordered SRE-first (on-call → incident
tooling → reliability/capacity → control-plane):

- **Jira Severity Controller / autonomous SRE agent** — automatic customer-impact
  assessment in the incident window, dry-run, alarm whitelisting, re-escalation.
  Hits the JD's "treat ops as software" ethos and "build automation to prevent
  recurrence" head-on.
- **Binomial alarm-threshold tuning** — false-alarm reduction (~13/mo). Closes the
  *algorithmic problem solving* MUST that was previously only implied, and adds a
  concrete alerting/SLO story.
- **Ops Copilot RCA** — auto root-cause for ~80% of on-call load (now in master).

Three less-SRE bullets were dropped from this copy (still in the master): RAG
`<9s>` retrieval, the AI-reporting `240 hrs` line, and the CSRF feature.

**Resolved from the prior report:** the SLA/SLO wording call (#4) — "SLOs" is now
on the page. The speculative Prometheus/ELK tools (#5) were removed, not invented.

## Prioritized edit list

1. **Summary — reframe as SRE-first.** Current opener: "Software and platform
   engineer." Lead instead with *Site reliability / platform engineer* and
   front-load reliability, on-call toil removal, incident automation, and
   multi-region availability. (No new facts — pure emphasis.)
2. **Skills — surface SRE vocabulary.** Add the verbatim terms an ATS scans for
   that your work already demonstrates: *SLIs/SLOs*, *on-call*, *incident
   response*, *capacity planning*, *high availability*. ⚠️ see #4 on SLO wording.
3. **Skills — name "distributed systems" and "Linux" cleanly** (both present;
   keep them scannable) and keep Grafana/Datadog under Monitoring.
4. **⚠️ CONFIRM — SLA/SLO wording.** The JD requires "Understanding of SLA, SLO."
   Your resume shows reliability engineering, health checks, on-call, and
   guardrails — strongly SLO-adjacent — but doesn't use the terms *SLA/SLO/error
   budget*. I'd add "service-level objectives (SLOs)" to the skills line **only
   if you can speak to it in an interview** (you almost certainly can, given the
   on-call/health-check work). Confirm and I'll include it; otherwise I'll leave
   the concept implied.
5. **Genuine tool gaps — do not invent.** Prometheus, Kibana, Graphite,
   Elasticsearch, OpenStack are ❌. These are all *nice-to-haves*, so the gap is
   low-stakes. Grafana + Datadog + Kubernetes cover the spirit. If you have real
   Prometheus/ELK exposure, tell me and I'll add a truthful line.
6. **[QUANTIFY optional]** Your bullets are already strongly quantified — nothing
   blocking.

## Genuine gaps (no fabrication)

- **Prometheus / Kibana / Graphite / Elasticsearch / OpenStack** — ❌ all
  nice-to-have only. Low impact. **Kept off the resume** (unsourced). `⚠️ CONFIRM`
  only if you have real exposure and want a truthful line added.
- **SLA/SLO as named terms** — ✅ now resolved; "SLOs" appears in summary + skills.
- **Consumer e-commerce domain** — ❌ your background is enterprise cloud, not
  consumer travel/e-commerce. Not a stated requirement.
- **Go / NodeJS** — ❌ but Java + Python satisfy "at least one backend language."

## Recommendation

Apply — this is your best-matched role (now **91/100**). The SRE-first framing plus
the bank-sourced autonomous-SRE / RCA / alarm-tuning evidence reposition the same
true facts as exactly the work this JD describes. No open `⚠️ CONFIRM` blockers
remain — the only optional add is real Prometheus/ELK exposure, if you have it.
