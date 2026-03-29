# ET Non-Prime Heavy Expansion Pack

This pack is designed to aggressively reduce ET Prime / ET Markets over-bias.

## Why this exists
Your current RAG already has enough ET Prime, ET Markets, and ET Masterclass coverage.
The failure mode now is different:
- direct ET Money questions still drift back to ET Prime
- ET Rise / SME / founder intent is underfed
- Brand Equity, ETGovernment, ET Now, TravelWorld, and Panache are too weakly represented
- general news or world-affairs prompts are incorrectly routed into profiling loops

## What this pack does
1. expands underrepresented ET verticals
2. adds a router behavior policy
3. gives bootstrap chunks that explain those lanes in natural language
4. adds eval prompts that catch ET Prime fallback bias

## Important limitation
A static JSON/bootstrap pack alone cannot solve fresh world-news queries forever.
To answer current world affairs well, you should ingest ET's International / World News pages on a schedule.
This pack includes those source URLs and router rules so Codex can implement that.

## Files
- backend_data_et_nonprime_heavy_sources.json
- backend_data_et_nonprime_heavy_product_registry.json
- backend_data_et_nonprime_heavy_chunks.jsonl
- backend_data_et_nonprime_heavy_eval_prompts.json
- backend_data_et_router_behavior_policy.json
- backend_data_README_et_nonprime_heavy_pack.md
- codex_prompt_et_nonprime_heavy_upgrade.md

## Recommended merge strategy
1. Keep your current Prime / Markets / Masterclass data.
2. Merge these products as equally routable lanes.
3. Increase retrieval weight for exact product-name matches on ET Money / Rise / Brand Equity / ETGovernment / ET Now / TravelWorld / Panache.
4. Lower the broad-default score of ET Prime when the query is explicitly about another lane.
5. Add information_mode and news_mode so the bot stops over-profiling.
6. Schedule fresh crawling for ET world/international URLs if you want news-style answers.

## What not to do
- Do not delete Prime/Markets entirely.
- Do not hardcode new product lists inside Python logic.
- Do not keep any fallback that says 'if uncertain, recommend ET Prime' without checking lane-specific products first.