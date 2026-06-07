---
name: interview-prep
description: Build and grow a self-contained interview-prep dashboard (single SPA HTML) from your resume and job gap reports, and add study notes from URLs or local docs. Derives topics from all applications' keywords + gaps, sources official documentation (Context7 first), distills the 80/20, and writes doc-grounded prep — core concepts, likely interview Q&A, and resume tie-in hooks. Use when the user wants to prep for interviews, study topics for a role, build a study dashboard, or add a note from a link/document.
---

# interview-prep

A global, repo-wide study dashboard that complements `tailor-application`. **One skill, two modes:** build/refresh the dashboard, and add a note. Both write Markdown and rebuild a single self-contained `index.html`.

## Conventions

- **Data dir (source of truth, git-tracked):** `interview-prep/` at the repo root.
  ```
  interview-prep/
  ├── topics/<slug>.md   # one per topic
  ├── notes/<slug>.md    # one per note
  └── index.html         # generated build artifact (gitignored)
  ```
- **Build:** `python3 skills/interview-prep/scripts/build.py interview-prep` renders every `.md` (via `pandoc`) into one self-contained `index.html` (inline CSS/JS, sidebar nav). Run it after any `.md` change.
- **Topic frontmatter:** `title`, `bucket` (tech/soft/experience/domain/certs), `must` (bool), `gap` (bool), `rank` (int; lower = higher in sidebar), `sources` (url), `generated` (bool — `true` until a human edits it).
- **Note frontmatter:** `title`, `source` (url/path), `added` (YYYY-MM-DD), `generated: true`.

## Mode 1 — build / refresh the dashboard

1. **Derive topics.** Scan **all** `applications/*/keywords.md` + `gap-report.md` and `master/resume.tex`. Union + dedup keywords. Rank: **must-have first, then gap-flagged, then cross-job frequency.** Cap ~20 prominent topics; lower-priority ones get a higher `rank` (sidebar "more").
2. **Skip existing** topic files unless `--refresh <topic>` is given (see Safety).
3. **Source official docs** for each new topic — see **Doc sourcing** below. Record the URL/library in `sources`.
4. **Write `topics/<slug>.md`** with `generated: true` and this body template:
   ```markdown
   ## 80/20 — Core concepts
   The ~20% that covers ~80% of interviews, grounded in the official docs. [cite inline]

   ## Likely interview questions
   **Q:** … 
   **A:** … (crisp, correct, doc-aligned)

   ## Say it with your resume
   - Tie to your real bullet: "<paraphrase a master/resume.tex achievement>" …

   ## Sources
   - [official-doc-title](https://…)
   ```
5. **Rebuild:** run `build.py`, then tell the user the path to open `interview-prep/index.html`.

## Mode 2 — add a note  (`<url | local file path>`)

1. **Fetch/convert the source:** public URL → `WebFetch`; `.md`/`.txt` → read directly; `.docx` → `pandoc`; `.pdf` → `pdftotext` (install poppler if missing: `brew install poppler`). Auth-gated sources (private Google Docs, Notion) → ask the user to paste the text or export to PDF.
2. **Distill 80/20**, doc-grounded, into a new `notes/<slug>.md` (`generated: true`), citing the `source`. Same right-pane shape; appears under the sidebar's **Notes** group.
3. **Rebuild** with `build.py`.

## Doc sourcing (Context7 first)

For libraries / frameworks / tools (Kubernetes, Terraform, Node.js, React, AWS services…):
- `ToolSearch` for `context7`, then `resolve-library-id` → `query-docs` to pull current official docs for the 80/20 essentials.

For concepts / soft skills / niche items Context7 can't resolve: `WebSearch` for the official site, then `WebFetch` it. Never fabricate — every topic cites its source.

## Safety rails

- **Additive refresh.** A normal refresh only **adds** topic files for new keywords and rebuilds. Existing topic files are left untouched by default.
- **Never clobber edits.** If a file's frontmatter `generated:` is missing or `false`, a human has edited it — do not overwrite; ask first.
- **Notes are sacred.** A topic refresh never touches `notes/*.md`.
- Per-topic re-fetch is opt-in: `--refresh <slug>`, and still asks before overwriting an edited file.
