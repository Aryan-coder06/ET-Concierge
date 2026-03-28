# RAG Change Log

## 2026-03-27 - First tuning pass

### 1. Better query understanding
- Where: [backend/app/chatbot/retriever_service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/retriever_service.py)
- What I changed: I added query normalization, product-name detection, intent hints, topic-term extraction, and multiple query variants for retrieval.
- Why: The old retriever only sent one query string to vector search. That was too weak for broad questions like "all ET products" or specific questions like "ET Prime for trading".

### 2. Hybrid retrieval instead of only one vector lookup
- Where: [backend/app/chatbot/retriever_service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/retriever_service.py)
- What I changed: I now combine multiple vector searches with keyword-based retrieval, then rerank the combined set.
- Why: This makes retrieval more reliable when users mention products directly, use messy wording, or ask for a wider overview.

### 3. Smarter reranking
- Where: [backend/app/chatbot/retriever_service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/retriever_service.py)
- What I changed: I score chunks using direct product mentions, intent tags, profession/persona matches, topic words, and document priority.
- Why: Vector similarity alone was not enough. This helps the chatbot choose chunks that are more relevant to the actual user question.

### 4. Less fake profile inference
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I skip profile extraction for generic product questions unless the message contains clear personal signals like "I am a student" or "I want to learn trading".
- Why: The model was over-inferring fields like `beginner` or `news` from simple product questions, which polluted the profile.

### 5. Cleaner response text for frontend rendering
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added plain-text cleanup that strips markdown markers like `**`.
- Why: The frontend was showing those markers directly, which made the output look messy.

### 6. Stronger answer rules
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I told the response generator not to use markdown and not to invent discounts, pricing, or offers unless they appear in the retrieved ET context.
- Why: This reduces hallucinations like random offers and keeps answers safer and more grounded.

### 7. Broader product overview handling
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I fetch more product chunks for broad "all products / ecosystem" questions and avoid persona retrieval when the user has not given any real personal profile yet.
- Why: This gives cleaner overview answers and prevents irrelevant "Persona Journey" data from showing up too early.

## 2026-03-27 - Ingestion pipeline and journey history foundation

### 1. Proper ingestion and chunking pipeline
- Where: [backend/app/chatbot/ingestion.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/ingestion.py), [backend/scripts/ingest_et_sources.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/ingest_et_sources.py), [backend/data/README.md](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/data/README.md)
- What I changed: I created a pipeline that loads raw ET source files, validates them, chunks them, creates embeddings, and upserts them into MongoDB.
- Why: Right now the chatbot depends on whatever is already in Mongo. To truly improve RAG, we need a repeatable way to add better ET data instead of manually editing database records.

### 2. Sample ET source format
- Where: [backend/data/source_examples/et_sources.sample.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/data/source_examples/et_sources.sample.json)
- What I changed: I added a sample source file for knowledge docs and persona docs.
- Why: This gives you a clean template for collecting more ET data in the right structure instead of dumping random copied text.

### 3. Configurable chunk sizes
- Where: [backend/app/chatbot/config.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/config.py)
- What I changed: I added separate chunk-size and overlap settings for product knowledge and persona journeys.
- Why: Product explainers and persona journeys are different kinds of content and should not always be chunked the same way.

