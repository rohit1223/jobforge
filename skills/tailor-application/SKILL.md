---
name: tailor-application
description: Tailor a LaTeX resume to a specific job posting and produce an ATS-optimized PDF. Given a career-page URL (or pasted job text), it fetches the posting, extracts must-have/nice-to-have keywords, scores the resume against them, writes a gap report, then on approval rewrites a copy of the master resume (content only) and compiles it to PDF. Use when the user wants to apply for a job, tailor/customize their resume to a posting, run an ATS gap analysis, or mentions a job link plus their resume.
---

# tailor-application

Tailors `master/resume.tex` to one job and emits an ATS-optimized PDF. **Two phases with a human gate:** analysis (report) → approval → rewrite + compile.

## Conventions

- **Master (read-only source of truth):** `master/resume.tex`. Never edit it. If absent, stop and ask the user to place it there.
- **Per-application artifacts:** `applications/<Company>_<Role>/` containing `job.md`, `keywords.md`, `gap-report.md`, `resume-tailored.tex`, `resume-tailored.pdf`.
- `<Company>_<Role>` uses PascalCase, no spaces (e.g. `Sensorfact_DevOpsEngineer`).

## Workflow

### Phase 1 — Analysis (always runs)

1. **Resolve the job posting.** If given a URL, `WebFetch` it. If the page is JS-rendered/empty (common with Ashby, Greenhouse, Lever), try the provider's public API:
   - Ashby: `https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true`
   - Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<org>/jobs/<id>`
   - Lever: `https://api.lever.co/v0/postings/<org>/<id>`
   If still empty/blocked, **stop and ask the user to paste the job text** — never write a placeholder/garbage `job.md`. Save the full posting verbatim to `job.md`.
2. **Extract keywords** → `keywords.md`. Bucket into **tech / soft / experience / domain / certs**; tag each **MUST** (job says "required", "X+ years") vs **nice** ("preferred", "no need to be an expert"). Mark each present/absent in the resume.
3. **Gap report** → `gap-report.md`. Compute a **weighted match score** (must-haves heavy), show **per-bucket coverage**, list strengths to surface and a **prioritized edit list**. Flag genuine gaps `⚠️ CONFIRM` and missing numbers `[QUANTIFY: …]`.
4. **Feed interview-prep.** If `interview-prep/` exists (skip silently otherwise):
   - Append a `## From <Company> (<Role>)` section to `interview-prep/suggested.md` listing this JD's important keywords as ranked `- Title — one-line why` items (the format the interview-prep build parses): matched, resume-proven keywords are revision candidates; genuine gaps get a "(gap — learn)" suffix. Skip topics already in `interview-prep/topics/` (compare slugs) or already listed anywhere in `suggested.md`.
   - Write `applications/<Company>_<Role>/prep.yml` — the job-prep manifest behind the dashboard's job switcher (schema in interview-prep's SKILL.md): map keywords to existing topic slugs with judgment (alias-aware); JD must-tier ⇒ `must: true`; rank by JD weight; add a one-line `angle:` per generated topic tying their stack to the resume; entries without a topic file get `title` + `why`. Ask before overwriting an existing `prep.yml`.
5. **Stop and present the report.** Phase 1 may be the whole job.

### Phase 2 — Rewrite + compile (only after approval)

6. **Per-edit triage, conversationally.** Walk proposed edits with the user in batches (old→new, why, flags). **Truthfulness policy:** only re-surface facts already true; you MAY draft a bullet for a real gap but tag it `% UNVERIFIED — confirm true` and require explicit per-edit approval. Never silently invent. Numbers you don't have become `[QUANTIFY: …]`.
7. **Write `resume-tailored.tex`** = copy of master + approved edits. **Content only** — never touch the preamble, packages, fonts, or layout.
8. **Ensure toolchain, then compile:** run `scripts/ensure-toolchain.sh` then `scripts/compile-resume.sh <dir>/resume-tailored.tex`. See **Toolchain** below. The compile script auto-installs missing LaTeX packages, reverts to no PDF on error, and **warns if the PDF exceeds 1 page**.
9. **ATS self-check.** The compile script extracts `resume-tailored.txt` from the PDF via `pdftotext` (the text an ATS actually parses). Verify every MUST keyword from `keywords.md` appears in it, case-insensitively; list any that didn't survive (e.g. lost in a glyph/ligature) so they can be re-worded. If `pdftotext` is unavailable the script prints the `brew install poppler` hint — note the check was skipped.
10. **Write `status.yml`** in the application dir — flat `key: value` lines only (a non-YAML parser reads it):
    ```yaml
    company: <Company>
    role: <Role>
    url: <posting url or empty>
    applied:            # YYYY-MM-DD, fill when actually submitted
    stage: tailored     # tailored | applied | interview | offer | rejected
    next_interview:     # YYYY-MM-DD when scheduled
    notes:
    ```
    The interview-prep dashboard renders these files as an **Applications tracker** pane (with a next-interview countdown). The user updates `stage`/`next_interview` by hand or by asking.
11. **Report** the final score, the diff summary, the PDF path, the ATS-check result, and any `UNVERIFIED`/`QUANTIFY` markers the user must still resolve.

## Cover letter (optional, on request)

When the user asks for a cover letter, write `applications/<Company>_<Role>/cover-letter.md` from `job.md` + the tailored resume (fall back to the master if no tailored copy exists):

- **250–350 words**, plain markdown, no letterhead — concrete and specific, never generic filler.
- Map **2–3 real achievements** from the resume to the JD's top must-haves; name the company and role; close with a direct ask.
- The Phase 2 **truthfulness policy applies verbatim**: only facts the resume already proves; anything unverifiable is tagged `UNVERIFIED — confirm true` and needs explicit approval; missing numbers become `[QUANTIFY: …]`.

## Toolchain (auto-install)

`scripts/ensure-toolchain.sh` checks for `pandoc`, `pdflatex`, and `tlmgr`:
- Installs `pandoc` via Homebrew automatically (no sudo).
- BasicTeX and `tlmgr install` need **sudo**, which requires a real TTY. Neither the agent's Bash tool **nor Claude Code's `!` inline prompt** provides one — sudo fails there with "a terminal is required to read the password". So the **one-time BasicTeX install must be run by the user in a real terminal window (Terminal.app / iTerm):** `brew install --cask basictex`. The script attempts it, and on sudo failure prints that instruction and exits with code 2. When you see exit 2, tell the user to run it in an actual terminal app (not the `!` prompt) and wait for them to confirm.
- Once `pdflatex` exists, `compile-resume.sh` resolves missing `.sty` files iteratively via `tlmgr search --file`.

## Formatting audit (one-time, separate from per-job runs)

When asked, audit `master/resume.tex` (not a copy): flag multi-column layout, non-ATS fonts, tables-as-layout, icon glyphs, and >1 page. Output suggestions; do not auto-change the master's layout. Per-job runs never touch formatting.
