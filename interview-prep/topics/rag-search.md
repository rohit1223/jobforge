---
title: RAG & Search Systems
bucket: tech
sources: https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism — BM25 vs dense vs hybrid, ANN

- **BM25 (lexical).** A bag-of-words probabilistic scorer built on three signals. *TF saturation*: the `k1` parameter (Elasticsearch default `1.2`) controls *non-linear* term-frequency normalization — score rises with term frequency but asymptotes, so the 10th occurrence of a word adds far less than the 2nd. *IDF*: rare terms across the corpus get more weight than common ones, so matching "BGP" matters more than matching "the". *Document-length normalization*: the `b` parameter (default `0.75`) controls how strongly long documents are penalized so a long doc doesn't win just by containing the term more often. Net effect: BM25 is unbeatable at exact-match — error codes, IP addresses, product SKUs, rare identifiers — and needs no training, but it has zero notion of meaning ("car" ≠ "automobile").
- **Dense retrieval.** An embedding model maps query and chunks into a shared vector space; relevance = cosine/dot similarity. Captures paraphrase and synonymy but *under-weights short literal tokens* (config flags, error codes) and can return plausible-but-wrong neighbors. Exhaustive nearest-neighbor is O(N·d), so production uses an **ANN index**:
  - **HNSW** (graph): multi-layer navigable small-world graph; ~1–10 ms at scale, >98% recall, but must hold full vectors in RAM (1–4 KB each) → expensive at billions. Build is slow; great default for latency-critical serving.
  - **IVF / IVF-PQ** (cluster + compress): partition into centroids, probe only `nprobe` nearest clusters; PQ compresses vectors 16–64× so it fits memory-constrained / huge corpora, at ~5–50 ms and 90–95% recall. Recall is tuned by `nprobe`; needs a representative training set for centroids.
- **Hybrid + RRF.** Run BM25 and dense in parallel, then fuse. **Reciprocal Rank Fusion** combines on *rank* (`score = Σ 1/(k + rank)`, k≈60), not raw scores — this sidesteps the score-incompatibility problem (BM25 ~0–15, cosine ~0.6–0.95 have incomparable distributions, so weighted averaging is fragile). Hybrid wins because the two retrievers *fail differently*: on lexical queries BM25 finds ~70% of relevant docs while dense finds ~5%, and the reverse holds for paraphrase queries.

### Trade-offs — recall vs latency vs cost

- **Recall ↔ latency ↔ cost is the central triangle.** HNSW buys recall+latency with RAM; IVF-PQ buys cost+scale with recall/latency. `efSearch`/`nprobe` are the runtime dials.
- **Reranking** (cross-encoder) jointly encodes each query-chunk pair for high-precision scoring — far more accurate than bi-encoder similarity, but O(candidates) model calls, so you only rerank the top-k (e.g. 100→10). It trades latency/cost for precision and also *reduces* downstream cost by sending the LLM fewer, better chunks.
- **Embedding choice + dimensionality.** Bigger dims and bigger models lift recall but cost more RAM, index time, and query latency; domain-specific or fine-tuned embeddings often beat a larger general model. Batch embedding amortizes API/GPU cost vs per-doc calls.
- **Chunking.** Fixed-size + overlap is simple and cheap but cuts mid-thought; semantic/structure-aware chunking respects boundaries (sections, tables) at higher preprocessing cost. Larger chunks raise recall-of-context but dilute precision and burn context tokens.

### Failure modes

- **Stale index.** Source updated, index didn't → confidently wrong answers from old content. Mitigate with incremental indexing on change events + TTL/versioning, not just periodic full rebuilds.
- **Bad chunking / chunk-boundary loss.** Answer spans two chunks, or a chunk loses the context that makes it findable (a table row with no header, a paragraph whose subject was named earlier). Anthropic's *Contextual Retrieval* prepends LLM-generated context to each chunk and cut top-20 retrieval failures 35% (embeddings) → 49% (with contextual BM25) → 67% (adding reranking).
- **Hallucination / ungrounded generation.** Retrieval reduces but does *not* eliminate it (legal RAG tools showed hallucination up to 33%). Enforce citation grounding: require every factual claim to cite a retrieved span, prefer simultaneous (cite-as-you-write) over post-hoc citation, and verify/abstain when context is empty.

