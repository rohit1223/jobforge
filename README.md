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

## Requirements

- **Claude Code** with web access — the skills use WebFetch/WebSearch to read job
  postings and source documentation.
- **The Context7 plugin** — **required by `interview-prep`** to ground topics in
  official library docs. Install it alongside jobforge (step 1 below).
- **macOS with [Homebrew](https://brew.sh)** for the résumé toolchain.
  `jobforge-toolchain` then installs the rest for you: **pandoc** + **poppler**
  (no sudo) and **BasicTeX / LaTeX** (via a GUI sudo prompt). **python3** (ships
  with macOS) renders the interview-prep dashboard.

Only Context7 and Homebrew need installing yourself; `jobforge-toolchain` handles
the rest.

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

**Then add Context7** — required by `interview-prep` for official-doc grounding:

```
/plugin install context7@claude-plugins-official
/reload-plugins
```

Run `/plugin list` to confirm both `jobforge` and `context7` are enabled. (If
Context7 isn't found, the official marketplace may need adding first via the
`/plugin` menu → Discover.)

### 2. Create your workspace

Pick a directory to keep your job search in (it can be its own private git repo),
`cd` into it, and seed the skeleton from the plugin's bundled templates:

```bash
cd ~/path/to/your-job-search
jobforge-scaffold          # creates master/, applications/, interview-prep/
```

`jobforge-scaffold` is on PATH once the plugin is enabled — no clone needed, and it
never overwrites existing files. Then **replace `master/resume.tex` with your own
résumé** (keep the custom commands the template defines — the skills rely on them).

### Don't have a LaTeX resume?

`jobforge-scaffold` already gives you a working ATS template at `master/resume.tex`. To
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

Installs `pandoc` automatically. BasicTeX + LaTeX packages need `sudo`: a macOS
password dialog pops up (via a `sudo -A` askpass helper) to install them. If
there's no GUI session, it prints the exact `brew install --cask basictex`
command to run in a terminal instead.

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

Developing the plugin, testing changes, or publishing a new version? See
**[CONTRIBUTING.md](CONTRIBUTING.md)**.

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
