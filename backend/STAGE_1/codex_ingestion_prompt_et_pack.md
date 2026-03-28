# Codex prompt: ingest and implement the ET product pack

You are working inside the existing ET concierge backend.

## Goal
Use the provided ET product pack to upgrade retrieval, grounding, and recommendation quality.

## Input files
- `backend_data_et_sources.json`
- `backend_data_et_product_registry.json`
- `backend_data_et_chunks.jsonl`
- `backend_data_et_eval_prompts.json`

## Required work
1. **Ingest source registry**
   - Read `backend_data_et_sources.json`.
   - Treat this as the allow-list of URLs and canonical source metadata.
   - Add a loader that can fetch, normalize, and chunk these sources.
   - Preserve `source_id`, `product_area`, `page_type`, `source_tier`, `source_of_truth`, `verification_status`, and `last_verified_at`.

2. **Implement structured product registry**
   - Load `backend_data_et_product_registry.json` into a collection or cached registry layer.
   - Expose helpers like:
     - `get_product_registry(product_name)`
     - `list_products_by_category(category)`
     - `route_user_intent_to_products(intent, user_profile)`

3. **Dual retrieval**
   - Keep vector retrieval for chunks.
   - Add structured lookup for product facts before or alongside vector retrieval.
   - For questions like “What do I get with ET Prime?” or “Which ET product fits me?”, consult the registry first, then enrich with vector chunks.

4. **Verification-aware answer generation**
   - If a fact has `verification_status = official_public`, answer confidently with citations.
   - If a fact has `verification_status = conflicting_public_signals`, the assistant must:
     - explicitly say public ET pages show mixed signals
     - cite both sides if available
     - avoid a binary unsupported claim
   - If a benefit has constraints (for example mobile-number-limited activation), ask an eligibility follow-up before giving a final recommendation.

5. **Chunking**
   - Use bootstrap chunks from `backend_data_et_chunks.jsonl` only as seed content.
   - Prefer live normalized fetches from the source registry when possible.
   - Store metadata on each chunk:
     - `product_name`
     - `source_id`
     - `source_url`
     - `page_type`
     - `verification_status`
     - `tags`

6. **Recommendation routing**
   - Implement product-routing logic that supports:
     - beginner start path
     - markets/investor path
     - learning path
     - wealth path
     - events/community path
   - Use the registry + session profile + journey history.
   - Favor ET Prime as broad entry point only when the user wants broad ET access.
   - Favor ET Markets for market tools.
   - Favor ET Portfolio for holdings/goals tracking.
   - Favor ETMasterclass for skill-building and executive learning.
   - Favor ET Events portals for live-event discovery.

7. **Evaluation**
   - Load `backend_data_et_eval_prompts.json`.
   - Create an evaluation script that runs each prompt and scores:
     - correct routing
     - citation presence
     - correct conflict handling
     - no hallucinated product facts
   - Save per-prompt outputs and failures.

8. **UI/API support**
   - Add a field in the response payload for:
     - `recommended_products`
     - `source_citations`
     - `verification_notes`
   - Ensure `/sessions` and session history preserve product-routing decisions.

## Strict rules
- Do not invent ET products or merge unrelated ET properties by assumption.
- Do not hardcode unsupported pricing or trial facts.
- Do not scrape the entire ET domain blindly. Use the source pack allow-list first.
- Do not remove existing journey-history tracking.
- Do not weaken existing RAG behavior; improve it with structure and provenance.

## Success criteria
- The assistant can answer ET product questions with citations.
- The assistant can route users to the right ET path.
- Trial/pricing contradictions are handled safely.
- Evaluation prompts show fewer unsupported answers.
- The vector store is enriched with better metadata and registry-aware retrieval.