### Tuning knobs

`k1`/`b` (BM25), `efConstruction`/`M`/`efSearch` (HNSW), `nlist`/`nprobe`/PQ codes (IVF), RRF `k` and per-retriever weights, chunk size/overlap, rerank candidate depth, top-k into the prompt, embedding model + dimension.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk through how BM25 scores a document, and what k1 and b actually control.</summary>

BM25 sums per-term contributions of `IDF(term) × (saturated TF) × (length normalization)`. IDF down-weights corpus-common terms so rare query terms dominate. `k1` controls term-frequency saturation — TF contributes with diminishing returns so a term appearing 20 times isn't 20× a single occurrence (Elastic default 1.2); raise it for verbose corpora where repetition is meaningful. `b` (default 0.75) controls document-length normalization: at `b=1` you fully penalize long docs, at `b=0` you ignore length — tune it down when long docs are legitimately more informative rather than just padded. The trade-off is that BM25 nails exact tokens but is blind to semantics.

</details>

<details>
<summary><strong>Q:</strong> HNSW vs IVF-PQ — when do you pick which, and what are the tuning dials?</summary>

HNSW is a navigable small-world graph giving ~1–10 ms queries and >98% recall, but it keeps full vectors in RAM (1–4 KB each), so at billions of vectors RAM cost dominates; `M` and `efConstruction` set graph quality/build cost, `efSearch` trades recall for latency at query time. IVF-PQ partitions vectors into centroids and compresses them with product quantization (16–64× smaller), so it fits memory-constrained or very large corpora at ~5–50 ms and 90–95% recall, tuned via `nlist`/`nprobe`. Rule of thumb: latency-critical and fits in RAM → HNSW; huge corpus or cost-constrained → IVF-PQ, often HNSW for hot data and IVF-PQ for cold.

</details>

<details>
<summary><strong>Q:</strong> Why does Reciprocal Rank Fusion beat naive score-weighted hybrid?</summary>

BM25 and cosine produce distributions on completely different scales (BM25 ~0–15 unbounded, cosine ~0.6–0.95), so a weighted sum is dominated by whichever scorer has larger raw magnitude and is destabilized by outliers, even after normalization. RRF discards magnitudes and fuses on rank: `Σ 1/(k + rank_i)` with k≈60, so a doc ranked highly by *either* retriever surfaces. It's robust precisely because the two retrievers fail on disjoint query types — RRF lets each cover the other's blind spot without per-corpus score calibration.

</details>

<details>
<summary><strong>Q:</strong> Why does hybrid retrieval beat either lexical or dense alone? Give the failure pattern.</summary>

They fail on complementary query classes. On lexical queries (exact codes, rare identifiers, config flags) BM25 recalls ~70% of relevant docs while dense recalls ~5%; on paraphrase/semantic queries the numbers flip. Dense under-weights short literal tokens — an IP address or error code is a needle BM25 finds instantly and embeddings smear into nearby neighbors. Hybrid via RRF captures both, and benchmarks show meaningful NDCG lift over either alone. The cost is two retrieval paths plus a fusion step, which is cheap relative to the recall gain.

</details>

<details>
<summary><strong>Q:</strong> What does a cross-encoder reranker buy you, and why not just embed everything with it?</summary>

A cross-encoder jointly encodes the query and a candidate chunk in one forward pass, so attention can model fine-grained query-document interactions a bi-encoder (which encodes them independently) cannot — much higher precision. You can't use it for first-stage retrieval because it requires a forward pass *per* query-document pair, so scoring the whole corpus is O(N) model calls — infeasible. The pattern is cheap recall first (BM25/ANN to top-100), then expensive precision (rerank to top-10). It also lowers LLM cost by sending fewer, more relevant chunks; Anthropic showed reranking pushed retrieval-failure reduction from 49% to 67%.

</details>

<details>
<summary><strong>Q:</strong> How do you choose chunk size and overlap, and what's the failure mode of getting it wrong?</summary>

There's no universal size — it's a recall/precision and context-budget trade-off. Large chunks preserve surrounding context and answer-spanning content but dilute the embedding (one vector summarizing many topics) and burn prompt tokens; small chunks are precise but lose the context that makes them retrievable and split answers across boundaries. Fixed-size with overlap (e.g. 10–20%) cheaply mitigates boundary cuts; semantic/structure-aware chunking (respecting sections, tables, code blocks) is better but costs preprocessing. The classic failure is a chunk that's unretrievable because the disambiguating context lived in a neighbor — which is exactly what contextual chunking (prepending document context) fixes.

