# Achievements / brag-doc (source of record)

This file is your **raw source material**. Drop true, sourced facts here — the
`update-master` skill reads everything in `master/additional-context/`, distills
it into `master/bullet-bank.md`, and (only on an explicit gated step) promotes
selected lines into `master/resume.tex`. Nothing here is ever published; the
whole `master/` directory is gitignored.

Rule baked into the skill: a bullet can only become `strong` (resume-grade) if it
traces to a real fact in this directory. No fabrication, ever. Missing numbers
become `[QUANTIFY: …]` and block promotion until you fill them in.

PDFs (promo packets, perf reviews) also work — drop them here too; the skill
reads them. Binary `*.pdf` files in this dir are gitignored.

## Example entry — anchor with a heading so the bank can cite it

### rag-ops-copilot
Built an internal operations copilot. Kept retrieval latency under 9 seconds on a
hybrid (BM25 + vector) index; cut incident triage from hours to minutes. Stack:
Spring AI, OCI GenAI, embeddings. (Replace with your own real achievement.)

### platform-migration
Led migration of N services to Kubernetes with zero customer-facing downtime;
reduced deploy time from 30 min to 4 min via a new CI/CD pipeline.
