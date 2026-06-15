---
name: update-master
description: Maintain the master resume from your raw achievements. Sweeps master/additional-context/ (brag-docs, promo PDFs, perf snippets) into a structured, reusable bullet bank, then on an explicit gated step promotes selected bank lines into master/resume.tex and validates the compile. The bank also acts as a reservoir of off-master lines that tailor-application can pull for a specific job. Use when the user wants to update/refresh the master resume, add a new achievement, turn a brag-doc or promo PDF into resume bullets, grow their reusable resume-line bank, or bootstrap a master by importing an existing PDF/Word/Docs resume into the LaTeX template.
---

# update-master

Turns your raw source-of-record material into resume bullets. This is the **one
skill that is allowed to edit `master/resume.tex`** — `tailor-application`
deliberately never touches the master; this does, behind a hard human gate.

The flow has two artifacts and one rule:

```
master/additional-context/   read-only human input (md tracked, *.pdf gitignored)
        │   (sweep)
        ▼
master/bullet-bank.md         skill-owned, structured, reusable bullets
        │   (gated promote)
        ▼
master/resume.tex             canonical résumé — edited only here, compile-validated
```

**The rule:** every line that reaches the bank — and therefore the résumé — must
trace to a real source in `master/additional-context/`. No fabrication, ever.

## Conventions

- **Input dir (read-only to this skill):** `master/additional-context/`. Any file
  there is a source. Markdown is read directly; PDFs via the Read tool's native PDF
  parsing. The skill **never writes into this directory.**
- **Bank (skill-owned):** `master/bullet-bank.md`. Structured entries (schema below).
  Git-tracked; the user may hand-edit but normally doesn't.
- **Master (high-stakes, gated):** `master/resume.tex`. Written only by *promote*
  (Mode 3) and the first-run *import* (Mode 4) — both content-only, never the
  preamble/layout.
- **Compile command (bundled, reused):** `jobforge-compile` (on PATH while the
  plugin is enabled; wraps tailor-application's compile script).

## Bullet-bank schema

`master/bullet-bank.md` is one markdown file; each bullet is a `##` heading + a
small field block:

```markdown
## RAG — hybrid retrieval for Ops Copilot
- bullet: Built an internal operations copilot keeping retrieval latency **under 9 seconds** … (LaTeX-ready, ATS-clean, no LaTeX errors)
- skills: [RAG, BM25, vector-search, Spring AI, OCI GenAI, embeddings]
- domain: [AI-ops, search, platform]
- company: Oracle (OCI API Gateway)
- metrics: [9s retrieval, hours→minutes indexing]
- strength: strong        # strong (resume-proven, sourced) | emerging (draft/aspirational)
- source: additional-context/achievements.md#rag-ops-copilot
- in_master: false        # true once promoted into resume.tex — prevents dupes
```

Field rules:
- **`bullet`** — a single, polished, ATS-clean line written the way it would read in
  the résumé (strong verb, concrete metric, no LaTeX that would break a compile).
  Keep it simple and impactful: **no em/en dashes or `--`/`---`** (they read as
  AI-generated — use a period or comma instead) and no filler jargon.
- **`skills` / `domain`** — the matchable tags; they line up against
  `tailor-application`'s keyword buckets so a job run can rank bank lines by overlap.
- **`source`** — points at the specific input file (and anchor) the fact came from.
  Mandatory. A bullet with no real source cannot exist as `strong`.
- **`strength`** — `strong` = sourced and resume-grade. `emerging` = a draft, or a
  fact you only asserted in chat without a source: it may sit in the bank but is
  **quarantined from promotion** until confirmed true (and any number made real).
- **`in_master`** — flip to `true` when promoted, so promotion never duplicates an
  existing résumé bullet and `tailor-application` can prefer off-master lines.
- **`metrics`** — any line missing a number it should have carries `[QUANTIFY: …]`
  in the `bullet` text; that placeholder **blocks promotion**.

## Modes

### Mode 1 — Sweep (default: build / refresh the bank)

Trigger: "update the master", "refresh the bank", "turn my brag-doc into bullets",
or just invoking the skill with no other instruction.

1. **Read every file** in `master/additional-context/` (markdown + PDFs).
2. **Diff against the existing bank.** For each candidate achievement decide: *new*
   bullet, *strengthen* an existing bank entry (better metric / sharper verb), or
   *dupe* (already covered in the bank or already a master bullet → skip). Run a
   light **staleness/dedupe pass** while here: flag near-duplicate bank entries and
   entries whose `source` file no longer exists.
3. **Write proposed entries to `master/bullet-bank.md`** — no per-entry gate; the
   bank is a git-tracked staging area and only *promote* touches the real résumé.
   Each new entry gets a real `source:`. Anything you only have from chat (no file)
   lands as `strength: emerging` and is flagged.
4. **Show the diff** — what was added, what was strengthened (old→new), what was
   skipped as a dupe, and any `emerging` / `[QUANTIFY: …]` items the user must
   resolve. The bank write is the deliverable of this mode; promotion is separate.

### Mode 2 — Add from paste or URL

Trigger: the user pastes an achievement, or gives a URL (promo blurb, launch post).

1. If a URL: `WebFetch` it; if a paste: take the text as-is.
2. Distill to one or more candidate bank entries. **No source file exists**, so each
   is `strength: emerging` with `source:` pointing at the URL or `chat:<date>` —
   tell the user to drop the underlying fact into `master/additional-context/` (or
   confirm it true) to make it `strong` and promotable.
3. Write to the bank and show the entry. Same no-gate-on-bank rule as Mode 1.

### Mode 3 — Promote (bank → master) — **HARD GATE**

Trigger: "promote `<bullet>` to master", "add that to my resume", "put the RAG line
on the master".

1. **Refuse to promote** any entry that is `strength: emerging` or whose `bullet`
   contains `[QUANTIFY: …]`. Say why and what's needed to unblock it.
2. **Show the exact LaTeX edit** before writing: which `\section` (`SUMMARY`,
   `EXPERIENCE` under which `\resumeSubheading`, `KEY ACHIEVEMENTS`, `SKILLS`),
   whether it's a new `\resumeItem` or a strengthen-in-place (old→new), and where it
   slots. **Stop for approval.**
3. On approval, **write `master/resume.tex`** (content only — never the preamble,
   packages, fonts, or layout) and flip the entry's `in_master: true`.
4. **Compile-validate:** run
   `jobforge-compile master/resume.tex`.
   This proves the master still compiles (a broken master poisons every future
   tailor run) and fires the **1-page guard**. If it spills past one page, surface
   it immediately so the user decides what to cut. `master/resume.pdf` is a
   gitignored, regenerable artifact — never commit it.
5. **Interview-prep feed (opt-in):** if `interview-prep/` exists, offer to append
   the promoted bullet's `skills:` tags as ranked candidates to
   `interview-prep/suggested.md` ("add these to your prep backlog? y/n") — a
   promoted achievement is one you'll have to defend. Sweeping never touches
   interview-prep; only this deliberate promote step does, and only on yes.

### Mode 4 — Import an existing resume (first-run bootstrap)

Trigger: "import my resume from `<file/url>`", "I don't have a LaTeX resume",
"create my master from this PDF/Word doc", or invoking the skill when
`master/resume.tex` is still the unedited scaffold template.

1. **Read the source.** `.pdf` → the Read tool's native PDF parsing (or
   `pdftotext`); `.docx` → `pandoc <file> -t markdown` (or the Read tool);
   `.md`/`.txt` → read directly; a public URL → `WebFetch`. Google Docs /
   auth-gated sources → ask the user to export to PDF/DOCX or paste the text. If
   nothing is readable, **stop and ask** — never guess a resume into existence.
