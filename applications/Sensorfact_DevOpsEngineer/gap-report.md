# Gap Report — Sensorfact · DevOps Engineer

**Candidate:** Rohit Kumar · **Master:** `master/resume.tex` · **Job:** `job.md`

---

## 🎯 Weighted match score: **82 / 100** — Strong

Must-haves dominate the weighting; the long tech-stack list is explicitly nice-to-have ("no need to be an expert"), so missing tools cost little. Your gaps are *specific tools*, not *capabilities* — and that's the easy kind to close.

### Per-bucket coverage

| Bucket | Coverage | Notes |
|---|---|---|
| Experience / seniority | ████████░░ **95%** | 9+ yrs vs 2+ required; large-scale rollouts. Over-qualified, if anything. |
| Soft skills / attitude | █████████░ **90%** | Enabling teams, cross-functional, self-service — bullseye for "support the dev team." |
| Hard skills (capability) | ███████░░░ **78%** | IaC, CI/CD, K8s, cost, security, observability all present. |
| Hard skills (their exact stack) | ████░░░░░░ **40%** | Node.js, GitLab CI, ArgoCD, Prometheus/Loki/Tempo, Kafka, Clickhouse, MQTT missing. |
| Domain | ██░░░░░░░░ **20%** | No climate / industrial-IoT / scale-up signal. |

---

## ✅ Strengths to lead with (already true — just surface louder)

1. **Cost predictability** — JD: *"costs are predictable."* You cut state-tier footprint **68.4%, eliminated 357 cores.** This is your single strongest differentiator; most DevOps candidates can't quantify cost impact. Move it up.
2. **Infra that scales** — JD: *"ready to scale as needed."* Your 34-region, 4-phase ARM rollout is exactly this story.
3. **Developer enablement / self-service** — JD: *"support our dev team with tools, automations… empower people and enable teams."* Ops Copilot + self-service management APIs map 1:1.
4. **Terraform / IaC** — JD core; you replaced ticket-driven deps with Terraform. Direct hit.
5. **Kubernetes** — present; just needs to be visible near the top.
6. **Security in infra** — mTLS, RBAC, IP restrictions, 300+ security tickets avoided. JD wants "properly secured."

---

## ⚠️ Gaps & prioritized edit suggestions

> Per our policy: edits that **re-surface things you already have** are safe. Items needing a true/false call from you are tagged `⚠️ CONFIRM`. Missing numbers tagged `[QUANTIFY]`.

### P1 — High impact, low effort (re-surfacing true facts)

- **AWS visibility.** JD prefers AWS; your résumé leads with OCI. AWS is in your skills line but buried.
  - *Suggested skills-line edit:* `\textbf{Cloud} {: AWS, Oracle Cloud Infrastructure (OCI), Terraform}` (AWS first).
  - ⚠️ CONFIRM: How deep is your hands-on AWS? If substantial, we should add one AWS-specific bullet. If it's mostly OCI, we keep it honest and lean on transferable cloud-platform depth.

- **Kubernetes prominence.** You have it; the JD runs on EKS. Surface it in the skills line's first infra group and ensure a bullet references container orchestration.
  - ⚠️ CONFIRM: Did any of your work (Orchestrator admin plane, live-migration workflow) run on Kubernetes? If yes, naming it in that bullet is a free, true keyword.

- **CI/CD wording.** You have Jenkins; they use GitLab CI + ArgoCD. Generalize to *"CI/CD pipelines (Jenkins; pipeline-as-code)"* so the ATS matches the concept, then a draft bullet below addresses GitOps.

### P2 — Tailored summary / headline (per-job)

- **Add a target headline** above the summary: `DevOps / Platform Engineer` (JD title). Your current resume has no headline line — just the name.
- **Tailor sentence 1 of summary** toward DevOps framing: lead with "cloud infrastructure, CI/CD, and developer tooling" (all true, just reordered to match JD's first line).

### P3 — Genuine tool gaps (require your input — `⚠️ CONFIRM` before any bullet is written)

These tools are **nice-to-have** per the JD, so don't fabricate. Decide which are genuinely true:

| Tool | Have you actually used it? | If yes → draft bullet |
|---|---|---|
| GitLab CI | ⚠️ CONFIRM | `<!-- UNVERIFIED --> Built CI/CD pipelines in GitLab CI for [X], [QUANTIFY: build-time / deploys].` |
| ArgoCD / GitOps | ⚠️ CONFIRM | `<!-- UNVERIFIED --> Adopted GitOps delivery with ArgoCD for [service].` |
| Prometheus / Loki / Tempo | ⚠️ CONFIRM | You have Grafana + Datadog; if you touched Prometheus, add it to Monitoring line (true keyword, no bullet needed). |
| Node.js | ⚠️ CONFIRM | Likely leave out — you're Java/Python. JD says no need to be expert; don't claim it. |
| Kafka / Clickhouse / Postgres / MQTT | ⚠️ CONFIRM | Add only the ones you've genuinely used to the skills line. |

### P4 — Domain / culture (optional, low cost)

- **Climate angle.** JD values "saving our climate." Your **68.4% capacity reduction / 357 cores eliminated** is genuinely an energy-efficiency win — reframing one bullet to note the *efficiency/resource-reduction* impact is true and resonates culturally. No fabrication needed.

---

## 🧹 Formatting audit (one-time, on master — not per-job)

- **Length:** résumé is **2 pages** (explicit `\newpage` at line 144). JD is for ~mid-level; with 9 yrs you *can* justify 2 pages, but a 1-page version is stronger for this role. Candidate for a trimmed variant.
- **Font:** uses `tgheros` (TeX Gyre Heros / Helvetica-like, sans-serif) + FiraMono. Helvetica-clone is ATS-safe and readable — ✅ no change needed (don't force Arial; this parses fine).
- **Layout:** single-column, standard sections (SUMMARY/SKILLS/EXPERIENCE/EDUCATION) — ✅ ATS-clean. No tables-as-layout, no text boxes, no graphics. Good.
- **Icons:** uses `fontawesome5` glyphs for phone/email/LinkedIn/GitHub. Minor ATS risk — some parsers choke on icon glyphs. Plain-text labels are safer. ⚠️ Low priority.
- **Margins:** aggressively widened (textwidth +1in). Fine for print; readable.

---

## ▶️ Recommended next action

Best ROI here is **P1 + P2** (all honest re-surfacing) — that alone likely pushes the match into the high-80s. Then we triage P3 conversationally: I'll ask you tool-by-tool what's genuinely true, and only write bullets you confirm.

Say **"go"** to start the per-edit triage against `master/resume.tex` → `applications/Sensorfact_DevOpsEngineer/resume-tailored.tex`.