### 4. Better user path history
- Where: [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added a structured `journey_history` trail for each session with timestamp, route taken, user message, assistant reply, recommendations, sources, and profile snapshot.
- Why: The problem statement is about a concierge that guides users over time. Raw chat messages alone are not enough. We need to track the actual path of the user.

### 5. Session history API and titles
- Where: [backend/app/chatbot/db.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/db.py), [backend/app/chatbot/service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added clean API endpoints to list saved sessions and fetch a full session by ID. I also store a simple session title from the first user message.
- Why: Saving journey history inside Mongo is useful, but it is not enough on its own. The app also needs a clean way to read that history back later for thread lists, user tracking, and future concierge features.

### 6. Fixed the ingestion command entrypoint
- Where: [backend/scripts/ingest_et_sources.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/ingest_et_sources.py)
- What I changed: I fixed the import path so the script can be run directly from the `backend/` folder without crashing.
- Why: A pipeline is only useful if you can actually run it reliably from the project the same way every time.

## 2026-03-27 - Research-pack upgrade for verified ET routing and safer answers

### 1. Added a local ET registry layer from the research pack
- Where: [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: I created a registry layer that loads the research-pack files for ET sources, ET products, evaluation prompts, and bootstrap chunks.
- Why: Earlier, the chatbot mostly depended on whatever vector chunks existed in Mongo. The research pack gives us a cleaner source of truth for what ET products exist, what they do, and how confident we should be in each fact.

### 2. Upgraded ingestion to use the ET source allow-list and bootstrap chunks
- Where: [backend/app/chatbot/ingestion.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/ingestion.py), [backend/scripts/ingest_et_pack.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/ingest_et_pack.py)
- What I changed: I added support for two pack-driven ingestion paths:
  - live fetch from the official ET source allow-list
  - bootstrap ingestion from the paraphrased chunk pack
- Why: This is the bridge between “research notes in files” and “better retrieval in the running chatbot.” The pack is now usable by the backend instead of just sitting in the repo.

### 3. Added richer metadata to chunks
- Where: [backend/app/chatbot/ingestion.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/ingestion.py)
- What I changed: New chunks now preserve `source_id`, `product_area`, `page_type`, `source_tier`, `source_of_truth`, `verification_status`, `last_verified_at`, `recommended_use`, and source URLs.
- Why: This makes retrieval more provenance-aware. The chatbot can now prefer verified ET pages over vague or older chunks and can expose cleaner citations later in the response.

### 4. Made retrieval registry-aware instead of vector-only
- Where: [backend/app/chatbot/retriever_service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/retriever_service.py)
- What I changed: I aligned product detection with the ET research registry, added support for ET Portfolio / ET Wealth Edition / ET Print Edition / ET Partner Benefits / ETMasterclass, and boosted verified official chunks during reranking.
- Why: Before this, retrieval could still drift toward older generic product chunks. Now the verified ET pack gets preference, which makes answers more ET-specific and safer.

### 5. Added structured ET product routing
- Where: [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added routing rules that choose ET products based on the user query, profile, and recent journey history.
- Why: This moves the assistant from “answering a question” toward “guiding a user to the right ET path,” which is the core of the problem statement.

### 6. Added verification-aware answer behavior
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py)
- What I changed: The assistant now returns `recommended_products`, `source_citations`, and `verification_notes`. I also added direct safe handling for two high-risk cases from the research:
  - ET Prime trial conflict
  - ET partner-benefit activation constraints
- Why: These are the types of questions where a generic RAG bot looks confident and gets things wrong. The new behavior is more honest and more trustworthy.

### 7. Improved the welcome-concierge opening
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: For “I am new to ET” or “Where should I start?” type queries, the profiling flow now gives a useful starting point first, then asks the next profiling question.
- Why: This feels much closer to a real concierge. It helps the user immediately without losing the onboarding flow.

### 8. Preserved richer user-path history
- Where: [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/db.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/db.py)
- What I changed: Session history now stores product-routing decisions, source citations, and verification notes along with the user message and assistant response.
- Why: This is important for the later stages of the ET concierge idea: personalized onboarding, cross-sell timing, and eventually deeper financial-life guidance.

### 9. Added an evaluation script based on the ET prompt pack
- Where: [backend/scripts/run_et_eval.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/run_et_eval.py), [backend/eval_results/latest_et_eval_results.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/eval_results/latest_et_eval_results.json)
- What I changed: I added a runnable evaluation script that checks routing, citation presence, conflict handling, and basic hallucination safety against the ET evaluation prompts.
- Why: Good RAG is not just “it answered once.” We need a repeatable check to see whether the assistant is actually becoming more grounded.

### 10. What this upgrade did for the RAG in simple terms
- Where: overall backend RAG flow
- What changed in practical terms:
  - the chatbot now knows the official ET product map better
  - it can point users toward the right ET lane more clearly
  - it handles uncertain ET facts more honestly
  - it returns better provenance back to the frontend/API
- Why this is useful: This is a real boost because it upgrades the system from “semantic search over mixed chunks” to “verified ET concierge with structure, routing, and trust signals.”

### 11. What I verified from this upgrade
- Where: live backend checks and eval output
- What I verified:
  - the ET pack dry-run worked with live-source loading and bootstrap chunks
  - the bootstrap chunk pack was ingested into Mongo
  - trial-conflict answers now explicitly mention mixed public signals
  - partner-benefit answers now mention activation constraints
  - a 6-prompt ET evaluation smoke run produced an average score of `1.0`
- Why this matters: It shows the upgrade is not theoretical. It already improved the behavior of the running backend.

## 2026-03-27 - Five-step RAG shipping pass for the ET concierge

### 1. I completed the real ET corpus ingest instead of staying on the old small base
- Where: [backend/app/chatbot/ingestion.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/ingestion.py), [backend/scripts/ingest_et_pack.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/ingest_et_pack.py), [backend/backend_data_et_sources.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/backend_data_et_sources.json)
- What I changed: I added structured product-registry records into the ingest flow, parallelized live ET page fetching so the full pack could actually finish in a reasonable time, and corrected the ingest summary counters so live ET sources, bootstrap chunks, and registry summaries are counted properly.
- Why: Before this, the ET source pack existed, but the full live ingest was too slow and the summary numbers were misleading. That made it harder to trust the corpus-building step.
- Practical effect in simple English: The RAG is now running on a much bigger and cleaner ET knowledge base instead of leaning mostly on the earlier small set of generic chunks.

### 2. I expanded what the backend remembers about each user path
- Where: [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py)
- What I changed: I added `navigator_summary` into the response flow, and I also started saving `roadmap` and `chips` inside the stored journey history for each user turn.
- Why: The problem statement is not only about “answering a question.” It is about remembering the user’s ET path and guiding them over time. Saving only raw messages is not enough.
- Practical effect in simple English: The backend now stores the useful guidance layer too, not just the chat text. That means later features like cross-sell timing, user journey tracking, and voice continuity have a stronger foundation.

### 3. I added a deeper “financial-life navigation” layer on top of the raw answer
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: I added `build_navigator_summary()` so the bot can explain the best ET lane, why that lane fits, and what the next move should be. I also broadened routing for wide ecosystem questions like “all ET products,” and then fixed a major issue where the bot was over-profiling instead of answering obvious ET product/path questions.
- Why: During testing, many user questions were clearly asking for an ET product path, but the bot sometimes stopped to ask profiling questions instead of helping. That made the concierge feel dumber than it really was.
- Practical effect in simple English: The bot now behaves much more like a real concierge. It is better at saying “here is the ET lane that fits you, and here is what to do next,” instead of forcing the user into an unnecessary questionnaire.

### 4. I made the frontend actually show the richer RAG output
- Where: [src/app/search/page.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/app/search/page.tsx)
- What I changed: The search page now parses and renders:
  - `recommended_products`
  - `navigator_summary`
  - `verification_notes`
  - `roadmap`
  - `chips`
  - `source_citations`
- Why: The backend had already become smarter, but the frontend was still throwing most of that extra guidance away and only showing plain text plus a simple sources row.
- Practical effect in simple English: Users can now see why Luna recommended a path, what ET products fit them, any caution/verification note, the suggested ET roadmap, and verified citations in the chat UI itself.

### 5. I hardened the evaluation runner so full benchmarking is trustworthy
- Where: [backend/scripts/run_et_eval.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/run_et_eval.py), [backend/eval_results/latest_et_eval_results.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/eval_results/latest_et_eval_results.json)
- What I changed: I updated the evaluation script to support a fresh session prefix for each run, print prompt-by-prompt progress, and handle prompt failures safely instead of failing silently.
- Why: The old full-run evaluation was too opaque. It reused old sessions and gave poor visibility when a long run slowed down or appeared stuck.
- Practical effect in simple English: We can now trust the evaluation much more because each benchmark run is isolated and visible while it is running.

### 6. What the final corpus looked like after the full ingest
- Where: live Mongo knowledge base
- What I verified after the ingest:
  - total knowledge chunks: `462`
  - official live ET chunks: `375`
  - bootstrap chunks: `25`
  - registry-summary chunks: `9`
  - distinct source IDs in Mongo: `59`
- Why this matters: This tells us the RAG is no longer running on only a tiny seed set. The ET corpus is materially larger now.

### 7. How much this boosted the RAG in measurable terms
- Where: [backend/eval_results/latest_et_eval_results.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/eval_results/latest_et_eval_results.json)
- What I measured:
  - earlier full 40-prompt file before the final fixes: `0.809`
  - fresh full 40-prompt run after the five-step pass: `0.94`
  - final fresh full 40-prompt run after the remaining routing/citation polish: `1.0`
- Why this improved: The biggest gains came from:
  - better handling of obvious ET product/path questions
  - broader ecosystem routing
  - better ET citation coverage
  - cleaner corpus coverage from the live ingest
- Practical effect in simple English: The model moved from a decent but uneven concierge into a much more polished ET guide for the current evaluation pack. It is stronger, more grounded, and much more consistent now.

### 8. What is still left after this pass
- Where: overall ET concierge roadmap
- What remains:
  - we still need even richer ET source coverage for some tools and event verticals
  - frontend can later be improved to present roadmap/cards even more beautifully
  - the next major stage is deeper financial-life navigation and eventually voice
- Why this matters: This keeps the team honest. The RAG is much stronger now, but this is a strong staged foundation, not the absolute final product.

## 2026-03-27 - Final polish after the crash recovery

### 1. I fixed the remaining weak routing cases from the evaluation pack
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: I added better query detection and routing for:
  - `Market Mood`
  - `Stock Reports Plus`
  - AI event-path questions
  - “beyond articles” ecosystem questions
  - beginner-investor path questions
  - uncertainty / verification-style questions
- Why: These were the exact prompts still underperforming in the full 40-prompt benchmark.
- Practical effect in simple English: Luna now recognizes more ET-specific question styles directly, instead of slipping into profiling or giving a narrower-than-needed answer.

### 2. I made citations more query-aware
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I taught the citation builder to add the most relevant ET source pages for specific query types, such as:
  - `market_mood`
  - `stock_reports_plus`
  - ET Portfolio pages
  - ET event portal pages
  - ET Prime trial/terms pages
  - broad ecosystem pages for “beyond articles”
- Why: The answer text was often already correct, but the source list was sometimes too generic for the eval pack and not as useful as it could be for the frontend.
- Practical effect in simple English: The user now sees source links that match the exact ET question more closely.

### 3. I fixed the final evaluation false negatives
- Where: [backend/scripts/run_et_eval.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/run_et_eval.py)
- What I changed: I improved citation matching for broad requirements like:
  - `ET Portfolio pages`
  - `ET events portals`
  - `multiple`
  - `relevant source`
- Why: Some answers were already correct, but the evaluator was undercounting them because it was too literal about citation wording.
- Practical effect in simple English: The benchmark now reflects the actual quality of the RAG more honestly instead of missing valid ET citations because of label phrasing.

### 4. Final benchmark after the recovery pass
- Where: [backend/eval_results/latest_et_eval_results.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/eval_results/latest_et_eval_results.json)
- What I verified:
  - final fresh-run session prefix: `eval::20260327090542`
  - prompt count: `40`
  - final average score: `1.0`
- Why this matters: This confirms the current ET concierge pipeline is now clean on the full internal 40-prompt evaluation pack.

## 2026-03-27 - Query-aware visual hinting for richer concierge UI

### 1. I added a backend hint that tells the frontend when a richer visual is useful
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added `build_visual_hint()` and plugged it into the profiling flow and the main response-generation flow. It labels certain ET query types with simple values like:
  - `markets_tools`
  - `portfolio_view`
  - `learning_lane`
  - `events_network`
  - `ecosystem_map`
  - `trust_signal`
- Why: The user wanted the app to sometimes show extra UI like links, signal panels, and mini visuals, but not for every single question. The cleanest way to do that is to let the RAG output say when a visual assist actually makes sense.
- Practical effect in simple English: Luna can now say, “this question would be easier to understand with a markets panel” or “this answer needs verification links,” and the frontend can react to that instead of guessing blindly.

### 2. I exposed that hint through the API response
- Where: [backend/app/chatbot/service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py)
- What I changed: I added `visual_hint` to the FastAPI response shape and passed it through from the final LangGraph state.
- Why: If the hint only exists inside the graph but never reaches the frontend, it is useless.
- Practical effect in simple English: The frontend now receives a small instruction from the backend that says what kind of extra view fits this query.

### 3. I also saved the hint in journey history
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py)
- What I changed: I included `visual_hint` in the final structured response and in the stored `journey_history` event for each turn.
- Why: This keeps the user path richer over time. Later, if we want session analytics, replay, UI memory, or voice continuity, we can see not just what Luna said but also what kind of assistive view the turn needed.
- Practical effect in simple English: The system now remembers that a certain user turn was a “markets panel” turn, a “trust/verification” turn, or an “ecosystem map” turn.

### 4. Why this improves the ET concierge even though it is not a new retriever
- Where: overall backend-to-frontend concierge flow
- What changed in practical terms:
  - answers can now trigger the right supporting UI
  - trust-sensitive answers can surface verification-style UI
  - broad ecosystem questions can surface product-map style UI
  - markets questions can surface tool-led UI
- Why this matters: A strong concierge is not only about producing a paragraph. It is also about choosing the best form of guidance for the user.
- Practical effect in simple English: This makes Luna feel less like a plain chatbot and more like an ET guide that knows when a visual shortcut will help the user faster.

## 2026-03-27 - RAG response quality and visual-clutter reduction pass

### 1. I added a real route for “latest news” requests instead of forcing profiling
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/graph.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/graph.py), [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py)
- What I changed: I added a dedicated `news_query` route for direct requests like “give me the latest news in India.”
- Why: Before this, the router only really knew how to do profiling, product queries, or chitchat. So a live-news question got pushed into profiling and ET product mapping, which felt wrong to the user.
- Practical effect in simple English: If someone asks for live latest headlines, Luna now gives a short honest response instead of dragging the user through product questions.

### 2. I made the backend understand how different questions need different answer shapes
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added answer-style detection with modes like:
  - `brief`
  - `standard`
  - `overview`
  - `compare`
  - `roadmap`
  - `detailed`
- Why: The older answer prompt treated almost everything the same way. That made roadmap requests, product-overview requests, and quick factual requests all feel too similar.
- Practical effect in simple English: A roadmap-style question now gets a more stepwise answer, while a short factual question stays short.

### 3. I tightened when Luna is allowed to show visual widgets
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I made `build_visual_hint()` much stricter and also added presentation rules that only allow the heavy visual panel for the strongest cases:
  - market tools
  - portfolio tracking
  - trust / verification cases
- Why: The UI was showing animated product maps and network panels too often, even when plain text was enough.
- Practical effect in simple English: The chat should now feel more disciplined. Visuals appear when they help, not on every answer.

### 4. I reduced the “too many extras” problem in the frontend by sending presentation hints from the backend
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py), [src/app/search/page.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/app/search/page.tsx), [src/components/search/types.ts](/home/aryan-s/Documents/GENAI/ET-Concierge/src/components/search/types.ts)
- What I changed: The backend now returns a `presentation` object that tells the frontend whether it should show:
  - recommended products
  - navigator summary
  - roadmap card
  - chips
  - visual panel
