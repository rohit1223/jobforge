---
name: interview-prep
description: Build and grow a self-contained interview-prep dashboard (single SPA HTML) for SENIOR-level revision of topics you can defend, drawn from your resume and the matched keywords of job gap reports, plus on-demand deep dives on any topic at a chosen depth. Each topic gets deep mental-model concepts (internals, trade-offs, failure modes, tuning) and seniority-calibrated interview questions as a click-to-reveal self-quiz, all grounded in official docs (Context7 first). Five modes: build/refresh (throttled to ~3 topics/run + a suggested backlog), add-topic <name> [--depth=quick|standard|deep], add-note, mock <topic|all> (interactive mock interview graded against the topics' model answers), and prep-for <Company_Role> (writes the per-job prep.yml manifest behind the dashboard's job switcher, reusing shared topics across jobs). Use when the user wants to revise/prep for interviews, prep for a specific job/role, deepen or explore a topic, build a study dashboard, be mock-interviewed, or add a note from a link/document. See USAGE.md for the user-facing guide.
---

# interview-prep

A global, repo-wide study dashboard that complements `tailor-application`. Its job is **deep revision of matched, defensible topics** — the things your resume already proves and the role needs — at a level suited to a senior/staff engineer (9+ years). **One skill, five modes:** build/refresh the dashboard, add a topic, add a note, a mock interview, and `prep-for` (a per-job manifest powering the dashboard's job switcher).

> **Scope note:** This skill is for *revision of what you match*, not closing gaps. Pure gaps (tools you haven't used) are out of scope here and belong to a separate topic-learning mode. Only include topics the resume genuinely demonstrates.

## Conventions

- **Data dir (source of truth, git-tracked):** `interview-prep/` at the repo root.
  ```
  interview-prep/
  ├── topics/<slug>.md   # one per topic
  ├── notes/<slug>.md    # one per note
  └── index.html         # generated build artifact (gitignored)
  ```
- **Build:** `jobforge-build interview-prep` renders every `.md` (via `pandoc`) into one self-contained `index.html` (inline CSS/JS, sidebar nav, collapsible Q&A). Run it after any `.md` change.
- **Topic frontmatter (intrinsic fields only):** `title`, `bucket` (tech/soft/experience/domain), `learning` (bool — a topic you can't yet fully defend; shows a "learning" badge), `depth` (`quick`/`standard`/`deep`), `sources` (url; comma-separate multiple), `added` (YYYY-MM-DD — Modes 1 and 3 MUST stamp this on every new topic), `updated` (YYYY-MM-DD, set on `--refresh`), `generated` (bool — `true` until a human edits it). The build shows a "generated N months ago" staleness hint once `updated`/`added` passes 60 days. **`must` and `rank` are job-relative and live in `prep.yml`, not topic frontmatter.** Optional `companies` (`[A, B]` or `A, B`) hand-tags a topic to companies it isn't otherwise linked to; normally you don't set it — company tags are **auto-derived** from which jobs' `prep.yml` reference the topic.
- **Company tags & filter:** every topic shows a chip per company that includes it (a company = the `<Company>` prefix of any `applications/<Company>_<Role>/` whose `prep.yml` lists the topic, unioned with any explicit `companies:` frontmatter). The dropdown carries a **"By company"** group (filter across all of a company's roles) alongside the per-role **"By role"** group — both feed the same sidebar/quiz filtering. No manual upkeep: adding a `prep.yml` topic entry tags it automatically on the next build.
- **Job-prep manifest:** `applications/<Company>_<Role>/prep.yml` — `job:` display name + `topics:` list of entries `slug`, `must` (bool), `rank` (int), `angle` (one-line job-specific framing shown as a callout in that job's view); not-yet-generated entries carry `title` + `why` and appear as "Suggested for this job". The dashboard's job switcher is driven entirely by these files; the All view aggregates them (must in any job, min rank).
- **Note frontmatter:** `title`, `source` (url/path), `added` (YYYY-MM-DD), `generated: true`.
- **Suggested backlog:** `interview-prep/suggested.md` — a ranked markdown list `- Title — one-line why` of matched topics not yet generated. The build renders it as a muted "Suggested · not generated" sidebar group; Mode 1 maintains it.
- **Depth tiers** (control concept richness + question count + number of doc fetches):
  | tier | questions | concepts | fetches |
  |---|---|---|---|
  | `quick` | ~5 | core mechanism + top trade-off | 1 |
  | `standard` *(default)* | 10–15 | full senior mental-model | 1–2 |
  | `deep` | ~20–25 | exhaustive + code + multiple design prompts | several |
- **`--detailed`** (modifier, orthogonal to `--depth`): fetch **more concepts** — extra doc sources/Context7 queries and an expanded **Core concepts** section that adds prerequisites/fundamentals and worked examples, without necessarily raising the question count. Use it when the topic is **new to the user** and needs more grounding (e.g. `add-topic <t> --depth=standard --detailed`). Record `detailed: true` in frontmatter when used.

## Mode 1 — build / refresh the dashboard  (throttled)

1. **Derive matched topics.** Scan all `applications/*/keywords.md` + `gap-report.md` and `master/resume.tex`. Select only topics the **resume genuinely demonstrates** (skip pure gaps — those are Mode 2). Rank **JD-must-have first, then resume strength / cross-job frequency.**
2. **Throttle: generate only the top ~3 not-yet-built topics** this run (default 3; honour `--count N` if given). This avoids doc-fetch rate-limits — do NOT fetch all topics at once.
3. **Write the rest to `suggested.md`** as a ranked `- Title — one-line why` list (skip ones already in `topics/`). 
4. **Source official docs** for each generated topic — see **Doc sourcing**. Use `standard` depth. Record the URL in `sources`; set `depth: standard`.
5. **Write `topics/<slug>.md`** (`generated: true`) using the **deep content template** below. Skip existing files unless `--refresh <slug>`.
6. **Rebuild** (`jobforge-build`), then tell the user: the path to open, the ~3 topics generated, and the **suggested next** topics (re-run Mode 1 for the next ~3, or `add-topic <name>` for a specific one).

## Mode 3 — add a topic on demand  (`add-topic <topic> [--depth=quick|standard|deep] [--detailed]`)

1. Generate **one named topic** — matched OR a gap you want to learn — at the requested depth (default `standard`; see the depth-tier table above for what each controls).
2. **`--detailed`**: when set, fetch **more concepts** — pull from additional doc sources/Context7 queries and expand the **Core concepts** section with prerequisites/fundamentals and worked examples (the question count still follows `--depth`). Default this **on** for topics flagged `learning` / unfamiliar, since a new topic needs more grounding. Record `detailed: true` in frontmatter.
3. **Source official docs** per **Doc sourcing**, scaling fetch breadth to depth (and wider when `--detailed`). Write `topics/<slug>.md` (`generated: true`, `depth: <tier>`, `detailed:` if used). If the resume can't yet defend it, set `learning: true`. Remove it from `suggested.md` if present; if a `prep.yml` lists the slug as not-yet-generated, it now resolves automatically on rebuild.
4. **Rebuild** with `jobforge-build`. Not throttled — this is an explicit single topic.

### Deep content template (this is the quality bar — not an overview)

```markdown
## Core concepts
Senior mental-model, cited throughout. Cover, with real depth:
- **How it actually works** — the mechanism/internals, not just component names.
- **Key trade-offs** — the decisions and when to choose what.
- **Failure modes & gotchas** — what breaks in production and why.
- **Tuning knobs** — the few config/levers that matter at scale.

## Interview questions
10-15 questions calibrated for 9+ years (NO "what is X" recall). Mix:
mechanism/"why & what breaks", trade-off/comparison, debugging/incident scenarios,
1-2 system-design prompts, and 1-2 experience questions tied to the resume.
Each as a click-to-reveal self-quiz block:

<details>
<summary><strong>Q:</strong> The question, posed as an interviewer would.</summary>

A crisp, correct, senior-level model answer — 3-6 sentences, with the
trade-off/why, doc-aligned. Code or commands where it sharpens the point.

</details>

## Say it with your resume
- Tie each strength to a real master/resume.tex achievement (paraphrased), so the
  candidate can pivot any question into evidence from their own work.

## Sources
- [official-doc-title](https://…)
```

Authoring notes: leave a blank line after `<summary>` and before `</details>` so pandoc renders the answer markdown. The build styles `<details>` as collapsible self-quiz rows automatically.

## Mode 2 — add a note  (`<url | local file path>`)

1. **Fetch/convert:** public URL → `WebFetch`; `.md`/`.txt` → read directly; `.docx` → `pandoc`; `.pdf` → `pdftotext` (install poppler if missing: `brew install poppler`). Auth-gated sources → ask the user to paste/export.
2. **Distill 80/20**, doc-grounded, into `notes/<slug>.md` (`generated: true`), citing the `source`. Same right-pane shape; appears under the sidebar **Notes** group. (Notes may use the same collapsible Q&A blocks where useful.)
3. **Rebuild** with `jobforge-build`.

## Mode 4 — mock interview  (`mock <topic|all> [--count N]`)

1. **Source questions** from the `<details>` self-quiz blocks of `interview-prep/topics/<slug>.md`. `all` samples across topics, weighted toward `must` and `learning` ones. Default `--count 8`. Realistic improvised follow-ups are fine, but stay grounded in the topic files' content.
2. **Ask ONE question at a time**, phrased as an interviewer would, and wait for the user's answer before continuing. Never dump answers.
3. **Grade each answer** strong / partial / missed against the model answer, with 1–2 sentences of specific feedback (what was missing or wrong), then ask the next question.
4. **Close with a session log:** write `notes/mock-log-<slug-or-all>-<YYYY-MM-DD>.md` (frontmatter: `title`, `added`, `generated: true`) summarizing per-question grades and the weak areas to drill, then rebuild with `jobforge-build`. Never modify the topic files themselves.

## Mode 5 — job-prep manifest  (`prep-for <Company_Role>`)

1. Read `applications/<Company_Role>/keywords.md` (+ `gap-report.md` if present). If neither exists, stop and suggest running tailor-application first.
2. **Map keywords → topic slugs with judgment** (aliases matter: "Prometheus / Loki / Tempo" → `observability`, "Kubernetes (EKS)" → `kubernetes` + `aws-eks`). JD must-tier keywords ⇒ `must: true`; rank by JD weight then resume strength.
3. Write `applications/<Company_Role>/prep.yml` per the **Job-prep manifest** convention: generated topics get `slug`/`must`/`rank`/`angle` (one line tying *their* stack to the candidate's experience); JD topics with no topic file yet get `slug`/`title`/`rank`/`why` so they appear under "Suggested for this job". If a `prep.yml` already exists, ask before overwriting.
4. **Rebuild** with `jobforge-build` and tell the user the job is now selectable in the dashboard's job switcher.

## Doc sourcing (Context7 first)

- **Libraries/frameworks/tools** (Kubernetes, Terraform, AWS, Jenkins, Java…): `ToolSearch` for `context7`, then `resolve-library-id` → `query-docs` for the deep essentials.
- **Concept topics** (distributed systems, API design, reliability/SRE, RAG): `WebSearch` the authoritative source (e.g. Google SRE book, REST/Richardson, DDIA-style references) then `WebFetch`.
- Never fabricate — every topic cites its source.

## Safety rails

- **Additive refresh.** A normal refresh only adds new topic files and rebuilds; existing topics are left untouched.
- **Never clobber edits.** If frontmatter `generated:` is missing or `false`, a human edited it — ask before overwriting.
- **Notes are sacred.** A topic refresh never touches `notes/*.md`.
- Per-topic re-fetch is opt-in: `--refresh <slug>`, still asking before overwriting an edited file.
- **`--refresh-stale`**: list topics whose `updated`/`added` date is older than ~90 days and offer (ask before) re-fetching each; stamp `updated:` on refresh.
