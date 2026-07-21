---
name: tailor-application
description: Tailor a LaTeX resume to a specific job posting and produce an ATS-optimized PDF. Given a career-page URL (or pasted job text), it fetches the posting, extracts must-have/nice-to-have keywords, scores the resume against them, writes a gap report, then on approval rewrites a copy of the master resume (content only) and compiles it to PDF. Use when the user wants to apply for a job, tailor/customize their resume to a posting, run an ATS gap analysis, or mentions a job link plus their resume.
---

# tailor-application

Tailors `master/resume.tex` to one job and emits an ATS-optimized PDF. **Two phases with a human gate:** analysis (report) → approval → rewrite + compile.

## Conventions

- **Master (read-only source of truth):** `master/resume.tex`. Never edit it. If absent, the workspace isn't set up — tell the user to run `jobforge-scaffold` (then drop in their résumé, or use update-master's import mode).
- **Per-application artifacts:** `applications/<Company>_<Role>/` containing `job.md`, `keywords.md`, `gap-report.md`, `resume-tailored.tex` (working source), and the deliverable PDF named `<UserName>_<RoleAbbr>_resume.pdf` (plus its `.txt`).
- `<Company>_<Role>` uses PascalCase, no spaces (e.g. `Acme_DevOpsEngineer`).
- **Deliverable filename:** the compiled PDF is `<UserName>_<RoleAbbr>_resume.pdf` (underscore-separated). The working `.tex` stays `resume-tailored.tex` in every app (uniform, easy to find and edit).
  - `UserName`: read `name:` from `.jobforge.yml` at the workspace root; if absent, derive from the master resume heading (`\Huge <name>`); if still unknown, ask. Strip to a filename-safe form (remove spaces and punctuation), e.g. `Rohit Kumar` → `RohitKumar`.
  - `RoleAbbr`: a short abbreviation of the job **designation only** (drop team/specialization qualifiers). Use an initialism for multiword titles and keep well-known forms. E.g. `Sr. Software Development Engineer` → `SSDE`; `DevOps Engineer` → `DevOps`; `Site Reliability Engineer II` → `SRE2`; `Sr. Software Engineer, Core Services` → `SSE`. Record it as `role_abbr` in `status.yml`.