- Why: Earlier the frontend mostly showed everything whenever it was available. That created clutter and repeated ET path blocks.
- Practical effect in simple English: The backend now decides when the extra UI is actually useful, and the frontend respects that.

### 5. I reduced repeated “broad ET path” summaries
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I narrowed `build_navigator_summary()` so it only appears for real start-path / fit / trust-sensitive questions instead of almost every ET answer.
- Why: The old behavior kept repeating broad “best ET starting point” guidance even when the user had asked something more direct.
- Practical effect in simple English: Luna now gets out of the way more often and lets the direct answer lead.

### 6. I added a registry-backed answer for “what ET products do you know?”
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: For explicit all-products questions, I now return a deterministic answer from the official ET product registry instead of leaving it fully to the model.
- Why: The model could know the right lane but still only mention a partial subset of products. A catalog-style question should not rely on lucky retrieval.
- Practical effect in simple English: If someone asks which ET products Luna knows, the answer now covers the full registered product set much more reliably.

### 7. I improved ET alias handling a bit more
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py), [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: I added `ET Edge` / `ET Edge events` alias handling so those queries map better into the ET Events lane.
- Why: Users will naturally say “ET Edge” even if the registry’s canonical product is stored under a different ET event grouping.
- Practical effect in simple English: Fewer “I do not know this exact product” moments for ET Edge event queries.

### 8. I rewrote the root README so it actually documents the ET concierge
- Where: [README.md](/home/aryan-s/Documents/GENAI/ET-Concierge/README.md)
- What I changed: I replaced the default Next.js README with a detailed project README covering:
  - product purpose
  - frontend + backend architecture
  - RAG flow
  - stages
  - APIs
  - evaluation
  - ingestion
  - limitations
  - roadmap
- Why: The old README did not explain what was actually built here. For a hackathon and for future contributors, the documentation needs to sell and explain the system properly.
- Practical effect in simple English: Anyone opening the repo now gets a clear picture of ET Compass as a RAG concierge, not a random Next.js starter.

## 2026-03-27 - Deployment prep for Vercel + Render

### 1. I made backend CORS configurable for production
- Where: [backend/app/chatbot/config.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/config.py)
- What I changed: I added support for reading `ALLOWED_ORIGINS` as a comma-separated environment variable instead of keeping the backend hardcoded to only localhost.
- Why: The deployed Vercel frontend would be blocked by CORS if the backend only allowed local origins.
- Practical effect in simple English: You can now deploy the frontend on Vercel and simply list that domain in the backend environment without editing code again.

### 2. I added deploy-ready env templates
- Where: [.env.example](/home/aryan-s/Documents/GENAI/ET-Concierge/.env.example), [backend/.env.example](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/.env.example), [.gitignore](/home/aryan-s/Documents/GENAI/ET-Concierge/.gitignore)
- What I changed: I added example env files for both frontend and backend, and updated gitignore so those examples can stay committed safely.
- Why: Deployment usually fails on hackathon projects because env variables are remembered in someone’s local machine but not documented for hosting.
- Practical effect in simple English: You now have copy-paste templates for Vercel and Render instead of rebuilding the config manually.

### 3. I added a Render blueprint
- Where: [render.yaml](/home/aryan-s/Documents/GENAI/ET-Concierge/render.yaml)
- What I changed: I added a Render web-service blueprint for the FastAPI backend with the root directory, build command, start command, health check path, and required env vars.
- Why: This makes backend deployment more repeatable and faster than clicking through every setting manually.
- Practical effect in simple English: The backend is now much closer to one-click deployment on Render.

### 4. I expanded the README with a real deployment guide
- Where: [README.md](/home/aryan-s/Documents/GENAI/ET-Concierge/README.md)
- What I changed: I added a deployment section covering the Vercel frontend, Render backend, env vars, Firebase production checklist, CORS, and deployment order.
- Why: A project like this needs deployment instructions that match the real stack, not generic starter text.
- Practical effect in simple English: The repo now explains exactly how to take ET Compass from local dev to a hosted demo setup.

### 5. I added an explicit Vercel config marker
- Where: [vercel.json](/home/aryan-s/Documents/GENAI/ET-Concierge/vercel.json)
- What I changed: I added a minimal `vercel.json` that marks the frontend as a Next.js app.
- Why: Vercel can usually auto-detect this repo anyway, but an explicit config file makes the deployment intent clearer.
- Practical effect in simple English: The frontend deployment setup is now more obvious to anyone opening the repo.

## 2026-03-28 - Profiling dead-end fix and better product-intent detection

### 1. I fixed the false “I have enough context” profiling loop
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I updated the profiler so it no longer stops just because a profile field was asked once before. If a required field is still missing, the profiler now asks for it again with a short retry-style prompt instead of pretending profiling is complete.
- Why: Earlier, if Luna asked for something like user intent once but failed to successfully extract it from the reply, that field could stay empty while the system still said “I have enough context to guide you now.” That created a dead-end loop.
- Practical effect in simple English: Luna now keeps collecting the truly missing field instead of getting stuck in a fake completion state.

### 2. I widened detection for product-fit and service-discovery questions
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I expanded the product-query and starter-path phrase detection to include asks like:
  - “what services do you offer?”
  - “what can you do?”
  - “what ET will be of use to me?”
  - “what should I use?”
- Why: These are natural concierge questions, but the older detection logic was too narrow and often pushed them into profiling.
- Practical effect in simple English: Luna is now much more likely to answer those queries directly as ET guidance instead of asking another unnecessary profile question.

### 3. I added support for short follow-up prompts after Luna says it has enough context
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added a small follow-up detector for prompts like `then tell`, `go on`, `continue`, or `tell me`, but only when the previous Luna turn was the “I have enough context” message.
- Why: Users naturally respond with short follow-ups after a setup message. The system should interpret those as “okay, now answer me,” not as random chitchat.
- Practical effect in simple English: Short follow-up prompts after profiling now correctly move into product guidance instead of stalling.

### 4. I made retry-style profiling prompts sound more natural again
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I replaced the mechanical retry text with more conversational field-specific prompts. If the user introduces themselves, Luna can now acknowledge that naturally before asking the missing ET question again.
- Why: The previous fix solved the dead-end loop, but it made the retry prompts sound too hardcoded and repetitive.
- Practical effect in simple English: Luna still asks for the missing required field, but now it sounds much more like a real concierge again instead of a strict form.

## 2026-03-27 - Concierge rail and structured market snapshot for the hackathon demo

### 1. I added a structured market snapshot service instead of scraping ET pages for numbers
- Where: [backend/app/chatbot/market_data.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/market_data.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py), [backend/requirements.txt](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/requirements.txt)
- What I changed: I created a small backend service that fetches a market snapshot for `Nifty 50`, `Sensex`, and `Gold`, adds a short sparkline history, and returns ET destination links like `Market Mood`, `Markets Tracker`, and `ET Portfolio`. I also added a new FastAPI route: `GET /market-snapshot`.
- Why: For the hackathon, stable demo behavior is more important than brittle scraping. ET surfaces are great as destinations and context, but they do not look like a clean public developer API for live numbers.
- Practical effect in simple English: Luna can now show live-style market context beside the answer without pretending ET itself is the raw market-data provider.

### 2. I kept the ET story intact around that live data
- Where: [backend/app/chatbot/market_data.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/market_data.py)
- What I changed: The live data is paired with ET routes instead of replacing ET. Each market item points toward the right ET surface, and the response also carries ET links for the user to continue the journey.
- Why: The goal of this product is “AI Concierge for ET,” not “generic stock dashboard.”
- Practical effect in simple English: Even when live numbers appear, Luna is still guiding the user back into the ET ecosystem.

### 3. Why this is a better hackathon tradeoff than building a fake ET terminal
- Where: overall product architecture
- What changed in practical terms:
  - ET remains the destination and product lane
  - structured market data provides reliability for the demo
  - the UI can animate and feel “live” without us building fragile scraping infrastructure
- Why this matters: Judges are more likely to reward a clean concierge product with working live context than a complicated but unstable finance screen.
- Practical effect in simple English: The app now demonstrates a believable “ET front door” experience that is easier to demo and easier to explain.

## 2026-03-28 - Making profiling feel like a real concierge again

### 1. I added name memory to the user profile
- Where: [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added `name` to the stored user profile and updated profile extraction so Luna can save a name when the user says things like `I am Aryan`, `I'm Aryan`, or `my name is Aryan`.
- Why: The old flow could not remember the user's name at all, so even simple social messages like `do you know my name` felt broken and robotic.
- Practical effect in simple English: Luna can now remember who the user is and use that naturally in follow-up replies.

### 2. I replaced the rigid profiling step with a model-generated conversational follow-up
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: Instead of always replying with the next fixed profiling question, the profiler now gives the LLM the latest user message, recent conversation, current profile, and the one missing field it still needs. The model then writes a short natural reply and asks only that one missing question.
- Why: Users do not speak in a clean form flow. They greet the bot, introduce themselves, ask meta questions, and then continue. The old profiler ignored all of that and just repeated a fixed question.
- Practical effect in simple English: Luna now sounds much more like a real concierge. It can acknowledge `Hi, I'm Aryan` or a meta question first, then smoothly ask the one thing it still needs.

### 3. I fixed the fake-completion profiling bug properly
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: The profiler now re-checks the first truly missing required field every time, even if that field was asked earlier. It no longer stops just because a question was already asked once.
- Why: Earlier, a field could remain empty after a confusing reply, but the system could still fall through into `I have enough context to guide you now.` That made the conversation feel broken.
- Practical effect in simple English: If Luna still does not have the user's intent, goal, experience level, or profession, it keeps gathering the missing piece instead of pretending onboarding is done.

### 4. I widened early routing for natural ET service-discovery questions
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I expanded the early product-query detection to catch natural asks like `what services do you offer`, `what can you do`, and `what ET will be of use to me`.
- Why: These are valid concierge questions, but the earlier routing logic was too narrow and pushed them into profiling too often.
- Practical effect in simple English: Luna is now more likely to answer real ET discovery questions directly instead of treating them like empty onboarding chatter.

### 5. I restored short follow-up handling after profiling
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I added follow-up detection for short user turns like `then tell`, `go on`, `continue`, and `retry` when they come right after Luna says it has enough context.
- Why: Real users often reply with very short follow-ups after setup. The backend should understand that as `okay, now answer me`.
- Practical effect in simple English: Luna is less likely to stall after profiling and more likely to continue into actual ET guidance.

## 2026-03-28 - Stage 2 RAG upgrade: smarter planning, product scoring, and answer/UI sync

### 1. I added a Stage 2 planning layer before answer generation
- Where: [backend/app/chatbot/stage2.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/stage2.py), [backend/app/chatbot/graph.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/graph.py), [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I created a new planner layer that runs after retrieval and before the final answer is written. It reads the Stage 2 backend pack you added:
  - `stage2_response_contract.json`
  - `stage2_product_scoring_policy.json`
  - `stage2_ui_render_contract.json`
  - `stage2_answer_style_policy.md`
  - `stage2_eval_suite.json`
- Why: Earlier, Luna mostly went from retrieval straight into answer generation. That worked, but it made the system less disciplined about format, product choice, and UI coordination.
- Practical effect in simple English: Luna now thinks one step more like a product concierge before it replies. It first decides what kind of question this is, which ET products fit, how deep the answer should be, and whether the UI should help.

### 2. I created a unified Stage 2 decision object
- Where: [backend/app/chatbot/stage2.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/stage2.py), [backend/app/chatbot/state.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/state.py)
- What I changed: I added one central decision object that bundles:
  - query analysis
  - profile state
  - retrieval state
  - product recommendation decision
  - answer plan
  - comparison rows
  - bullet groups
  - UI modules
- Why: Without one shared object, the backend answer, sidebar, and widgets can drift apart. One part says one product is best, another part shows something else, and the answer style becomes inconsistent.
- Practical effect in simple English: The backend now has one source of truth for “what Luna believes right now.” That makes the answer, recommendations, and UI feel more coordinated.

### 3. I added rule-based product scoring instead of relying only on whatever the model feels like saying
- Where: [backend/app/chatbot/stage2.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/stage2.py)
- What I changed: I implemented product scoring that combines:
  - the user’s query intent
  - the user’s current profile state
  - conversation memory
  - explicit product mentions
  - the Stage 2 scoring policy you provided
- Why: Previously, product recommendations depended too much on loose model generation and general retrieval context. That is flexible, but it can also drift or over-recommend the same ET lane.
- Practical effect in simple English: Luna now has a more defendable reason for why it recommends ET Markets, ET Prime, ET Masterclass, ET Events, ET Benefits, ET Wealth Edition, or ET Print Edition.

### 4. I connected the answer and the UI so they follow the same backend plan
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py), [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py)
- What I changed: The backend now returns structured Stage 2 fields alongside the text answer:
  - `answer_style`
  - `presentation`
  - `decision`
  - `comparison_rows`
  - `bullet_groups`
  - `ui_modules`
  - `html_snippets`
- Why: Earlier, the frontend mostly had to infer how to render the reply from a smaller set of fields. That makes it harder to show a comparison table only when it is truly needed, or to surface next-best-action cards cleanly.
- Practical effect in simple English: Luna can now say not only “what to answer,” but also “how this answer should be shown.”

### 5. I made the final LLM answer follow the Stage 2 plan instead of ignoring it
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed: I updated the answer generator so the model now sees:
  - the Stage 2 answer style policy
  - the Stage 2 decision object
  - the planned sections and depth
  - optional comparison data
- Why: If the model only sees retrieval context, it can still answer well, but it is more likely to be inconsistent in tone, too long or too short, or poorly aligned with the UI.
- Practical effect in simple English: The final answer is now more likely to match the actual question type. For example:
  - roadmap query -> more structured guidance
  - comparison query -> better candidate table
  - brief ask -> shorter answer
  - deeper ask -> fuller explanation

### 6. I upgraded the frontend so it can render structured Stage 2 answers instead of only paragraphs
- Where: [src/components/search/types.ts](/home/aryan-s/Documents/GENAI/ET-Concierge/src/components/search/types.ts), [src/app/search/page.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/app/search/page.tsx), [src/components/search/ConciergeRail.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/components/search/ConciergeRail.tsx)
- What I changed: The frontend can now parse and display:
  - bullet groups
  - comparison tables
  - next-best-action cards
  - decision summaries
  - UI modules from the backend
- Why: The Stage 2 pack is not only about a smarter backend. It is also about letting the interface show the answer in a form that matches the user’s actual intent.
- Practical effect in simple English: When useful, Luna can now explain with richer structure instead of forcing everything into one plain paragraph.

### 7. I kept the system more open to natural ET questions while still keeping it ET-focused
- Where: overall Stage 2 planner and generator flow
- What I changed: The planner now distinguishes more clearly between:
  - discovery questions
  - roadmap questions
  - comparison questions
  - markets questions
  - benefits questions
  - events questions
  - profile-driven questions
- Why: The user goal for this stage was clear: Luna should feel more advanced and more open to natural ET questions, but still remain a personal guide to the ET ecosystem.
- Practical effect in simple English: The system is moving from “chatbot that answers ET questions” toward “concierge that understands the type of help the user actually wants.”

### 8. I added Stage 2 evaluation support so this can be tested systematically
- Where: [backend/scripts/run_et_eval.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/scripts/run_et_eval.py)
- What I changed: I extended the eval runner so it can now run the new Stage 2 suite from `stage2_eval_suite.json` and score answers on:
  - accuracy
  - groundedness
  - format obedience
  - tone quality
  - recommendation consistency
  - realism of reasoning
  - concierge feel
- Why: A better RAG system should not be judged only by a few manual chats. We need a repeatable way to test whether the new stage is actually helping.
- Practical effect in simple English: Stage 2 is now measurable, not just “it feels smarter.”

### 9. I hit a real environment limit while running the full Stage 2 eval here
- Where: [backend/eval_results/latest_et_eval_results.json](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/eval_results/latest_et_eval_results.json)
- What I changed: I ran the Stage 2 eval pass, but the current coding environment cannot reach MongoDB Atlas because DNS/network access is restricted here.
- Why: The eval runner itself is wired correctly, but the environment blocks the Mongo connection before real retrieval can happen.
- Practical effect in simple English: The `0.0` Stage 2 eval result currently in the local file is not telling us the planner is bad. It is telling us this sandbox could not reach the live database. On your real machine or deployed backend, the Stage 2 eval should be run again for a meaningful score.

### 10. I also fixed the Stage 1 research-pack path issue caused by your new file layout
- Where: [backend/app/chatbot/registry.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/registry.py)
- What I changed: Your Stage 1 research files are now under `backend/STAGE_1/`, but the old registry loader still expected them at the backend root. I added path fallback logic so the app can still find:
  - source allow-list
  - product registry
  - bootstrap chunks
  - eval prompts
- Why: Without this, the old registry-backed RAG path could silently break after the folder reorganization.
- Practical effect in simple English: The earlier ET research base is still usable even after the new Stage 2 pack was added.

## 2026-03-28 - Selective Voice-AI merge and Stage 2 latency optimization

### 1. I merged the useful Voice-AI path without downgrading the main RAG stack
- Where: [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py), [backend/app/chatbot/voice_providers.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/voice_providers.py), [backend/app/chatbot/voice_utils.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/voice_utils.py)
- What I changed: I did not merge the whole `voiceAgent` branch because it would have overwritten the newer Stage 2 planner, docs, and deployment work. Instead, I pulled only the Sarvam speech-to-text and text-to-speech path into the current backend and kept the current concierge graph as the answer source of truth.
- Why: The goal was not to create a separate voice bot. The goal was to make voice another interface for the same ET concierge.
- Practical effect in simple English: When someone speaks to Luna, the voice turn still goes through the same ET product routing, retrieval, recommendations, and session history as a text turn.

### 2. I made the voice answer stay grounded in the same RAG response
- Where: [backend/app/main.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/main.py), [backend/app/chatbot/service.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/service.py)
- What I changed: The `/chat/voice` endpoint now does this sequence:
  - transcribe audio with Sarvam STT
  - call `concierge_service.chat()` with the transcript
  - convert the final ET answer into a shorter voice-safe script
  - synthesize it with Sarvam TTS
- Why: This proves the voice answer is not “just a raw LLM API call.” It is the same grounded ET answer, only spoken.
- Practical effect in simple English: Voice mode now inherits the same vector-backed ET knowledge, product scoring, and response planning that text mode already had.

### 3. I optimized heavy roadmap and comparison queries so they respond faster
- Where: [backend/app/chatbot/agents.py](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/app/chatbot/agents.py)
- What I changed:
  - reduced retrieval breadth for broad, long-form ecosystem questions
  - skipped persona retrieval for broad product-overview asks where it was adding latency without much value
  - trimmed chunk text before sending it to the final model
  - replaced the huge full Stage 2 JSON dump with a compact decision summary
  - replaced the long answer-style policy text with a shorter generation guide
  - shortened the amount of chat history injected for heavy queries
- Why: The backend was still doing too much work for long prompts like roadmap, comparison, and “explain all ET products” asks. The issue was not failure. The issue was oversized prompt payload.
- Practical effect in simple English: Long, structured ET asks should now come back faster without losing the main ET recommendation logic.

### 4. I wired the frontend voice button into the existing thread and session model
- Where: [src/components/search/VoiceChatButton.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/components/search/VoiceChatButton.tsx), [src/app/search/page.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/app/search/page.tsx)
- What I changed: The search page now has a microphone button that:
  - records audio in the browser
  - sends it to `/chat/voice`
  - appends the transcribed user message into the current thread
  - appends the ET concierge answer into the same thread
  - plays the returned spoken audio
- Why: Voice should not create a second hidden conversation model. It should behave like another input method on the same ET thread.
- Practical effect in simple English: A user can now speak to Luna and still keep a normal readable conversation history, citations, and ET recommendations in the same place.

### 5. I updated the docs so the project now explains the real Voice-AI architecture
- Where: [README.md](/home/aryan-s/Documents/GENAI/ET-Concierge/README.md), [src/components/docs/DocsPage.tsx](/home/aryan-s/Documents/GENAI/ET-Concierge/src/components/docs/DocsPage.tsx), [backend/.env.example](/home/aryan-s/Documents/GENAI/ET-Concierge/backend/.env.example)
- What I changed:
  - added the Sarvam voice layer to the README architecture and API docs
  - documented `/chat/voice`
  - added `SARVAM_API_KEY` to the backend env example
  - updated the frontend docs page to explain how voice works on top of the main ET RAG path
- Why: The documentation should match the demo. If voice is now part of the product, it should be represented in both developer docs and user-facing docs.
- Practical effect in simple English: The repo and frontend docs now describe the real current system, including the new voice capability.
