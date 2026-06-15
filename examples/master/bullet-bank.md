# Bullet bank

Skill-owned staging area for reusable, sourced resume lines (managed by
`update-master`). Each entry is a `##` heading plus a field block. Lines with
`in_master: false` are a reservoir: `tailor-application` can pull a `strong` one
into a specific application without ever changing the master.

You normally don't hand-edit this — run `update-master` to populate it from
`master/additional-context/`. The entry below shows the schema.

## RAG — hybrid retrieval for Ops Copilot
- bullet: Built an internal operations copilot keeping retrieval latency **under 9 seconds** on a hybrid BM25 + vector index, cutting incident triage from hours to minutes.
- skills: [RAG, BM25, vector-search, embeddings]
- domain: [AI-ops, search, platform]
- company: Example Corp
- metrics: [9s retrieval, hours→minutes triage]
- strength: strong        # strong (resume-proven, sourced) | emerging (draft/aspirational)
- source: additional-context/achievements.example.md#rag-ops-copilot
- in_master: false        # true once promoted into resume.tex — prevents dupes