- **Writing style (avoid the AI tell):** write bullets as simple, impactful sentences. Do **not** use em-dashes (—), en-dashes (–), or LaTeX `--`/`---` — heavy dash use reads as AI-generated; use a period or comma and split long sentences. Cut filler buzzwords and convoluted phrasing. Keep the concrete tech keywords ATS needs, but state them plainly. Applies to every rewrite and to cover letters.
- **Impact-first bullets:** lead each experience bullet with the quantified outcome, then the how. Put the metric at or near the front — "Cut build time from 30 days to 8 hours by redesigning the build workflow…", not "Redesigned the build workflow, cutting build time…". For a bullet with no hard number, lead with the capability or result it produced (e.g. "Enabled autonomous incident triage with human-in-the-loop guardrails by…"). One sentence, plain language; never invent a metric to satisfy this — a metric-less bullet just leads with its outcome.
- **Concise bullets (10–30 words):** keep each experience bullet to roughly 10–30 words. Preserve every metric, the impact-first opener, and the JD's key keywords; trim the supporting detail (long tool lists, parentheticals, secondary clauses) when a bullet runs long. Cut the "how," never the outcome or the keywords. Scannable one-liners beat dense paragraphs for recruiters and resume scanners.
- **Summary as an elevator pitch:** open with the **target job title** (mirror the JD's exact title, not a generic self-label), state **years of experience**, name the **critical skills tailored to this JD**, and close with **one or two of the strongest, most relevant achievements**. Keep it to roughly three sentences and mirror the JD's own value language (e.g. "availability, scalability"). Do not restate more than one or two bullet metrics verbatim; the summary is a pitch, not a metrics dump (the rest live in the bullets).
- **Repetition: reinforce keywords, not filler.** Vary the opening verb across bullets (do not open several bullets with the same verb like "Cut"; rotate Reduced, Eliminated, Slashed, Lowered, Shipped, Built, Delivered, etc.), and never state the same fact twice (e.g. an award named in both a bullet and Key Achievements). But **do** reuse the JD's core role keywords across the summary, skills, and bullets — repeating required terms (e.g. "distributed systems", "SLO", "on-call") helps ATS matching and is not the repetition to remove.

## Workflow

### Phase 1 — Analysis (always runs)

1. **Resolve the job posting.** If given a URL, `WebFetch` it. If the page is JS-rendered/empty (common with Ashby, Greenhouse, Lever), try the provider's public API:
   - Ashby: `https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true`
   - Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<org>/jobs/<id>`
   - Lever: `https://api.lever.co/v0/postings/<org>/<id>`
   If still empty/blocked, **stop and ask the user to paste the job text** — never write a placeholder/garbage `job.md`. Save the full posting verbatim to `job.md`.
2. **Extract keywords** → `keywords.md`. Bucket into **tech / soft / experience / domain / certs**; tag each **MUST** (job says "required", "X+ years") vs **nice** ("preferred", "no need to be an expert"). Mark each present/absent in the resume.
3. **Gap report** → `gap-report.md`. Compute a **weighted match score** (must-haves heavy), show **per-bucket coverage**, list strengths to surface and a **prioritized edit list**. Flag genuine gaps `⚠️ CONFIRM` and missing numbers `[QUANTIFY: …]`. **Consult the bullet bank:** if `master/bullet-bank.md` exists, for any must-have not covered by a current master bullet, check whether a bank line (matched via its `skills:`/`domain:` tags, `strength: strong` only) covers it — if so, note in the gap report "bank line available: `<heading>`" rather than calling it an unfillable gap.
4. **No interview prep during tailoring.** Never write to `interview-prep/` or create `applications/<Company>_<Role>/prep.yml` in a tailoring run; that work slows tailoring down and belongs to the interview-prep skill.
   The user starts it separately with "do interview prep for <Company>_<Role>" (interview-prep Mode 5), which builds the job's prep manifest and scouts real interview questions.
   Your only job here is to mention that follow-up in the reports (steps 5 and 11).
5. **Stop and present the report.** Phase 1 may be the whole job. Close with the interview-prep pointer: `do interview prep for <Company>_<Role>` when they are ready.

### Phase 2 — Rewrite + compile (only after approval)

6. **Per-edit triage, conversationally.** Walk proposed edits with the user in batches (old→new, why, flags). **Truthfulness policy:** only re-surface facts already true; you MAY draft a bullet for a real gap but tag it `% UNVERIFIED — confirm true` and require explicit per-edit approval. Never silently invent. Numbers you don't have become `[QUANTIFY: …]`. **Bank as reservoir:** when a must-have is uncovered, prefer proposing a `strong` bank line from `master/bullet-bank.md` (its `bullet` text is already sourced and truth-checked, so it doesn't need `% UNVERIFIED`) over inventing — these are the off-master lines (`in_master: false`) meant for exactly this. Adding a bank line to this one application does **not** modify the master or the bank; permanently adopting it is a separate `update-master` promote.
7. **Write `resume-tailored.tex`** = copy of master + approved edits. **Content only** — never touch the preamble, packages, fonts, or layout.
8. **Ensure toolchain, then compile:** run `jobforge-toolchain` then `jobforge-compile <dir>/resume-tailored.tex <UserName>_<RoleAbbr>_resume` (both are on PATH while the plugin is enabled). The 2nd arg names the deliverable, producing `<dir>/<UserName>_<RoleAbbr>_resume.pdf` (and matching `.txt`); omitting it falls back to the `.tex` basename. See **Toolchain** below. The compile script auto-installs missing LaTeX packages, reverts to no PDF on error, and **warns if the PDF exceeds 1 page**.
9. **ATS self-check.** The compile script extracts `<UserName>_<RoleAbbr>_resume.txt` from the PDF via `pdftotext` (the text an ATS actually parses). Verify every MUST keyword from `keywords.md` appears in it, case-insensitively; list any that didn't survive (e.g. lost in a glyph/ligature) so they can be re-worded. If `pdftotext` is unavailable the script prints the `brew install poppler` hint — note the check was skipped. **Also run a quick polish pass** on the rewrite: every experience bullet ≤30 words, no opening verb repeated across many bullets, no fact (award, metric) stated twice, and the summary follows the elevator-pitch rule above. Fix any that fail and recompile.
10. **Write `status.yml`** in the application dir — flat `key: value` lines only (a non-YAML parser reads it):
    ```yaml
    company: <Company>
    role: <Role>
    role_abbr: <RoleAbbr>                          # used in the deliverable filename
    resume_pdf: <UserName>_<RoleAbbr>_resume.pdf   # the compiled deliverable
    url: <posting url or empty>
    applied:            # YYYY-MM-DD, fill when actually submitted
    stage: tailored     # tailored | applied | interview | offer | rejected
    next_interview:     # YYYY-MM-DD when scheduled
    notes:
    ```
    The interview-prep dashboard renders these files as an **Applications tracker** pane (with a next-interview countdown). The user updates `stage`/`next_interview` by hand or by asking.
11. **Report** the final score, the diff summary, the deliverable PDF path (`<UserName>_<RoleAbbr>_resume.pdf`), the ATS-check result, and any `UNVERIFIED`/`QUANTIFY` markers the user must still resolve.
    Remind the user of the separate follow-up: `do interview prep for <Company>_<Role>`.

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
