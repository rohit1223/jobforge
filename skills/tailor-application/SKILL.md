---
name: tailor-application
description: Tailor a LaTeX resume to a specific job posting and produce an ATS-optimized PDF. Given a career-page URL (or pasted job text), it fetches the posting, extracts must-have/nice-to-have keywords, scores the resume against them, writes a gap report, then on approval rewrites a copy of the master resume (content only) and compiles it to PDF. Use when the user wants to apply for a job, tailor/customize their resume to a posting, run an ATS gap analysis, or mentions a job link plus their resume.
---

# tailor-application

Tailors `master/resume.tex` to one job and emits an ATS-optimized PDF. **Two phases with a human gate:** analysis (report) → approval → rewrite + compile.

## Conventions

- **Master (read-only source of truth):** `master/resume.tex`. Never edit it. If absent, the workspace isn't set up — tell the user to run `jobforge-scaffold` (then drop in their résumé, or use update-master's import mode).
- **Per-application artifacts:** `applications/<Company>_<Role>/` containing `job.md`, `keywords.md`, `gap-report.md`, `resume-tailored.tex`, `resume-tailored.pdf`.
- `<Company>_<Role>` uses PascalCase, no spaces (e.g. `Acme_DevOpsEngineer`).
- **Writing style (avoid the AI tell):** write bullets as simple, impactful sentences. Do **not** use em-dashes (—), en-dashes (–), or LaTeX `--`/`---` — heavy dash use reads as AI-generated; use a period or comma and split long sentences. Cut filler buzzwords and convoluted phrasing. Keep the concrete tech keywords ATS needs, but state them plainly. Applies to every rewrite and to cover letters.

## Workflow

### Phase 1 — Analysis (always runs)

1. **Resolve the job posting.** If given a URL, `WebFetch` it. If the page is JS-rendered/empty (common with Ashby, Greenhouse, Lever), try the provider's public API:
   - Ashby: `https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true`
   - Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<org>/jobs/<id>`
   - Lever: `https://api.lever.co/v0/postings/<org>/<id>`
   If still empty/blocked, **stop and ask the user to paste the job text** — never write a placeholder/garbage `job.md`. Save the full posting verbatim to `job.md`.
2. **Extract keywords** → `keywords.md`. Bucket into **tech / soft / experience / domain / certs**; tag each **MUST** (job says "required", "X+ years") vs **nice** ("preferred", "no need to be an expert"). Mark each present/absent in the resume.
3. **Gap report** → `gap-report.md`. Compute a **weighted match score** (must-haves heavy), show **per-bucket coverage**, list strengths to surface and a **prioritized edit list**. Flag genuine gaps `⚠️ CONFIRM` and missing numbers `[QUANTIFY: …]`. **Consult the bullet bank:** if `master/bullet-bank.md` exists, for any must-have not covered by a current master bullet, check whether a bank line (matched via its `skills:`/`domain:` tags, `strength: strong` only) covers it — if so, note in the gap report "bank line available: `<heading>`" rather than calling it an unfillable gap.
4. **Feed interview-prep.** If `interview-prep/` exists (skip silently otherwise):
   - Append a `## From <Company> (<Role>)` section to `interview-prep/suggested.md` listing this JD's important keywords as ranked `- Title — one-line why` items (the format the interview-prep build parses): matched, resume-proven keywords are revision candidates; genuine gaps get a "(gap — learn)" suffix. Skip topics already in `interview-prep/topics/` (compare slugs) or already listed anywhere in `suggested.md`.
   - Write `applications/<Company>_<Role>/prep.yml` — the job-prep manifest behind the dashboard's job switcher (schema in interview-prep's SKILL.md): map keywords to existing topic slugs with judgment (alias-aware); JD must-tier ⇒ `must: true`; rank by JD weight; add a one-line `angle:` per generated topic tying their stack to the resume; entries without a topic file get `title` + `why`. Ask before overwriting an existing `prep.yml`.
5. **Stop and present the report.** Phase 1 may be the whole job.

### Phase 2 — Rewrite + compile (only after approval)

6. **Per-edit triage, conversationally.** Walk proposed edits with the user in batches (old→new, why, flags). **Truthfulness policy:** only re-surface facts already true; you MAY draft a bullet for a real gap but tag it `% UNVERIFIED — confirm true` and require explicit per-edit approval. Never silently invent. Numbers you don't have become `[QUANTIFY: …]`. **Bank as reservoir:** when a must-have is uncovered, prefer proposing a `strong` bank line from `master/bullet-bank.md` (its `bullet` text is already sourced and truth-checked, so it doesn't need `% UNVERIFIED`) over inventing — these are the off-master lines (`in_master: false`) meant for exactly this. Adding a bank line to this one application does **not** modify the master or the bank; permanently adopting it is a separate `update-master` promote.
7. **Write `resume-tailored.tex`** = copy of master + approved edits. **Content only** — never touch the preamble, packages, fonts, or layout.
8. **Ensure toolchain, then compile:** run `jobforge-toolchain` then `jobforge-compile <dir>/resume-tailored.tex` (both are on PATH while the plugin is enabled). See **Toolchain** below. The compile script auto-installs missing LaTeX packages, reverts to no PDF on error, and **warns if the PDF exceeds 1 page**.
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

`jobforge-toolchain` checks for `pandoc`, `pdflatex`, and `tlmgr`:
- Installs `pandoc` via Homebrew automatically (no sudo).
- BasicTeX and `tlmgr install` need **sudo**, and the Bash tool / `!` prompt have no TTY. The scripts handle this with a bundled **GUI askpass helper** (`scripts/askpass.sh` via `sudo -A`): a macOS password dialog pops up to install BasicTeX / packages, and the credential is cached so follow-on installs don't re-prompt. Only if that dialog is cancelled or unavailable (e.g. a headless/SSH session) do they fall back to printing the manual `brew install --cask basictex` / `sudo tlmgr install` command and exiting with code 2. On exit 2, tell the user to run the printed command in a real terminal and confirm.
- Once `pdflatex` exists, `jobforge-compile` resolves missing `.sty` files iteratively via `tlmgr search --file`.

## Formatting audit (one-time, separate from per-job runs)

When asked, audit `master/resume.tex` (not a copy): flag multi-column layout, non-ATS fonts, tables-as-layout, icon glyphs, and >1 page. Output suggestions; do not auto-change the master's layout. Per-job runs never touch formatting.
