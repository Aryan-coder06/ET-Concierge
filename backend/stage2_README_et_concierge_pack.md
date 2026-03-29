# ET Concierge Stage 2 Upgrade Pack

This pack is for the next major upgrade of LUNA / ET Compass after the first RAG and UI version.

## Main goal
Make the bot feel like a natural, ET-focused concierge:
- answer open-ended natural questions
- remain grounded in ET data
- adapt depth: brief / normal / detailed
- adapt representation: paragraph / bullets / table / roadmap / cards
- keep prose answer, recommendation lane, sidebar state, and widgets synchronized
- avoid defaulting everything to ET Markets
- use HTML/UI blocks only when they improve understanding

## Core architecture changes
1. **Response planner**
   - decides answer depth, structure, and tone before generation
   - supports short / normal / deep answers
   - supports bullets, table, comparison, roadmap, assumptions, and next-step sections

2. **Unified recommendation engine**
   - one decision object drives:
     - prose recommendation
     - sidebar best lane
     - widgets
     - next best action
     - CTA links

3. **Profile-to-product scoring**
   - explicit weighted logic instead of hidden default bias
   - products connected:
     - ET Prime
     - ET Markets
     - ET Portfolio
     - ET Masterclass
     - ET Events / ET Edge / ET Education
     - ET Benefits / partner benefits

4. **UI rendering policy**
   - default to natural text first
   - use HTML or UI cards only when helpful
   - avoid overwhelming the user with decorative components

5. **Evaluation upgrade**
   - measure realism, reasoning depth, formatting obedience, and answer/UI sync

## Recommended runtime flow
User query
-> retrieval
-> profile update
-> response planning
-> product scoring
-> decision object
-> answer generation
-> UI render plan
-> final response

## Files
- `stage2_response_contract.json`:
  output contract for planner + final answer object
- `stage2_product_scoring_policy.json`:
  weighted routing and product recommendation logic
- `stage2_ui_render_contract.json`:
  rules for when to use plain text, bullets, tables, or HTML
- `stage2_answer_style_policy.md`:
  tone + style + natural language behavior
- `stage2_eval_suite.json`:
  prompts and rubrics for testing the upgraded system

## Key principle
The bot should answer naturally first.

That means:
- if the user asks casually, answer casually but well
- if the user wants detail, expand
- if the user wants a table, give a table
- if the user wants a roadmap, give a roadmap
- only show UI modules when they add actual value

## HTML / UI recommendation
Yes, HTML can be used, but only for controlled response blocks:
- comparison tables
- recommendation cards
- profile summary cards
- roadmap / timeline cards
- disclaimer / verification boxes

Do NOT make HTML the only output mode.
The best approach is:
- natural text answer first
- optional structured UI blocks second
- backed by the same recommendation object

## Biggest issue this pack fixes
Currently the natural-language answer and the visual recommendation layer can disagree.

This pack forces them to come from one common decision object.
