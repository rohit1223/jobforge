---
name: interview-prep
description: Build and grow a self-contained interview-prep dashboard (single SPA HTML) for SENIOR-level revision of topics you can defend, drawn from your resume and the matched keywords of job gap reports, plus on-demand deep dives on any topic at a chosen depth. Each topic gets deep mental-model concepts (internals, trade-offs, failure modes, tuning) and seniority-calibrated interview questions as a click-to-reveal self-quiz, all grounded in official docs (Context7 first). Three modes: build/refresh (throttled to ~3 topics/run + a suggested backlog), add-topic <name> [--depth=quick|standard|deep], and add-note. Use when the user wants to revise/prep for interviews, deepen or explore a topic, build a study dashboard, or add a note from a link/document. See USAGE.md for the user-facing guide.
---

# interview-prep

A global, repo-wide study dashboard that complements `tailor-application`. Its job is **deep revision of matched, defensible topics** — the things your resume already proves and the role needs — at a level suited to a senior/staff engineer (9+ years). **One skill, two modes:** build/refresh the dashboard, and add a note.

> **Scope note:** This skill is for *revision of what you match*, not closing gaps. Pure gaps (tools you haven't used) are out of scope here and belong to a separate topic-learning mode. Only include topics the resume genuinely demonstrates.

## Conventions

- **Data dir (source of truth, git-tracked):** `interview-prep/` at the repo root.
  ```
  interview-prep/
  ├── topics/<slug>.md   # one per topic
  ├── notes/<slug>.md    # one per note
  └── index.html         # generated build artifact (gitignored)
  ```
- **Build:** `python3 skills/interview-prep/scripts/build.py interview-prep` renders every `.md` (via `pandoc`) into one self-contained `index.html` (inline CSS/JS, sidebar nav, collapsible Q&A). Run it after any `.md` change.
- **Topic frontmatter:** `title`, `bucket` (tech/soft/experience/domain), `must` (bool — JD-required, floats to top), `learning` (bool — a topic you can't yet fully defend; shows a "learning" badge), `depth` (`quick`/`standard`/`deep`), `rank` (int; lower = higher), `sources` (url), `generated` (bool — `true` until a human edits it).
- **Note frontmatter:** `title`, `source` (url/path), `added` (YYYY-MM-DD), `generated: true`.
- **Suggested backlog:** `interview-prep/suggested.md` — a ranked markdown list `- Title — one-line why` of matched topics not yet generated. The build renders it as a muted "Suggested · not generated" sidebar group; Mode 1 maintains it.
- **Depth tiers** (control concept richness + question count + number of doc fetches):
  | tier | questions | concepts | fetches |
  |---|---|---|---|
  | `quick` | ~5 | core mechanism + top trade-off | 1 |
  | `standard` *(default)* | 10–15 | full senior mental-model | 1–2 |
  | `deep` | ~20–25 | exhaustive + code + multiple design prompts | several |

## Mode 1 — build / refresh the dashboard  (throttled)

1. **Derive matched topics.** Scan all `applications/*/keywords.md` + `gap-report.md` and `master/resume.tex`. Select only topics the **resume genuinely demonstrates** (skip pure gaps — those are Mode 2). Rank **JD-must-have first, then resume strength / cross-job frequency.**
2. **Throttle: generate only the top ~3 not-yet-built topics** this run (default 3; honour `--count N` if given). This avoids doc-fetch rate-limits — do NOT fetch all topics at once.
3. **Write the rest to `suggested.md`** as a ranked `- Title — one-line why` list (skip ones already in `topics/`). 
4. **Source official docs** for each generated topic — see **Doc sourcing**. Use `standard` depth. Record the URL in `sources`; set `depth: standard`.
5. **Write `topics/<slug>.md`** (`generated: true`) using the **deep content template** below. Skip existing files unless `--refresh <slug>`.
6. **Rebuild** (`build.py`), then tell the user: the path to open, the ~3 topics generated, and the **suggested next** topics (re-run Mode 1 for the next ~3, or `add-topic <name>` for a specific one).

## Mode 3 — add a topic on demand  (`add-topic <topic> [--depth=quick|standard|deep]`)

1. Generate **one named topic** — matched OR a gap you want to learn — at the requested depth (default `standard`; see the depth-tier table above for what each controls).
2. **Source official docs** per **Doc sourcing**, scaling fetch breadth to depth. Write `topics/<slug>.md` (`generated: true`, `depth: <tier>`). If the resume can't yet defend it, set `learning: true` (and omit `must`). Remove it from `suggested.md` if present.
3. **Rebuild** with `build.py`. Not throttled — this is an explicit single topic.

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
3. **Rebuild** with `build.py`.

## Doc sourcing (Context7 first)

- **Libraries/frameworks/tools** (Kubernetes, Terraform, AWS, Jenkins, Java…): `ToolSearch` for `context7`, then `resolve-library-id` → `query-docs` for the deep essentials.
- **Concept topics** (distributed systems, API design, reliability/SRE, RAG): `WebSearch` the authoritative source (e.g. Google SRE book, REST/Richardson, DDIA-style references) then `WebFetch`.
- Never fabricate — every topic cites its source.

## Safety rails

- **Additive refresh.** A normal refresh only adds new topic files and rebuilds; existing topics are left untouched.
- **Never clobber edits.** If frontmatter `generated:` is missing or `false`, a human edited it — ask before overwriting.
- **Notes are sacred.** A topic refresh never touches `notes/*.md`.
- Per-topic re-fetch is opt-in: `--refresh <slug>`, still asking before overwriting an edited file.