</details>

<details>
<summary><strong>Q:</strong> Your RAG system returns irrelevant documents for a class of queries. How do you diagnose it?</summary>

Isolate the stage: log retrieved chunks with scores and check whether the *right* chunk exists in the index at all (recall problem) versus exists but ranks low (ranking problem). If it's missing, suspect chunking (answer split across boundaries, lost context) or a stale/partial index. If present but low-ranked, look at retriever mismatch — lexical queries hitting a dense-only pipeline (add BM25/hybrid) or vice versa, or an embedding model wrong for the domain. Measure context recall@k offline on a labeled query set to quantify it, then add a cross-encoder rerank if candidates are good but ordering is poor. Tune RRF weights or `efSearch`/`nprobe` only after you've localized the stage.

</details>

<details>
<summary><strong>Q:</strong> The model hallucinates despite RAG. Walk through root-causing and fixing it.</summary>

First separate retrieval failure from generation failure: if the supporting chunk wasn't retrieved, the model had nothing to ground on — fix recall (hybrid, rerank, chunking). If the chunk *was* in context but the answer contradicts it, that's a faithfulness/generation failure — enforce citation grounding (every claim cites a span), instruct the model to abstain when context is insufficient, and reduce distractor chunks via reranking. Measure with faithfulness (LLM extracts each claim and checks it against context) and context recall; these two are the highest-signal metrics. Remember retrieval *reduces* but never eliminates hallucination — production legal RAG hit 33% — so abstention and citation verification are required, not optional.

</details>

<details>
<summary><strong>Q:</strong> How do you evaluate a RAG pipeline beyond "it looks good"?</summary>

Split metrics by stage. Retrieval: context recall@k (did we fetch the relevant chunks?) and context precision (are top-ranked chunks the relevant ones?) — recall tells you if the architecture is even capable of answering. Generation: faithfulness/groundedness (is every answer claim supported by retrieved context?) and answer relevancy (does it address the question?). Frameworks like RAGAS automate this LLM-as-judge without human labels. Start with faithfulness + context recall as the two highest-signal metrics, run them on a fixed query set in CI so chunking/embedding/reranker changes are A/B-comparable rather than vibes.

</details>

<details>
<summary><strong>Q:</strong> Incremental vs batch indexing — when and why, and what breaks?</summary>

Batch (re)indexing is simplest and gives a clean consistent snapshot, but full rebuilds over large corpora are slow and you serve stale results between runs. Incremental indexing applies adds/updates/deletes on change events (or CDC), keeping the index fresh in near-real-time and turning hours-long rebuilds into minutes — essential when source docs change continuously. The hard parts are deletes/tombstones (orphaned vectors), idempotency on retries, and ANN structures that degrade with churn (HNSW graphs and IVF centroids can drift, needing periodic compaction/retraining). The dominant failure mode either way is the stale index: source changed, index didn't, model answers confidently from old content — so you version chunks and reconcile.

</details>

<details>
<summary><strong>Q:</strong> Design a low-latency RAG system over a large enterprise document corpus (runbooks, PDFs, HTML, tables). What's your architecture?</summary>

Ingest with format-aware parsing (preserve table structure and HTML/section boundaries), then structure-aware chunking with overlap and contextual enrichment so chunks stay findable. Index hybrid: BM25 (Lucene/Elastic) for exact terms plus an HNSW vector index for semantics, embeddings produced in batches to amortize cost. Query path: run both retrievers in parallel, fuse with RRF, cross-encoder rerank the top candidates to a small top-k, then generate with mandatory citations and abstention when context is thin. Keep latency down with HNSW + tuned `efSearch`, cap rerank depth, cache embeddings/frequent queries, and keep the index fresh via incremental indexing on document-change events. Close the loop with offline recall@k and faithfulness evals in CI.

</details>

<details>
<summary><strong>Q:</strong> How do you hold retrieval latency under a hard SLO (say single-digit seconds) without tanking recall?</summary>

