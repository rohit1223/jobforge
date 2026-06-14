---
title: AI SRE Agents & Autonomous Incident Triage
bucket: tech
sources: https://incident.io/blog/what-is-ai-sre-complete-guide-2026, https://sre.google/workbook/eliminating-toil/
depth: deep
added: 2026-06-13
generated: true
---

## Core concepts

### What an "AI SRE" actually is
An AI SRE is an LLM-driven agent that automates the **investigation and triage** loop of incident response — not a replacement for the on-call human. The mature framing (2025–26) is a **governed human–agent model**: the agent does the toil-heavy L1/L2 work (gather context, correlate, hypothesize) and a human stays the decision-maker for anything that mutates production. It's the direct descendant of classic SRE **toil elimination** — automating the repetitive, manual, automatable, tactical work that scales with service size.

### The autonomous-triage pipeline
A standard agent loop:
1. **Detect** — consume the alert/signal from the monitoring pipeline.
2. **Triage** — the LLM reads the alert and *concurrently* queries metrics, traces, logs, and recent changes.
3. **Correlate** — surface probable root cause + similar historical incidents (this is where **RAG over runbooks/postmortems** lives).
4. **Remediate** — for *known* failure classes only, execute **pre-approved runbooks** (restart, scale, drain, roll back).
5. **Escalate** — when confidence is below a configurable threshold, hand to a human with the evidence trail attached.

### Confidence routing — the core design decision
Not all agent outputs need the same bar. For **suggestions** (root-cause hypotheses), high-but-imperfect precision is fine — a human verifies, and even a 70%-right hypothesis saves minutes. For **autonomous actions** (rollback, scale, config change), the bar is much higher and **human approval is mandatory** above a risk line. So you route by `(action_risk, confidence)`: read-only investigation can be fully autonomous; destructive/production-mutating actions require sign-off.

### Guardrails (the part that makes it shippable)
- **Block destructive actions** unless a human approves; gate higher-risk prod changes behind explicit sign-off.
- **No-loop rule**: if a remediation runs twice and the problem persists, *escalate* rather than retry forever.
- **Dry-run mode / shadow mode**: the agent proposes and logs what it *would* do before it's trusted to act — exactly how you de-risk a new failure class.
- **Allow/deny lists (whitelisting)** scope which alarms/services/actions the agent may touch.
- **Anomalous-behavior kill switch**: stop an agent that's acting outside expected bounds.
- **Auditability**: every step transparent and explainable — engineers must see *which data* led to a recommendation, or they won't trust (or be able to debug) it.
- **Expand autonomy only after a failure class proves reliable** under those boundaries — never big-bang.

### Failure modes & gotchas
- **Hallucination**: an LLM produces a *confident but wrong* diagnosis — dangerous precisely because it's plausible. Mitigate with grounding (RAG citations), confidence thresholds, and human verification on action.
- **Tool-calling failures**: production data shows **3–15%** tool-call failure rates — the agent must degrade gracefully and escalate, not silently stall.
- **Novel incidents**: no historical precedent = the agent's weakest case; these benefit *most* from human-in-the-loop escalation, not autonomous action.
- **Automation that creates toil**: a brittle agent that needs constant babysitting is negative-value — the toil test still applies to the automation itself.

### Tuning knobs that matter
The confidence/risk thresholds for auto-act vs escalate; the action allow-list per service; dry-run vs live per failure class; the RAG corpus freshness (stale runbooks = wrong remediations); and the no-loop / retry-limit settings.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through how you'd design an agent that triages on-call alerts. Where does it act autonomously and where does it stop?</summary>

Pipeline: detect → triage (LLM concurrently pulls metrics/traces/logs/recent changes) → correlate (RAG over runbooks + similar past incidents for a root-cause hypothesis) → remediate *only known classes via pre-approved runbooks* → escalate below a confidence threshold. The split is by `(action_risk, confidence)`: read-only investigation and hypothesis generation run fully autonomously because a wrong guess is cheap and human-verified; anything that mutates production (rollback, scale, config) requires human sign-off above a risk line. That governed split is what makes it safe to ship.

</details>

<details>
<summary><strong>Q:</strong> An LLM agent confidently proposes a root cause that's wrong. How does your design keep that from causing an outage?</summary>

Three layers: (1) **grounding** — the hypothesis must cite the evidence (RAG over runbooks/logs) so it's explainable and falsifiable, not a vibe; (2) **confidence routing** — a hypothesis is a *suggestion* for a human, never an auto-action, so a wrong guess wastes a glance, not production; (3) **action guardrails** — any remediation it does take is restricted to pre-approved runbooks on whitelisted services with a no-loop limit. Hallucination is acceptable in the *suggestion* lane precisely because nothing destructive happens without human approval.

</details>

