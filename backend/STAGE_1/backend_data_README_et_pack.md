# ET Product Pack for RAG Ingestion

Generated on: 2026-03-27

## Files
- `backend_data_et_sources.json` — allow-list of official sources and metadata
- `backend_data_et_product_registry.json` — structured product facts for routing and recommendation
- `backend_data_et_chunks.jsonl` — paraphrased retrieval chunks for bootstrap ingestion
- `backend_data_et_eval_prompts.json` — evaluation questions and expected behaviors
- `codex_ingestion_prompt_et_pack.md` — prompt to give Codex for ingestion and registry-aware retrieval

## Design principles
1. Prefer **official ET pages** and official app-store listings.
2. Store **structured facts** and **retrieval chunks** separately.
3. Attach a `verification_status` to every important fact.
4. Treat trial/pricing/benefit claims as time-sensitive.
5. Do not answer more confidently than the underlying source quality allows.

## Verification statuses
- `official_public` — directly supported by an official ET page or official app-store listing
- `conflicting_public_signals` — public official surfaces disagree; assistant must answer carefully
- `needs_manual_review` — use when a page is gated, heavily dynamic, or unclear

## Recommended ingest order
1. ET Prime FAQ / About / Plans
2. ET Markets app listing + tool pages
3. ET Portfolio
4. ET Wealth Edition / Print Edition
5. ETMasterclass
6. ET Events portals
7. ET Benefits / partner offers

## Runtime answer style
- If `verification_status == official_public`, answer normally with citations.
- If `verification_status == conflicting_public_signals`, explicitly mention that public ET pages are mixed and ask the user to verify the latest checkout or live page.
- If a benefit has activation constraints, ask the quick eligibility question before overpromising.

## Important note on chunks
The `backend_data_et_chunks.jsonl` file contains **paraphrased summary chunks** intended for bootstrapping a RAG pipeline safely. For production retrieval, fetch and normalize the live HTML from `backend_data_et_sources.json` at ingest time and regenerate embeddings from the cleaned page text.
