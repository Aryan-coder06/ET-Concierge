# Codex Prompt: Non-Prime Heavy ET RAG Upgrade

You are upgrading an existing ET-focused RAG system that currently over-indexes on ET Prime / ET Markets / ET Masterclass.

## Current backend facts
The project currently uses local JSON / JSONL packs via:
- backend/app/chatbot/registry.py
- backend/app/chatbot/ingestion.py

The current problem is:
- too much product hardcoding or hardcoded assumptions in routing behavior
- ET Prime often becomes the default answer even on ET Money / ET Rise / ETGovernment / Brand Equity / ET Now / Panache / TravelWorld queries
- general news queries get trapped in repeated profiling loops

## Files to use
- backend_data_et_nonprime_heavy_sources.json
- backend_data_et_nonprime_heavy_product_registry.json
- backend_data_et_nonprime_heavy_chunks.jsonl
- backend_data_et_nonprime_heavy_eval_prompts.json
- backend_data_et_router_behavior_policy.json

## Required code changes
1. Refactor registry/router logic so product names, aliases, lane names, and routing hints come from JSON.
2. Make these first-class lanes: ET Money, ET Rise / ET SME, ET Brand Equity, ETGovernment, ET Now, ET TravelWorld, ET Panache, ET World / International.
3. Add query modes: concierge_mode, information_mode, news_mode.
4. In information_mode and news_mode, answer directly first and avoid unnecessary profiling.
5. Only use ET Prime as a broad default when the user is vague and asks where to start in ET overall.
6. Boost exact alias/product matches heavily before broad ET retrieval.
7. Keep JSON / JSONL as the feed mechanism and reduce Python-side product hardcoding to near zero.
8. Add scheduled refresh ingestion for ET world/international, ET Now feeds, ETGovernment home, Brand Equity home, TravelWorld home, and ET Money help/home.
9. Ensure UI/sidebar lane matches the same lane chosen in prose.
10. Re-run eval prompts and fix any ET Prime fallback bias.

## Output expectation
Modify the codebase so the assistant:
- knows these non-Prime ET products deeply
- answers naturally
- stops forcing profile loops for direct/news questions
- and stops leading every conversation back to ET Prime