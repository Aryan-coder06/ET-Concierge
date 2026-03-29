# Codex Stage 2 Upgrade Prompt for ET Compass / LUNA

You are upgrading an existing ET-focused RAG assistant into a more natural, adaptive, synchronized concierge.

## Current problems to fix
1. The prose answer and UI recommendation layer can disagree.
2. The system often defaults to ET Markets even when the user's preference points elsewhere.
3. Formatting instructions like bullets, tables, short answer + recommendation are inconsistently followed.
4. The bot sometimes asks clarifying questions too early instead of answering naturally first.
5. Live market widgets appear even when the current user intent is learning or broad discovery.

## Main goal
Make LUNA feel like a natural ET concierge:
- answer natural questions naturally
- stay grounded in ET data
- adapt answer depth and format
- synchronize prose answer, recommendation cards, sidebar, and widgets
- connect ET products intelligently rather than through fixed routes

## Use these files
- stage2_response_contract.json
- stage2_product_scoring_policy.json
- stage2_ui_render_contract.json
- stage2_answer_style_policy.md
- stage2_eval_suite.json

## Implementation requirements

### 1. Add a response planner
Before final generation, build a planner that decides:
- primary intent
- secondary intents
- depth mode (brief / standard / deep)
- tone mode
- whether bullets / table / roadmap are required
- whether live context is required
- whether a verification box is required

The planner must ensure every part of a multi-part prompt is answered.

### 2. Add a unified decision object
Build one structured decision object that contains:
- profile state
- retrieval state
- product scores
- primary recommendation
- secondary recommendations
- current lane
- next best action
- answer plan
- UI module plan

This object must be the single source of truth for:
- prose answer
- recommendation panel
- sidebar
- live context module
- next best action card

### 3. Replace default-routing bias with explicit scoring
Use stage2_product_scoring_policy.json to compute product scores from:
- user profile
- remembered preferences
- explicit prompt wording
- intent classification
- time / noise / beginner signals

Do not default to ET Markets unless the signals strongly support it.

### 4. Improve natural answer behavior
The assistant should:
- answer directly first
- ask follow-up questions only when helpful
- avoid stiff concierge phrasing
- feel friendly and professional
- support beginner-friendly, executive, and premium-concierge tone variants

### 5. Add format-aware rendering
If the user asks for:
- bullets -> return bullets
- table -> return a real table
- roadmap -> return a roadmap
- concise answer -> keep it short
- deep answer -> expand with useful structure

### 6. Add UI rendering logic
Support three output layers:
1. natural markdown answer
2. structured JSON for UI modules
3. optional sanitized HTML snippets for special cards/tables if the frontend uses them

Do not make HTML the only output mode.
Prefer structured JSON for frontend rendering.

### 7. Add intent-sensitive widgets
- markets query -> market snapshot / market context
- learning query -> learning card / masterclass card
- events query -> event card
- broad discovery query -> ET overview + best starting point
- simple factual query -> minimal widgets

### 8. Add answer/UI synchronization tests
Add automated tests or offline eval checks that fail if:
- prose primary recommendation != UI primary recommendation
- current lane != visible sidebar lane
- market widget is shown on a learning-first response
- requested format is ignored

### 9. Add model orchestration if helpful
If the codebase supports multiple LLM calls, separate:
- planner / router step
- final answer generation step

The planner can be shorter and deterministic.
The answer generation step can be more expressive.

### 10. Preserve current strengths
Keep:
- grounded ET retrieval
- conflict-aware answers
- source-aware caution
- good citation / verification behavior

## Suggested internal pipeline
User input
-> retrieval
-> memory/profile update
-> planner
-> product scoring
-> unified decision object
-> answer generator
-> UI module generator
-> final response payload

## Suggested output payload
{
  "plain_answer_markdown": "...",
  "decision": {...},
  "ui_modules": [...],
  "html_snippets": [...],
  "sources": [...]
}

## Practical frontend behavior
- show plain answer first
- then show recommendation or profile card
- then show comparison / roadmap / live context only if relevant
- never overwhelm the answer with decorative modules

## Success criteria
The upgraded assistant should:
- sound natural
- answer in the requested format
- give better ET recommendations
- connect ET products coherently
- avoid contradictory UI
- feel more like a real concierge than a themed chatbot