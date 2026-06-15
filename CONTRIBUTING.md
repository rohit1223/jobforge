# Contributing to JobForge

This guide is for developing the **plugin itself**. For *using* it, see the
[README](README.md).

JobForge is a Claude Code plugin: three skills (`tailor-application`,
`update-master`, `interview-prep`) plus helper commands, distributed from this
repo as a single-plugin marketplace.

## Local development

Load the repo as a live plugin directory so edits take effect without
re-installing:

```bash
claude --plugin-dir /path/to/jobforge
```

- Edits to `SKILL.md` files **hot-reload in the current session**.
- After changing `bin/`, the `.claude-plugin/` manifests, or hooks, run
  `/reload-plugins`.
- A local `--plugin-dir` copy **shadows** an installed plugin of the same name, so
  you can iterate without uninstalling the published one.

## Layout

```
.claude-plugin/   plugin.json (manifest) + marketplace.json (single-plugin marketplace)
bin/              PATH wrappers: jobforge-build / jobforge-compile / jobforge-toolchain
skills/           the three skills (SKILL.md + USAGE.md + scripts/)
  tailor-application/scripts/   compile-resume.sh, ensure-toolchain.sh, askpass.sh
  interview-prep/scripts/       build.py
examples/         tracked starter templates (seeded into a user workspace by scaffold.sh)
scaffold.sh       seeds master/ applications/ interview-prep/ from examples/
```

A user's own workspace (`master/`, `applications/`, `interview-prep/` data) is
gitignored and never part of the plugin.

## Testing changes

The basics need no network or sudo:

```bash
# shell scripts parse
bash -n bin/* skills/tailor-application/scripts/*.sh

# manifests are valid JSON
python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json'))"

# the dashboard builds (renders examples/interview-prep/index.html)
bin/jobforge-build examples/interview-prep

# the example résumé compiles to a 1-page ATS PDF (needs the LaTeX toolchain)
bin/jobforge-compile examples/master/resume.example.tex

# clean up build artifacts
rm -f examples/interview-prep/index.html examples/master/resume.example.{pdf,txt,aux,log,out}
```

The `bin/` wrappers resolve their own bundled scripts, so they work from any CWD.

## Publishing a new version

`plugin.json` sets an explicit `version`, so **pushing commits alone won't reach
users** — Claude Code keeps the cached copy until the version string changes.

On each release:

1. **Bump `version`** in `.claude-plugin/plugin.json` (semver: patch for fixes,
   minor for new features). `plugin.json` is the single source of truth — no other
   file pins the version.
2. Commit and push to the repo backing the marketplace.
3. Users pull it with:
   ```
   /plugin marketplace update jobforge
   /plugin update jobforge@jobforge
   /reload-plugins
   ```

> Iterating fast and don't want to bump every push? Remove the `version` field —
> the plugin then tracks the git commit SHA, so every push is treated as a new
> version. Add it back when you want controlled, semver'd releases.

## Conventions

- Skills edit **content only** — never a résumé's LaTeX preamble or layout.
- **No fabrication.** Facts must trace to a real source; gaps are flagged
  (`% UNVERIFIED`, `[QUANTIFY: …]`), never invented. Preserve this bar in any
  change to the skills' prompts.
- Bundled scripts invoked from a `SKILL.md` go through a `bin/` wrapper (bare
  name) so they resolve regardless of the user's working directory.
