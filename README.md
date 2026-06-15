# JobForge

A Claude Code **plugin** for running a job search end to end:

- **`tailor-application`** — point it at a job posting; it does an ATS gap analysis
  against your résumé, then (after you approve) rewrites a per-job copy and
  compiles a 1-page PDF. Never edits your master.
- **`update-master`** — the only skill allowed to touch your master résumé. Turns
  raw achievements into a reusable, sourced **bullet bank**, and promotes selected
  lines into `master/resume.tex` behind a hard human gate.
- **`interview-prep`** — builds a self-contained interview-prep dashboard (one
  offline HTML page) of senior-level topics drawn from your résumé and job gap
  reports, with a job switcher, self-quiz, and mock-interview mode.

The plugin ships the **tools**. Your résumé, applications, and prep content are
**your data** — they live in a workspace directory that is gitignored and never
published.

---

## Install

### 1. Add the plugin

In Claude Code:

```
/plugin marketplace add rohit1223/jobforge      # or the git URL of this repo
/plugin install jobforge@jobforge
```

This puts the three skills and the helper commands (`jobforge-toolchain`,
`jobforge-compile`, `jobforge-build`) on Claude Code's PATH whenever the plugin is
enabled — no symlinks, no clone required.

### 2. Create your workspace

Pick a directory to keep your job search in (it can be its own private git repo).
Clone or copy this repo's `scaffold.sh` + `examples/` there, or run the bundled
scaffold, then seed the skeleton:

```bash
bash scaffold.sh            # copies examples/ -> master/, applications/, interview-prep/
```

It never overwrites existing files. Then **replace `master/resume.tex` with your
own résumé** (keep the custom commands the template defines — the skills rely on
them).

### 3. Install the LaTeX toolchain (one-time)

```
jobforge-toolchain
```

Installs `pandoc` automatically. BasicTeX needs `sudo`, so if it can't proceed it
prints the exact `brew install --cask basictex` command to run in a real terminal.

---

## Use

Launch Claude Code **from your workspace directory** (see the CWD note below), then
just ask:

```
Tailor my resume to https://jobs.example.com/some-role
update my master resume
add this achievement: <paste a brag-doc line or URL>
promote the RAG line to my resume
Build my interview prep dashboard
add-topic Kafka --detailed
mock me on Kubernetes
prep-for Acme_SeniorSRE
```

`tailor-application` runs a two-phase pipeline with a human gate: **analysis**
(fetch → keywords → gap report, *stops for review*) → **rewrite + compile** after
you approve.

---

## How your data is laid out

Everything below is created by `scaffold.sh` / the skills and is **gitignored** —
it stays on your machine:

```
master/resume.tex                  Your résumé. Edited only by update-master.
master/bullet-bank.md              Reusable, sourced résumé lines (skill-owned).
master/additional-context/         Drop true source material here (brag-docs, promo PDFs).
applications/<Company>_<Role>/      One folder per job (job.md, keywords.md, gap-report.md,
                                     resume-tailored.{tex,pdf,txt}, status.yml, prep.yml).
interview-prep/topics/<slug>.md    One per study topic.
interview-prep/notes/<slug>.md     One per note.
interview-prep/index.html          The generated dashboard (gitignored).
```

The tracked, publishable parts of this repo are: `skills/`, `bin/`, `examples/`,
`scaffold.sh`, the `.claude-plugin/` manifests, and this README.

### The CWD contract

The skills resolve `master/`, `applications/`, and `interview-prep/` **relative to
the directory you launch Claude Code from**. Always run it from your workspace
root. (The bundled helper commands resolve their own bundled scripts, so they work
regardless of CWD.)

---

## Developing / customizing the plugin

To iterate on the skills locally without re-installing on every change, load the
repo as a live plugin directory:

```bash
claude --plugin-dir /path/to/jobforge
```

Edits to `SKILL.md` files reload in-session; after changing `bin/`, hooks, or
manifests, run `/reload-plugins`.

---

## Ground rules baked into the skills

- **No fabrication.** Edits only re-surface facts already true; any gap-fill bullet
  is tagged `% UNVERIFIED` and needs explicit approval; missing numbers become
  `[QUANTIFY: …]`. A bank line can't be `strong` (or promotable) unless it traces
  to a real file in `master/additional-context/`.
- **The master is sacred.** Only `update-master` writes `master/resume.tex`, behind
  a gate, compile-validated, with a 1-page guard. `tailor-application` never touches
  it — it rewrites a per-application copy.
- **Layout is untouched per job.** Fonts/columns/margins are a one-time audit of the
  master, never changed on a per-job run.
- **Additive interview-prep refreshes.** New topics are added; hand-edited files and
  notes are never clobbered (tracked via a `generated:` frontmatter flag).