<details>
<summary><strong>Q:</strong> What's the "no-loop" guardrail and why is it essential?</summary>

If a remediation script runs and the problem persists, a naive agent re-runs it — and can thrash, mask the real issue, or amplify damage. The no-loop rule caps retries: run once (maybe twice), and if the condition holds, *escalate to a human* instead of continuing. It encodes humility — the agent assumes that a remediation that didn't work means it doesn't understand the incident, which is exactly when a human should take over.

</details>

<details>
<summary><strong>Q:</strong> How do you safely roll out a new autonomous remediation? (Tie to your own work.)</summary>

Shadow/dry-run first: the agent proposes and logs what it *would* do without acting, so you can measure precision against what the human actually did. Only after that failure class proves reliable do you promote it to act, still scoped by an allow-list and a confidence threshold. That's exactly how I built the Jira Severity Controller — it does customer-impact assessment with **dry-run mode, alarm whitelisting, config gating, and re-escalation** when impact surfaces later, so autonomy expanded per failure class instead of all at once.

</details>

<details>
<summary><strong>Q:</strong> Why is RAG over runbooks central to an AI SRE, and what breaks it?</summary>

The agent's correlation/remediation quality is bounded by what it can retrieve — runbooks, past postmortems, config docs — so RAG is how it grounds hypotheses in *your* environment rather than generic LLM priors, and how it cites evidence for human trust. What breaks it: a **stale corpus** (it'll confidently apply a deprecated runbook), poor retrieval (misses the relevant doc), and missing citations (engineers can't verify, so they won't trust it). Corpus freshness and citation discipline are first-class reliability concerns, not nice-to-haves.

</details>

<details>
<summary><strong>Q:</strong> Where should a human stay in the loop, and where is full autonomy fine, in 2026 practice?</summary>

Full autonomy is fine for read-only investigation: pulling and correlating telemetry, generating hypotheses, drafting the incident timeline. Humans stay in the loop for production-mutating actions (rollback, scale, config), for novel failure classes with no precedent, and for anything above the risk/confidence line. The consensus is a *governed* model — automate L1/L2 triage, RAG over runbooks, expand autonomy only as each failure class earns trust — not wholesale on-call replacement.

</details>

<details>
<summary><strong>Q:</strong> Tool-calling failure rates run 3–15%. How does that shape the architecture?</summary>

It means the agent must treat its own tools as unreliable dependencies: wrap calls with timeouts/retries-with-limits, validate outputs before reasoning on them, and **fail toward escalation** — if it can't gather the evidence, it hands a partial context to a human rather than guessing. It also argues for keeping a human-readable evidence trail at every step, so when a tool call silently returns garbage, the on-call can see the gap instead of inheriting a confident-but-unfounded conclusion.

</details>

<details>
<summary><strong>Q:</strong> How is an AI SRE just "toil elimination," and why does that framing matter?</summary>

Classic SRE defines toil as manual, repetitive, automatable, tactical work that scales linearly with the service — exactly the L1/L2 triage grind (gather context, check the usual suspects, write the ticket). An AI SRE automates that loop, which is why the same discipline applies: if the agent itself becomes toil (constant babysitting, brittle prompts), it's failing the test. Framing it as toil elimination keeps the goal honest — free human attention for novel, judgment-heavy work — rather than chasing autonomy for its own sake.

</details>

<details>
<summary><strong>Q:</strong> What metrics tell you the AI SRE is actually helping, not just adding risk?</summary>

Leading: triage/MTTR reduction on the failure classes it covers, hypothesis precision (how often its top root cause is right, measured against human conclusions), and escalation rate trending the right way as classes mature. Guardrail health: tool-call failure rate, no-loop trips, and how often a human had to override an auto-action. If MTTR drops but overrides and false remediations climb, the autonomy expanded faster than trust was earned — pull it back to dry-run for those classes.

</details>

## Say it with your resume
- **Jira Severity Controller** → your concrete autonomous-triage system: customer-impact assessment in the incident window with dry-run, alarm whitelisting, config gating, evidence trails, re-escalation — textbook guardrails + confidence routing.
- **Ops Copilot RCA (80% of on-call load, ~80% accuracy)** → the correlate/hypothesize stage at production scale, with a feedback loop improving accuracy over time.
- **Ops Copilot RAG (hybrid BM25/vector, citations)** → the grounding layer: RAG over runbooks/docs with citations is *exactly* what keeps an AI SRE honest.
- **Generic MCP integration** → tool-using agents: how the LLM safely reaches the runbook/knowledge tools.

## Sources
- [incident.io — What is an AI SRE (2026 guide)](https://incident.io/blog/what-is-ai-sre-complete-guide-2026)
- [Google SRE Workbook — Eliminating Toil](https://sre.google/workbook/eliminating-toil/)
