# Gap Report — Constantinople, Senior Software Engineer

## Weighted Match Score: ~58 / 100

Strong on the **seniority signals** the role screens for (architecture, scalable systems, end-to-end ownership, mentoring, AI-native platform building) but has a **hard stack mismatch** on the role's core language requirement. The JD is explicit: *"Hands-on experience with Node.js and TypeScript in production environments."* The resume is a Java/Python platform-engineering profile with **no Node.js, TypeScript, or React**. That single gap is the dominant risk and caps a higher score regardless of how well the leadership criteria match.

### Per-bucket coverage

| Bucket | Coverage | Notes |
|---|---|---|
| Tech (core) | ~45% | Architecture/API/scalability ✅; **Node.js ❌, TypeScript ❌, React ❌** — the named must-haves are missing |
| Soft / Leadership | ~95% | Mentoring, leading engineers, cross-team, tech leadership all strongly evidenced |
| Experience | ~90% | End-to-end ownership, performance/design decisions, platform reliability all present |
| Domain | ~50% | Fintech ❌ (not required); regulated ⚠️ (healthcare); AI-native ✅ strong fit |

## Strengths to surface

1. **Scalable systems architecture & software design** — V2 API surface (16 resources), DTO-layer decoupling, control planes, 34-region rollout. Directly answers "deep understanding of software design principles and scalable systems architecture."
2. **End-to-end feature ownership (idea → production)** — Ops Copilot, live-migration workflow, V2 API all built and owned to production. Direct match.
3. **Leading & mentoring engineers** — "Develop and drive architectural changes while leading engineers" maps to "led ARM adoption across 34 regions, leading engineers."
4. **AI-native platform building** — Constantinople is "AI-native banking"; resume's Ops Copilot (RAG, hybrid BM25/vector), AI reporting pipeline, and ticket-enrichment automation are an unusually strong culture/mission fit.
5. **Service performance & design decisions** — perf testing, shard sizing, capacity planning, 68.4% footprint reduction → "provide decisions on service performance and design implementation."
6. **Secure platform** — mTLS, RBAC, IP restrictions, tenant validation, 300+ security tickets avoided → "support a secure and functional platform."

## Genuine gaps

- ⚠️ **CONFIRM — Node.js (production):** Core must-have, absent. Do you have *any* real Node.js production exposure (side scripts, tooling, internal services)? If yes we can surface it honestly. If no, this is the headline gap.
- ⚠️ **CONFIRM — TypeScript (production):** Same. The Ops Copilot / AI tooling — was any of it built in TS/Node, or all Python?
- ⚠️ **CONFIRM — React / React Native:** "Strong plus." Any frontend work at all (even internal dashboards / the API Developer Portal UI)?
- **Serverless AWS:** "Highly desirable." Resume lists AWS but the deep work is OCI/Terraform. Any Lambda/API Gateway-serverless/Step Functions experience?
- **Domain-Driven Design / event-driven systems:** "Bonus." The live-migration workflow and orchestrator are adjacent; can be framed as event-driven if accurate.

## Prioritized edit list

The resume cannot manufacture Node/TS/React experience — and shouldn't. The strategy is to **maximize the seniority + AI-native + architecture signals** the role values, reframe transferable work in the JD's language, and let the cover letter address the stack gap directly (strong senior engineers cross languages).

1. **Summary** — add "software design," "scalable systems architecture," and "AI-native" framing; lead with end-to-end ownership and technical leadership. *(content reword, no new facts)*
2. **Skills** — surface API design / REST, event-driven & DDD-adjacent language *only if true*; keep AWS visible. Add a **"Learning/Working toward"** line for Node.js/TypeScript **only if you have genuine in-progress exposure** — otherwise leave out (don't fabricate).
3. **Experience bullets** — reword the V2 API and live-migration bullets to foreground "software design principles," "event-driven," and "service performance/design decisions" in the JD's vocabulary (facts unchanged).
4. **AI-native bullets** — keep Ops Copilot + AI reporting prominent; this is the biggest differentiator for an AI-native banking platform.
5. **Cover letter (recommended for this one)** — the JD explicitly asks for one. Address the Node/TS gap head-on: senior-level architecture + fast language transfer + AI-native mission alignment.

## Recommendation

This is a **stretch application** worth doing **with a cover letter**, because the role weights senior architecture/leadership/AI-native fit heavily and treats fintech as optional — but go in clear-eyed that Node.js/TypeScript is a screening must-have you don't currently meet on paper. Answer the four ⚠️ CONFIRM questions above and I'll tailor accordingly.