2. **Fill the bundled template — do NOT let a converter generate LaTeX.** Use the
   existing `master/resume.tex` (the scaffolded ATS template) as the structural
   base and keep its preamble, custom commands (`\resumeSubheading` / `\resumeItem`),
   fonts, and layout **untouched**. pandoc's generic LaTeX is not ATS-clean and
   won't match these commands — only the *content* is ported.
3. **Map content → sections:** header (name + contact), `SUMMARY`, `EXPERIENCE`
   (each role = one `\resumeSubheading` + its `\resumeItem` bullets), `KEY
   ACHIEVEMENTS`, `SKILLS`. Preserve the user's real wording; tighten only for ATS.
4. **Truthfulness (same bar as everywhere).** Port only what the source actually
   says. A number you can't read cleanly → `[QUANTIFY: …]`; anything you inferred
   rather than read → `% UNVERIFIED — confirm true`. Never invent roles, dates, or
   metrics.
5. **Show the mapped content and STOP for approval** before writing — this creates
   the canonical master. On approval, write `master/resume.tex` (content only).
6. **Compile-validate:** `jobforge-compile master/resume.tex`. An imported resume
   often spills past one page — the **1-page guard** will flag it; surface it so the
   user decides what to trim (don't auto-cut).
7. **Seed the bank (optional, suggested).** The bank's `strong` lines must trace to
   a file in `master/additional-context/`. Tell the user to drop the original resume
   file there (it's their source of record), then run **Mode 1** to sweep it into
   `bullet-bank.md`. (The skill still never writes into `additional-context/` itself.)

## Truthfulness policy (applies to every mode)

Identical bar to `tailor-application`, raised because this edits the canonical
résumé:
- Only facts present in `master/additional-context/` reach the bank as `strong`.
- A drafted/asserted line with no source is `emerging` and **cannot be promoted**.
- A number you don't have is `[QUANTIFY: …]`; the master never carries a bracketed
  placeholder, so it **blocks promotion** until filled with a real figure.
- Never silently invent, inflate, or round a metric.

## First-run setup

- **No workspace yet?** If `master/resume.tex` is missing, run `jobforge-scaffold`
  to create it from the bundled templates. If it's still the scaffold placeholder,
  bootstrap it with **Mode 4** (import an existing PDF/Word resume) or by
  hand-filling the template — then the other modes apply.
- If `master/bullet-bank.md` doesn't exist, create it with a one-line header and
  seed it by running Mode 1 over `master/additional-context/`.
- The compile step reuses `tailor-application`'s toolchain. If `pdflatex` is missing,
  `jobforge-compile` / `jobforge-toolchain` install it via a GUI sudo password
  dialog (with a real-terminal fallback — see tailor-application's SKILL.md).
