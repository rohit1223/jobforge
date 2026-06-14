# Bullet bank — reusable, sourced resume lines

Skill-owned, derived by `update-master` from `master/additional-context/`. Each `##`
entry is one polished, ATS-clean résumé line plus matchable tags. `in_master: true`
means it's already in `resume.tex`. `strength: strong` = sourced and resume-grade;
`emerging` = draft, quarantined from promotion. Numbers missing a real figure carry
`[QUANTIFY: …]` and block promotion. **Do not hand-author facts here without a
source in `master/additional-context/`.**

---

## Region/realm build — 30 days to 8 hours
- bullet: Reduced OCI API Gateway new-region and new-realm build time from \textbf{30 days to 8 hours} by redesigning the build workflow, replacing ticket-driven dependencies with Terraform automation, and streamlining policy serialization and tenancy-aware provisioning.
- skills: [Terraform, IaC, cloud-provisioning, automation, multi-region]
- domain: [platform, cloud-infra, control-plane]
- company: Oracle (OCI API Gateway)
- metrics: [30d→8h]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## ARM adoption — 34 production regions
- bullet: Led ARM adoption and mixed-shape platform validation across \textbf{34 production regions in 4 rollout phases}, enabling API Gateway to run across x86 and ARM while addressing capacity bottlenecks through performance testing, shard sizing, and staged production rollout.
- skills: [ARM, performance-testing, capacity-planning, rollout, distributed-systems]
- domain: [platform, cloud-infra]
- company: Oracle (OCI API Gateway)
- metrics: [34 regions, 4 phases]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## State-tier footprint — 68.4% reduction via live migration
- bullet: Cut state-tier capacity footprint by \textbf{68.4\% in OC1} — eliminating \textbf{357 cores} and reducing large-region usage from \textbf{63 to 18 OCPUs per region} — with an 8-step automated live-migration workflow for Redis-based state services using strict sequencing, health checks, and production guardrails.
- skills: [Redis, live-migration, capacity-optimization, automation, reliability]
- domain: [platform, reliability, cloud-infra]
- company: Oracle (OCI API Gateway)
- metrics: [68.4%, 357 cores, 63→18 OCPUs]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## On-call pages — 10+/week to 0
- bullet: Cut access- and setup-related on-call pages from \textbf{10+ per week per UK–India shift to 0} by exposing secure public management APIs, removing tunnel dependencies, and enforcing tenant validation, RBAC, IP restrictions, and mTLS ingress.
- skills: [API-security, RBAC, mTLS, on-call-toil, reliability]
- domain: [reliability, platform, security]
- company: Oracle (OCI API Gateway)
- metrics: [10+/wk→0]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## Ops Copilot RAG — hybrid retrieval, <9s
- bullet: Built an internal operations copilot over runbooks, docs, PDFs, HTML, tables, and multi-team knowledge bases, keeping retrieval latency \textbf{under 9 seconds} and cutting indexing time from \textbf{hours to minutes} via hybrid BM25/vector search, citation-aware responses, batch embeddings, and incremental indexing.
- skills: [RAG, BM25, vector-search, Spring AI, OCI GenAI, embeddings, Lucene]
- domain: [AI-ops, search, platform]
- company: Oracle (OCI API Gateway)
- metrics: [<9s retrieval, hours→minutes indexing]
- strength: strong
- source: additional-context/achievements.md#rag-ops-copilot
- in_master: true

