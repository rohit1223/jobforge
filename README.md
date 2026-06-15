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

### Don't have a LaTeX resume?

`scaffold.sh` already gives you a working ATS template at `master/resume.tex`. To
fill it from a resume you already have (PDF, Word, Google Docs export, or plain
text), drop the file in your workspace and ask Claude Code:

> import my resume from ./my-resume.pdf

`update-master`'s import mode (Mode 4) reads it and maps the content into the
template — keeping the ATS layout, porting only what's actually in your file (no
fabrication), then compiling to check it. From there `tailor-application` works as
normal. Prefer to do it by hand? Just edit the placeholders in `master/resume.tex`,
keeping the `\resumeSubheading` / `\resumeItem` commands the skills expect.

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

## Updating the plugin

### If you installed it from the marketplace (normal use)

Pull the maintainer's latest changes:

```
/plugin marketplace update jobforge      # refresh the listing from the repo
/plugin update jobforge@jobforge         # update the installed plugin
/reload-plugins                          # apply in this session (no restart)
```

- `marketplace update` re-fetches `marketplace.json`; `plugin update` is what
  actually swaps in the new version; `/reload-plugins` avoids a full restart.
- You can also do it from the `/plugin` menu → **Installed** tab.
- **Update everything** you've installed: `/plugin update --scope user`.

### Enable auto-update (optional)

`/plugin` → **Marketplaces** tab → toggle **auto-update** (off by default for
third-party marketplaces like this one). When on, Claude Code refreshes at startup
and prompts you to run `/reload-plugins` if anything changed. To disable all
auto-updating globally: `export DISABLE_AUTOUPDATER=1`.

### If you run it locally (`--plugin-dir`, e.g. you're hacking on it)

No update step needed — you're running the repo directly. `SKILL.md` edits
hot-reload in-session; after changing `bin/`, manifests, or hooks, run
`/reload-plugins`. (A local `--plugin-dir` copy also shadows an installed one of
the same name.)

### Publishing a new version (maintainer)

`plugin.json` sets an explicit `version`, so **pushing commits alone won't reach
users** — Claude Code keeps the cached copy until the version string changes. On
each release: **bump `version`** in `.claude-plugin/plugin.json` (currently
`0.2.1`), commit, push. Then users run the update commands above.

> Iterating fast? Remove the `version` field instead — the plugin then tracks the
> git commit SHA, so every push is treated as a new version. Add `version` back
> when you want controlled, semver'd releases.

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
