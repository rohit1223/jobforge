# Resume — job-tailoring workspace

A version-controlled system for tailoring a master LaTeX resume to specific job
postings and producing ATS-optimized PDFs. The logic lives in a Claude Code skill
(`skills/tailor-application`) that is symlinked into `~/.claude/skills/`, so it's
tracked in this repo yet discoverable by Claude Code.

## Layout

```
master/resume.tex                  Canonical resume — the single source of truth. Edit this.
applications/<Company>_<Role>/     One folder per job, holding generated artifacts:
  ├── job.md                         the posting (fetched or pasted)
  ├── keywords.md                    bucketed must-have / nice-to-have keywords
  ├── gap-report.md                  weighted match score + prioritized edits
  ├── resume-tailored.tex            master + approved, content-only edits
  └── resume-tailored.pdf            compiled output
skills/
  ├── install.sh                     symlinks skills/* into ~/.claude/skills
  └── tailor-application/            the skill (SKILL.md + scripts/)
```

## Setup

```bash
# 1. Make the skill discoverable by Claude Code (idempotent; safe to re-run)
bash skills/install.sh

# 2. Install the LaTeX/PDF toolchain (pandoc auto; BasicTeX needs your password)
bash skills/tailor-application/scripts/ensure-toolchain.sh
```

`ensure-toolchain.sh` installs `pandoc` automatically. BasicTeX and `tlmgr`
package installs need `sudo` (a real password prompt) — the script prints the
exact command to run if it can't proceed.

## Usage

In Claude Code, point the skill at a job:

> Tailor my resume to https://jobs.example.com/some-role

The skill runs a two-phase pipeline with a human gate in the middle:

1. **Analysis** — fetch the posting → extract keywords → score the resume →
   write `gap-report.md`. *Stops here for you to review.*
2. **Rewrite + compile** (after you approve) — conversational per-edit triage →
   write `resume-tailored.tex` (content only, never the layout) → compile to PDF
   with a 1-page guard.

### Ground rules baked into the skill

- **Master is never edited** — only a per-application copy is rewritten.
- **No fabrication** — edits re-surface true facts; any gap-fill bullet is tagged
  `% UNVERIFIED` and needs explicit approval; missing numbers become `[QUANTIFY: …]`.
- **Layout is untouched per job** — fonts/columns/margins are handled as a
  separate one-time audit of the master, not on every run.

## Compiling manually

```bash
export PATH="/Library/TeX/texbin:$PATH"
bash skills/tailor-application/scripts/compile-resume.sh \
  applications/<Company>_<Role>/resume-tailored.tex
```

The compile script auto-installs any missing LaTeX packages via `tlmgr` and warns
if the result spills past one page.