## Jira alarm-context enrichment — 203.5 hours saved
- bullet: Saved \textbf{203.5 engineering hours} in API Gateway and improved incident resolution time by \textbf{20\%} by automating Jira alarm-context enrichment across \textbf{2,442 tickets}; onboarded \textbf{6 teams} to the workflow.
- skills: [automation, Jira, incident-tooling, LLM, cross-team-onboarding]
- domain: [AI-ops, reliability]
- company: Oracle (OCI API Gateway)
- metrics: [203.5 hrs, 20%, 2442 tickets, 6 teams]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## Weekly ops reporting pipeline — 240 dev-hours/month
- bullet: Saved approximately \textbf{240 developer hours per month} across \textbf{15 teams} by launching an AI-assisted weekly operations reporting pipeline that clusters incidents, summarizes recurring themes, generates HTML reports, and publishes standardized outputs automatically.
- skills: [LLM, reporting-automation, clustering, incident-analysis]
- domain: [AI-ops, reliability]
- company: Oracle (OCI API Gateway)
- metrics: [240 hrs/mo, 15 teams]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## Performance-testing modernization — Java 21, 300+ security tickets avoided
- bullet: Modernized the API Gateway performance-testing stack by migrating from legacy Canary to Test Service, upgrading to \textbf{Java 21} and a new framework, and building the supporting infrastructure; retired legacy instances and avoided more than \textbf{300 security tickets} across \textbf{34 production regions}.
- skills: [Java 21, performance-testing, Terraform, security-remediation, migration]
- domain: [platform, security, reliability]
- company: Oracle (OCI API Gateway)
- metrics: [Java 21, 300+ tickets, 34 regions]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## Orchestrator admin plane — V2 API, 16 named resources
- bullet: Re-architected the Orchestrator admin plane with a production-ready V2 API spanning \textbf{16 named resources}, modernized pagination and query behavior, decoupled API contracts from persistence through a DTO layer, and enabled parallel V1/V2 migration with no data-model changes.
- skills: [API-design, DTO, pagination, backend, migration]
- domain: [platform, control-plane, API]
- company: Oracle (OCI API Gateway)
- metrics: [16 resources]
- strength: strong
- source: additional-context/achievements.md
- in_master: true

## Ticket Context Writer — ~74,000 incidents enriched (strengthens Jira enrichment)
- bullet: Scaled an automated incident-context writer that enriches new alarm tickets in \textbf{~10 seconds} with runbook, log, dashboard, and evidence links across \textbf{10 OCI services}, writing context for roughly \textbf{74,000 incidents} and saving on-call engineers 4–5 minutes of manual lookup per ticket.
- skills: [automation, incident-tooling, RCA, Jira, cross-team-onboarding]
- domain: [AI-ops, reliability]
- company: Oracle (OCI API Gateway)
- metrics: [~74,000 incidents, 10 services, ~10s, 7909 Sev2 tickets]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false   # strengthens the 2,442-ticket master bullet with the larger, current numbers

## Ops Copilot RCA — auto root-cause for ~80% of on-call load
- bullet: Built the Ops Copilot RCA subsystem now used by API Gateway on-call to auto-root-cause alarms covering roughly \textbf{80\% of on-call load}, combining ticket context, logs, metrics, and LLM reasoning at \textbf{~80\% accuracy}; redesigned RCA into a shared background workflow with Object Storage reuse, saving \textbf{~11.7 engineering hours/month} on Sev2/Sev3 follow-up across \textbf{777 tickets (211 Sev2)}.
- skills: [LLM, RCA, incident-automation, Object-Storage, on-call]
- domain: [AI-ops, reliability]
- company: Oracle (OCI API Gateway)
- metrics: [80% load, 80% accuracy, 11.7 hrs/mo, 777 tickets, 211 Sev2]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: true

## User-configurable CSRF disablement — 76 requests, self-service
- bullet: Owned a customer-facing CSRF policy feature, turning a risky operator-only workaround into a layered self-service product: a Data Plane Sec-Fetch-Site same-origin path plus an explicit \textbf{trustedOrigins} allowlist, addressing \textbf{76 CSRF disablement requests} while preserving protection and auditability and cutting on-call/manual intervention.
- skills: [CSRF, web-security, API-design, Sec-Fetch-Site, customer-facing]
- domain: [security, platform, API]
- company: Oracle (OCI API Gateway)
- metrics: [76 requests]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: true

## Secure management plane v2 + OCI-OPS CLI onboarding
- bullet: Led the redesign of API Gateway's orchestrator management plane — a new \textbf{v2 Admin API} with DTOs, custom cursor pagination, and Forge/SPLAT role-protected resources — replacing fragile tunnel-based access; in production since \textbf{May 2025 with no known defects}, and onboarded API Gateway to \textbf{OCI-OPS CLI} so operators administer it through standard tooling across commercial and government realms.
- skills: [API-design, Forge, SPLAT, RBAC, CLI, security-review]
- domain: [platform, control-plane, security]
- company: Oracle (OCI API Gateway)
- metrics: [v2 Admin API, since May 2025, 0 defects]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: true   # folded into the V2 16-resource master bullet (prod-stability + OCI-OPS CLI)

