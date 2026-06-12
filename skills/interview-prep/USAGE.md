# interview-prep — usability guide

A self-contained interview-prep dashboard built from your résumé and job gap
reports. Senior-level revision of topics you can defend, plus on-demand deep
dives on any topic. Everything renders into one offline HTML page:
`interview-prep/index.html`.

## The four modes

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

- **Left sidebar** — the guide (this page), Topics (gap-weighted / must-first),
  Notes, and the **Suggested** backlog. Use the **Filter** box to jump around.
- **Suggested · not generated** — collapsible groups, **résumé topics first, then
  JD topics**. Click any to open a pane with ready-to-copy prompts (standard /
  `--detailed` / deep+detailed). An item disappears from here once you generate it.
- **Badges** — `must` (JD-required), `learning` (still studying, can't fully
  defend yet), and the depth tier (`quick`/`standard`/`deep`).
- **Questions** are **click-to-reveal**: read the question, think, then expand
  the model answer. Use it as an active self-quiz.
- Every topic **cites its official source** at the top.

## Rebuilding manually

```
python3 skills/interview-prep/scripts/build.py interview-prep
open interview-prep/index.html
```

## Where things live

```
interview-prep/topics/<slug>.md   generated topics (git-tracked)
interview-prep/notes/<slug>.md    your notes
interview-prep/suggested.md       ranked backlog of not-yet-generated topics
interview-prep/index.html         the built dashboard (gitignored)
skills/interview-prep/            the skill: SKILL.md, USAGE.md, scripts/build.py
```

## Safety

- The **master résumé and your hand-edits are never clobbered**: a topic file
  with `generated: false` (or edited) is left alone — the skill asks first.
- A topic refresh **never touches your notes**.
- Per-topic re-fetch is opt-in: `--refresh <slug>`.