Budget the pipeline stage-by-stage: parallelize BM25 and ANN (don't serialize), cap ANN cost with HNSW + a tuned `efSearch` rather than exhaustive search, and bound the reranker by only scoring a fixed candidate depth (e.g. top-50→10). Pre-compute and cache embeddings so query-time is just an encode of the query, and cache hot queries and frequent chunks. Keep the working set in RAM (HNSW) for the hot corpus; push cold data to IVF-PQ. The recall lever you protect is hybrid+rerank quality, so you spend the saved latency on better ranking, not on a bigger candidate set than the reranker can afford.

</details>

<details>
<summary><strong>Q:</strong> At Oracle you built an Ops Copilot with hybrid BM25/vector search under 9s. Walk me through the retrieval design decisions.</summary>

The corpus was heterogeneous — runbooks, docs, PDFs, HTML, tables across many teams' KBs — which is exactly where pure dense retrieval fails: operators search by literal error strings, command names, and config keys that BM25 nails and embeddings smear. So hybrid was a correctness decision, not a buzzword: BM25 for the literal SRE tokens, vectors for "how do I recover from X" phrasing, fused so each covers the other's blind spot. Sub-9-second latency meant parallel retrieval, an ANN index for the dense path, capped rerank/top-k, and batch embeddings so indexing cost was amortized rather than per-doc. Citation-aware responses were the grounding control — every answer pointed back to the source runbook so on-call engineers could trust and verify it instead of acting on a hallucination.

</details>

<details>
<summary><strong>Q:</strong> You cut indexing time from hours to minutes with incremental indexing. What was the actual mechanism and the risks you had to handle?</summary>

Instead of rebuilding the whole index when any KB changed, I indexed only the deltas — adds/updates/deletes on document-change events — and batched the embedding calls so the embed step wasn't the bottleneck. That turned a multi-hour full rebuild into minutes and, just as importantly, kept retrieval fresh so the copilot wasn't answering from stale runbooks during an incident. The risks I had to handle were deletes leaving orphaned vectors, idempotency so retried events didn't duplicate chunks, and ANN-structure drift from continuous churn, which I managed with chunk versioning and periodic compaction. Freshness mattered more than anything here because a stale ops index produces confident-but-wrong remediation steps.

</details>

## Say it with your resume

- **Lead with the Ops Copilot hybrid retrieval.** At Oracle I built an internal Ops Copilot over runbooks/docs/PDFs/HTML/tables across 15 teams' KBs using **hybrid BM25 + vector search** — BM25 for the literal error codes, commands, and config keys SREs search by, vectors for natural-language "how do I fix X", fused so neither retriever's blind spot reached the user.
- **<9s retrieval latency was an engineered SLO**, not luck: parallel lexical+dense retrieval, an ANN index on the dense path, capped top-k, and **batch embeddings** to amortize cost — the classic recall/latency/cost triangle, tuned for an on-call audience that can't wait.
- **Citation-aware responses** were my hallucination control — every answer grounded to its source runbook so engineers could verify before acting; this is exactly the citation-grounding pattern authoritative RAG guidance recommends, since retrieval reduces but never eliminates hallucination.
- **Incremental indexing took indexing from hours to minutes** and kept the index fresh, directly attacking the stale-index failure mode that produces confidently-wrong remediation during an incident.
- **Adopted by 15 teams** — proof the system was trustworthy and fast enough for real operational use, which is the real bar for grounded RAG in production.

## Sources

- [BM25 similarity parameters (k1, b) — Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html)
- [Introducing Contextual Retrieval — Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- [How to Choose Between IVF and HNSW for ANN Vector Search — Milvus](https://milvus.io/blog/understanding-ivf-vector-index-how-It-works-and-when-to-choose-it-over-hnsw.md)
- [Hybrid Search: BM25 and Dense Retrieval Combined — Brenndoerfer](https://mbrenndoerfer.com/writing/hybrid-search-bm25-dense-retrieval-fusion)
- [Reciprocal Rank Fusion explained — Serghei's Blog](https://blog.serghei.pl/posts/reciprocal-rank-fusion-explained/)
- [How to Evaluate RAG Pipelines with RAGAS (faithfulness, context precision/recall) — INVRA](https://www.invra.co/en/rag-evaluation-with-ragas-measuring-faithfulness-context-precision-and-recall-in-production/)
