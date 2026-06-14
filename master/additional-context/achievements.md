# Additional context — raw achievements / brag-doc

This file is one source in `master/additional-context/`. **Everything in this
directory is human-owned input** — drop true, source-of-record material here in any
form (markdown brag-docs, promo PDFs, perf-review snippets, launch write-ups). The
`update-master` skill **reads the whole directory and writes none of it**; it
distills what it finds into `master/bullet-bank.md`, and a gated promote step
carries selected bank lines into `resume.tex`. `tailor-application` may also pull
fitting bank lines for a specific job. **Truthfulness policy:** only facts stated
in this directory ever reach the bank or the résumé.

## RAG — Ops Copilot

Rohit delivered the Ops Copilot RAG subsystem by solving several core technical challenges required for production use in APIGW operations. He designed a hybrid retrieval architecture that combines Lucene BM25 and vector search to support both exact operational lookups, such as error strings and config keys, and semantic natural-language questions. He built a robust ingestion pipeline that normalizes PDFs, HTML, Markdown, runbooks, Confluence pages, tables, links, code, and headings into enriched, citation-aware chunks. He implemented incremental indexing with source hashes, stable document IDs, manifest tracking, stale-record deletion, and Lucene/vector synchronization so the corpus stays fresh without expensive full rebuilds. He also extended the Spring AI and OCI GenAI integration with custom embedding batching, source-aware vector deletion, metadata filtering, advisor/citation handling, and Cohere tool support, turning RAG from a prototype into an operationally usable subsystem.

Ops Copilot was delivered as a multi-module operational AI framework spanning RCA automation, RAG-based knowledge retrieval, ticket context writing, reports generation, and AI SRE agent workflows. The framework was primarily driven by Paul and Rohit; Rohit led and implemented the RAG platform, ticket context onboarding across multiple services, RCA intelligence improvements including background RCA, Object Storage reuse, Jira evidence attachments, egress dependency detection, and Generic MCP integration, while also contributing to AI SRE agent automation for ticket handling and severity analysis.
