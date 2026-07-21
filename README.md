# JobForge

A Claude Code plugin that runs a job search end to end, with three skills:

- **`tailor-application`** runs an ATS gap analysis of your résumé against a job posting, then compiles a tailored 1-page PDF on your approval. It never edits your master.
- **`update-master`** is the only skill that edits your master résumé. It turns achievements into a reusable bullet bank and promotes them behind a human gate.
- **`interview-prep`** builds an offline interview-prep dashboard (topics, self-quiz, mock interviews) from your résumé and job gaps, including real interview questions scoured from Glassdoor, AmbitionBox, LinkedIn and similar sites. It runs only when you ask (e.g. `do interview prep for <job>`), never as part of tailoring.

The plugin ships the tools. Your résumé and job data stay in a local, gitignored workspace and are never published.

## Requirements

- **Claude Code** with web access.
- **Context7 plugin**, required by `interview-prep` (installed in step 1).
- **macOS + [Homebrew](https://brew.sh)**. `jobforge-toolchain` installs the rest (pandoc, poppler, BasicTeX/LaTeX).

## Install

```
/plugin marketplace add rohit1223/jobforge
/plugin install jobforge@jobforge
/plugin install context7@claude-plugins-official
/reload-plugins
```

`/plugin list` should show both `jobforge` and `context7` enabled.

## Set up your workspace

```bash
cd ~/path/to/your-job-search     # your private job-search folder
jobforge-scaffold                # creates master/, applications/, interview-prep/
jobforge-toolchain               # installs the LaTeX/PDF toolchain (one-time; pops a macOS password prompt)
```

Then replace `master/resume.tex` with your own résumé. No LaTeX résumé? Drop a PDF or Word file in the folder and ask Claude Code `import my resume from ./my-resume.pdf`; `update-master` fills the template from it (no fabrication).

## Use

Launch Claude Code **from your workspace folder**, then ask:

```
Tailor my resume to https://jobs.example.com/some-role
update my master resume
Build my interview prep dashboard
mock me on Kubernetes
quick prep on Kafka
do interview prep for Acme_SeniorSRE
```

`tailor-application` stops after the gap report for your review, then rewrites and compiles on approval.

## Updating

```
/plugin marketplace update jobforge
/plugin update jobforge@jobforge
/reload-plugins
```

Optional auto-update: `/plugin` → Marketplaces tab.

## Good to know

- **Run from your workspace folder.** The skills read `master/`, `applications/`, and `interview-prep/` relative to where you launch Claude Code.
- **Your data is gitignored.** Only the tooling (`skills/`, `bin/`, `examples/`, `.claude-plugin/`) is published.
- **No fabrication.** Skills surface only true facts; gaps are flagged, never invented.
- **The master is protected.** Only `update-master` edits it, gated and compile-checked; `tailor-application` edits a per-job copy.

Developing or publishing the plugin? See [CONTRIBUTING.md](CONTRIBUTING.md).
