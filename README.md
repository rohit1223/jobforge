# Resume — job-tailoring workspace

A version-controlled system for tailoring a master LaTeX resume to specific job
postings and producing ATS-optimized PDFs. The logic lives in a Claude Code skill
(`skills/tailor-application`) that is symlinked into `~/.claude/skills/`, so it's
tracked in this repo yet discoverable by Claude Code.

## Layout

```
master/resume.tex                  Canonical resume — edited only by the update-master skill.
master/bullet-bank.md              Reusable, sourced resume lines (skill-owned; promoted into resume.tex).
master/additional-context/         Read-only source-of-record dir (brag-docs/.md tracked, promo *.pdf gitignored).
applications/<Company>_<Role>/     One folder per job, holding generated artifacts:
  ├── job.md                         the posting (fetched or pasted)
  ├── keywords.md                    bucketed must-have / nice-to-have keywords
  ├── gap-report.md                  weighted match score + prioritized edits
  ├── resume-tailored.tex            master + approved, content-only edits
  ├── resume-tailored.pdf            compiled output
  ├── resume-tailored.txt            ATS text extraction (pdftotext) for keyword checks
  ├── cover-letter.md                optional, on request
  ├── status.yml                     stage / applied / next_interview (tracker pane)
  └── prep.yml                       job-prep manifest (drives the dashboard's job switcher)
interview-prep/                    Global, repo-wide study dashboard (not job-specific):
  ├── topics/<slug>.md               one per topic (derived from keywords + gaps)
  ├── notes/<slug>.md                one per note (from a URL or local doc)
  └── index.html                     generated self-contained SPA (gitignored)
skills/
  ├── install.sh                     symlinks skills/* into ~/.claude/skills
  ├── tailor-application/            resume↔job tailoring skill
  ├── update-master/                 master-resume + bullet-bank skill
  └── interview-prep/                interview-prep dashboard + notes skill
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

## Updating the master resume

`tailor-application` never edits the master. A second skill, `update-master`, is the
**only** thing that does — behind a hard human gate. It turns your raw achievements
into résumé bullets through a staging bank:

```
master/additional-context/   ── you drop true source material here (md + promo PDFs)
        │   sweep            (skill reads the whole dir, writes none of it)
        ▼
master/bullet-bank.md        ── structured, reusable, tagged bullets (each cites its source)
        │   promote          (you approve the exact LaTeX edit; compile-validated, 1-page guard)
        ▼
master/resume.tex            ── canonical résumé
```

Three modes, in Claude Code:

> update my master resume            # sweep additional-context/ → propose bank entries → show diff
> add this achievement: …            # paste/URL → a new (emerging) bank entry
> promote the CSRF line to my resume # gated: shows the LaTeX edit, writes resume.tex, recompiles

Ground rules: only facts present in `master/additional-context/` reach the bank as
`strong`; unsourced/asserted lines are `emerging` and can't be promoted; a missing
number is `[QUANTIFY: …]` and blocks promotion; the master is compile-validated on
every promote (a broken master would poison future tailor runs). Bank lines that stay
`in_master: false` are a reservoir — `tailor-application` can pull one for a specific
job without ever changing the master.

## Interview prep

A second skill, `interview-prep`, builds a single self-contained SPA
(`interview-prep/index.html`) for **senior-level revision of topics you can
defend**. One skill, five modes:

- **Build / refresh** — derives matched, resume-proven topics (JD-required
  first), sources official docs (Context7 first, WebSearch+Fetch fallback), and
  writes deep prep per topic: senior mental-model concepts (internals,
  trade-offs, failure modes, tuning) + 10–15 seniority-calibrated interview
  questions as a **click-to-reveal self-quiz** + "say it with your resume" hooks.
- **Add a topic** (`add-topic <name> [--depth] [--detailed]`) — any single
  topic on demand, matched strength or gap you're learning.
- **Add a note** — point it at a public URL or local doc; it 80/20-distills the
  source into a note section.
- **Mock interview** (`mock <topic|all>`) — get interviewed in chat, one
  question at a time, graded against the model answers, with a weak-areas log.
- **Prep for a job** (`prep-for <Company_Role>`) — writes the per-job
  `prep.yml` manifest (topics, musts, order, one-line angles) behind the
  dashboard's **job switcher**.

The dashboard itself has a **job switcher** (pick a role to see only its
topics, must-first in its own order, with job-specific angle callouts and a
job-scoped quiz — shared topics reuse one content file and one progress store
across jobs), tracks **self-quiz progress** (grade each answer; stored in
localStorage), runs **shuffled quiz / weak-only flashcard sessions**, has
full-content search, keyboard navigation, a printable cheat-sheet mode, a
mobile drawer layout, staleness hints on old topics, and an **Applications
tracker** pane fed by `applications/*/status.yml` (stage + next-interview
countdown).

In Claude Code:

> Build my interview prep dashboard
> add-topic ClickHouse --detailed
> mock me on Kafka
> Add a note from https://…

Each `.md` lives under `interview-prep/`; the build renders them to one HTML page:

```bash
python3 skills/interview-prep/scripts/build.py interview-prep
open interview-prep/index.html
```

Refreshes are **additive** — new topics are added, hand-edited files and notes
are never clobbered (tracked via a `generated:` frontmatter flag).