## AI SRE — Jira Severity Controller for autonomous triage
- bullet: Designed and built the Jira Severity Controller that turns API Gateway service logs into automatic customer-impact assessment during the incident window — a key input to an autonomous SRE agent — with dry-run mode, alarm whitelisting, config gating, evidence trails, and re-escalation when impact surfaces later.
- skills: [SRE-automation, agents, customer-impact, severity-analysis, safety-guardrails]
- domain: [AI-ops, reliability]
- company: Oracle (OCI API Gateway)
- metrics: []
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## Hot-path state-tier alarm tuning — binomial threshold analysis
- bullet: Eliminated a recurring on-call page by replacing static alarm thresholds with \textbf{binomial probabilistic threshold analysis}, sizing per-region thresholds to fire on true positives while suppressing false positives and reducing false alarms by \textbf{~13 per month}.
- skills: [statistics, alerting, observability, on-call-toil, reliability]
- domain: [reliability, observability]
- company: Oracle (OCI API Gateway)
- metrics: [~13 false alarms/mo]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## Test coverage investment — 133 test methods across Ops Copilot
- bullet: Invested in platform test coverage alongside feature delivery, adding \textbf{133 test methods}, \textbf{47 new test files}, and \textbf{5,363 lines of test code} across \textbf{48 merged PRs} spanning RAG retrieval, RCA, ticket-context onboarding, and the agent/MCP platform.
- skills: [testing, test-coverage, quality, Java]
- domain: [engineering-rigor, AI-ops]
- company: Oracle (OCI API Gateway)
- metrics: [133 methods, 47 files, 5363 lines, 48 PRs]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## CAPA — long-standing certificate bug break-fix (OCCAPA-51637)
- bullet: Root-caused a customer gateway-deletion failure to a \textbf{2019 certificate-association-limit bug}, delivered the break-fix, and extended the resilience pattern to deployment workflows so the failure class could not recur (OCCAPA-51637).
- skills: [debugging, root-cause, certificates, resilience, CAPA]
- domain: [reliability, platform]
- company: Oracle (OCI API Gateway)
- metrics: []
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## Demos, mentoring & AI evangelism — go-to for AI adoption
- bullet: Drove API Gateway's AI adoption as a recognized go-to engineer — running regular AI workshops, presenting Orchestrator v2, Ops Copilot, RAG, and MCP work in org- and leadership-facing forums, and turning complex designs into patterns other engineers and partner teams (Exec, Test, Workflow-as-a-Service) reused in their own workflows.
- skills: [technical-leadership, mentoring, AI-adoption, cross-team-enablement, communication]
- domain: [leadership, AI-ops]
- company: Oracle (OCI API Gateway)
- metrics: []
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: true

## Generic MCP integration foundation
- bullet: Built a generic MCP (Model Context Protocol) integration foundation for the operations copilot, exposing tool-based runbook search and team knowledge stores to LLM agents and extending the platform from RAG into an agentic, tool-using support system.
- skills: [MCP, agents, LLM-tools, RAG, platform]
- domain: [AI-ops, agents, platform]
- company: Oracle (OCI API Gateway)
- metrics: []
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## Operational excellence — ~180 tickets resolved this year
- bullet: Resolved \textbf{~180 production tickets in a year} across customer issues and alarm tickets spanning Control Plane, Dataplane, Orchestrator, and infrastructure, sustaining high-volume operational ownership alongside feature delivery with timely resolution and no escalations.
- skills: [operations, incident-resolution, on-call, ownership]
- domain: [reliability, operations]
- company: Oracle (OCI API Gateway)
- metrics: [~180 tickets/yr]
- strength: strong
- source: additional-context/1rohit_kumar_draft_promo_doc.pdf
- in_master: false

## Pega install automation — 11 hours to 30 minutes (Bravo Award)
- bullet: Automated end-to-end Pega installation with Python and shell, cutting per-server setup from \textbf{11 hours to 30 minutes} and removing ~\textbf{95\%} of manual effort; recognized with the \textbf{Aquamarine Bravo Award for Innovation}.
- skills: [Python, shell, automation, Pega, provisioning]
- domain: [platform, automation]
- company: UnitedHealth Group
- metrics: [11h→30m, 95%]
- strength: strong
- source: additional-context/achievements.md
- in_master: true
