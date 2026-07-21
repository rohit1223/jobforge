# interview-prep — usability guide

A self-contained interview-prep dashboard built from your résumé and job gap
reports. Senior-level revision of topics you can defend, plus on-demand deep
dives on any topic. Everything renders into one offline HTML page:
`interview-prep/index.html`.

## The five modes

### 1. Build / refresh the dashboard
Derives **matched, résumé-proven** topics (JD-required first), and generates the
**top ~3 not-yet-built** topics per run (kept small to avoid doc-fetch
rate-limits). The rest are listed under **Suggested · not generated** in the
sidebar and in the chat reply.

> "Build my interview prep dashboard" · "Refresh interview prep"

Re-run to generate the next ~3. Idempotent — existing topics are never
re-fetched or overwritten.

### 2. Add a topic, at the depth you choose  (`add-topic`)
Generate **any single topic on demand** — a strength to revise *or* a gap you
want to learn — at a depth you pick.

> "add-topic Redis --depth=deep" · "add-topic gRPC --detailed" · "explore Kafka quick"

- Default depth is **standard** (same as Mode 1 output).
- Add **`--detailed`** to fetch *more concepts* (extra sources + expanded
  fundamentals/worked examples) without changing the question count — ideal when
  the topic is **new to you**. It's on by default for `learning` topics.
- Topics you can't yet defend are flagged with a **learning** badge.

### 3. Add a note  (`add-note`)
Point it at a public URL or a local file (`.md/.txt/.pdf/.docx`). It distills the
source (80/20) into a note section under **Notes**.

> "add a note from https://… " · "add-note ./papers/raft.pdf"

### 4. Mock interview  (`mock`)
Get interviewed in chat on any generated topic (or all of them): one question
at a time, your answer graded strong / partial / missed against the model
answer with specific feedback, and a session log of weak areas saved under
**Notes** at the end.

> "mock me on Kafka" · "mock interview, 10 questions across all topics"

- Defaults to 8 questions; `all` weights sampling toward `must`/`learning` topics.

### 5. Prep for a specific job  (`prep-for` / "do interview prep for <job>")
One command does the whole per-job prep.
It creates `applications/<Company>_<Role>/prep.yml` from that job's keyword
analysis (which shared topics matter for *this* role, which are musts, their
order, and a one-line *angle* per topic), adds the job's missing topics to the
**Suggested** backlog, and scours the web (Glassdoor, AmbitionBox, LinkedIn,
Blind, Reddit, and similar) for **real interview questions** asked at that
company, saved as a note. The dashboard's **job switcher** is driven by these
files.

> "do interview prep for ExampleCorp_DevOpsEngineer" · "prep-for Acme_SRE" · "prep me for the Acme SRE role"

Interview prep never runs while you tailor a resume - tailoring stays fast, and
you start prep with this command whenever you are ready.

Topics are shared across jobs: two roles needing Kubernetes reuse the same
topic (and your quiz progress on it) — only ordering, musts, angles, and the
job's suggested gaps differ.

## Depth tiers

| Tier | Questions | Concepts | Doc fetches |
|------|-----------|----------|-------------|
| `quick` | ~5 | core mechanism + top trade-off | 1 |
| `standard` *(default)* | 10–15 | full senior mental-model (internals · trade-offs · failure modes · tuning) | 1–2 |
| `deep` | ~20–25 | exhaustive + code examples + multiple system-design prompts | several |

**`--detailed`** is orthogonal to depth: keep your chosen question count but pull
*more concepts* — extra doc sources plus prerequisites/fundamentals and worked
examples. Best for unfamiliar topics; on by default for `learning` topics.

## Reading the dashboard

- **Left sidebar** — the guide (this page), Topics (gap-weighted / must-first,
  grouped by bucket when there's more than one), Notes, the **Suggested**
  backlog, and the **Applications** tracker. The **Filter** box searches full
  topic content, not just titles.
- **Job switcher** (dropdown at the top) — pick a job to see only that role's
  topics, must-first in its own order, each with a job-specific *angle*
  callout; Suggested narrows to that job's missing topics and **Quiz me /
  Weak only quiz only that job's questions**. "All topics" restores the
  global view; your choice is remembered. Badges and quiz progress are shared
  across jobs because the topics themselves are shared.
- **Self-grading** — every revealed answer has ✓ Knew it / ~ Shaky / ✗ Missed
  buttons. Grades persist in your browser (localStorage); each topic shows a
  `known/total` counter in the sidebar that turns green when complete.
- **Quiz me / Weak only** — shuffled flashcard runs (up to 20 questions across
  all topics, or only what you've graded shaky/missed). Grades write back to
  the same progress store.
- **Keyboard** — `j`/`k` move between topics, `/` focuses the filter, `Esc`
  blurs it. Each topic also has **Expand all / Collapse all** buttons.
- **Print** — `Cmd+P` on a topic prints a light-themed cheat sheet with every
  answer opened (and restores your open/closed state afterwards).
- **Applications** — rendered from `applications/*/status.yml`; shows stage and
  a next-interview countdown (red within 7 days).
- **Suggested · not generated** — collapsible groups, **résumé topics first, then
  JD topics**. Click any to open a pane with ready-to-copy prompts (standard /
  `--detailed` / deep+detailed). An item disappears from here once you generate it.
- **Badges** — `must` (JD-required), `learning` (still studying, can't fully
  defend yet), and the depth tier (`quick`/`standard`/`deep`).
- **Questions** are **click-to-reveal**: read the question, think, then expand
  the model answer. Use it as an active self-quiz.
- **Real-world questions** - topics carry a community-sourced section of
  questions people report actually being asked (each tagged with the site it
  was reported on); per-job prep also saves a company-specific real-questions
  note under **Notes**.
- Every topic **cites its official source** at the top.

## Rebuilding manually

```
jobforge-build interview-prep
open interview-prep/index.html
```

## Where things live

```
interview-prep/topics/<slug>.md   generated topics (your data; gitignored)
interview-prep/notes/<slug>.md    your notes
interview-prep/suggested.md       ranked backlog of not-yet-generated topics
interview-prep/index.html         the built dashboard (gitignored)
(the skill itself ships inside the jobforge plugin; `jobforge-build` is on PATH)
```

## Safety

- The **master résumé and your hand-edits are never clobbered**: a topic file
  with `generated: false` (or edited) is left alone — the skill asks first.
- A topic refresh **never touches your notes**.
- Per-topic re-fetch is opt-in: `--refresh <slug>`. Topics older than ~2 months
  show a muted "generated N months ago" hint, and `--refresh-stale` offers to
  re-fetch everything older than ~90 days (asking per topic).
