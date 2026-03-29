import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import get_settings
from .db import get_sessions_collection
from .registry import (
    analyze_query,
    build_verification_notes,
    canonical_product_name,
    canonical_sources_for_product,
    get_source_by_url,
    get_product_registry,
    get_source_metadata,
    official_product_names,
    product_display_name,
    product_primary_link,
    product_registry_context,
    route_user_intent_to_products,
    select_visual_hint,
)
from .retriever_service import get_persona_chunks, get_product_chunks
from .state import AgentState, REQUIRED_PROFILE_FIELDS
from .stage2 import (
    build_stage2_decision,
    load_stage2_ui_render_contract,
    to_display_product_name,
)


logger = logging.getLogger(__name__)

INTENT_ALIASES = {
    "business": "growing_business",
    "business_growth": "growing_business",
}
SOPHISTICATION_ALIASES = {
    "advanced": "expert",
}
GOAL_ALIASES = {
    "learning": "career_growth",
    "trading": "wealth_building",
}
PROFESSION_ALIASES = {
    "salaried": "salaried_employee",
    "employee": "salaried_employee",
    "founder": "startup_founder",
    "business_owner": "sme_owner",
    "trader": "active_trader",
    "executive": "cxo",
}

def _normalize_scalar(value: str | None, aliases: dict[str, str] | None = None) -> str | None:
    if value in (None, "", "null"):
        return None

    normalized = str(value).strip().lower().replace(" ", "_")
    if aliases:
        normalized = aliases.get(normalized, normalized)
    return normalized


def _normalize_name(value: str | None) -> str | None:
    if value in (None, "", "null"):
        return None

    cleaned = re.sub(r"[^A-Za-z .'-]", " ", str(value)).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None

    parts = cleaned.split()
    if len(parts) > 4:
        return None

    blocked = {"hi", "hello", "hola", "brother", "friend", "luna", "et"}
    if cleaned.lower() in blocked:
        return None

    return " ".join(part.capitalize() for part in parts)


def _extract_name_from_message(message: str) -> str | None:
    patterns = [
        r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{0,40})",
        r"\bi am\s+([A-Za-z][A-Za-z .'-]{0,40})",
        r"\bi'm\s+([A-Za-z][A-Za-z .'-]{0,40})",
        r"\bcall me\s+([A-Za-z][A-Za-z .'-]{0,40})",
    ]
    lowered = message.lower()

    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue

        candidate = match.group(1)
        candidate = re.split(
            r"\b(and|but|because|so|nice to meet|targetting|targeting|want|would|looking)\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        normalized = _normalize_name(candidate)
        if normalized:
            return normalized

    return None


def _normalize_products(values: list[str] | None) -> list[str]:
    if not values:
        return []

    normalized: list[str] = []
    for value in values:
        normalized_name = canonical_product_name(str(value).strip())
        if normalized_name and normalized_name not in normalized:
            normalized.append(normalized_name)
    return normalized


def _strip_markdown_formatting(text: str) -> str:
    cleaned = text.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _is_followup_guidance_request(message: str, messages: list[dict[str, str]]) -> bool:
    normalized = message.strip().lower()
    if normalized not in {
        "then tell",
        "tell me",
        "go on",
        "continue",
        "okay tell me",
        "retry",
        "then?",
    }:
        return False

    for previous in reversed(messages):
        if previous.get("role") != "assistant":
            continue
        return "i have enough context to guide you now" in previous.get("content", "").lower()

    return False


def _field_description(field: str) -> str:
    descriptions = {
        "intent": "whether they are here for investing, business news, or growing a business",
        "sophistication": "their current experience level",
        "goal": "their main goal right now",
        "profession": "what best describes their current role",
    }
    return descriptions.get(field, field)


def _looks_like_heavy_structured_query(
    message: str,
    query_analysis: dict[str, Any] | None = None,
) -> bool:
    normalized = message.lower()
    if query_analysis:
        if query_analysis.get("requires_roadmap") or query_analysis.get("requires_table"):
            return True
        if query_analysis.get("depth_mode") == "deep":
            return True

    heavy_phrases = [
        "2 month",
        "2-month",
        "week by week",
        "week-by-week",
        "roadmap",
        "timeline",
        "compare",
        "comparison",
        "all products",
        "all et products",
        "interrelated products",
        "interrelated",
        "detailed",
        "elaborate",
        "in detail",
        "full ecosystem",
    ]
    return len(message.split()) >= 18 or any(phrase in normalized for phrase in heavy_phrases)


def _truncate_for_prompt(text: str, max_chars: int) -> str:
    flattened = re.sub(r"\s+", " ", text).strip()
    if len(flattened) <= max_chars:
        return flattened
    trimmed = flattened[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{trimmed}..."


def _build_generation_context(retrieved_chunks: list[Any], *, heavy_query: bool) -> str:
    unique_chunks: list[Any] = []
    seen_keys: set[str] = set()

    for chunk in retrieved_chunks:
        metadata = getattr(chunk, "metadata", {}) or {}
        key = "|".join(
            [
                str(metadata.get("source_id") or ""),
                str(metadata.get("product_name") or ""),
                str(metadata.get("category") or metadata.get("goal") or ""),
            ]
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_chunks.append(chunk)

    max_chunks = 3 if heavy_query else 4
    max_chars = 360 if heavy_query else 560
    context_parts: list[str] = []

    for chunk in unique_chunks[:max_chunks]:
        metadata = getattr(chunk, "metadata", {}) or {}
        product = metadata.get("product_name") or metadata.get("type", "ET Context")
        section = metadata.get("category") or metadata.get("goal") or "General"
        excerpt = _truncate_for_prompt(getattr(chunk, "page_content", ""), max_chars)
        context_parts.append(f"[{product} | {section}] {excerpt}")

    return "\n".join(context_parts)


def _build_compact_decision_summary(stage2_decision: dict[str, Any]) -> str:
    query_analysis = stage2_decision.get("query_analysis", {})
    decision = stage2_decision.get("decision", {})
    primary = decision.get("primary_recommendation", {})
    secondary = decision.get("secondary_recommendations", [])[:2]
    next_action = decision.get("next_best_action") or {}

    compact_payload = {
        "query_analysis": {
            "primary_intent": query_analysis.get("primary_intent"),
            "depth_mode": query_analysis.get("depth_mode"),
            "tone_mode": query_analysis.get("tone_mode"),
            "requires_live_context": query_analysis.get("requires_live_context"),
            "requires_table": query_analysis.get("requires_table"),
            "requires_bullets": query_analysis.get("requires_bullets"),
            "requires_roadmap": query_analysis.get("requires_roadmap"),
        },
        "primary_recommendation": {
            "product": primary.get("product"),
            "display_product": primary.get("display_product"),
            "why": primary.get("why", [])[:3],
            "confidence": primary.get("confidence"),
        },
        "secondary_recommendations": [
            {
                "product": item.get("product"),
                "display_product": item.get("display_product"),
                "why": item.get("why", [])[:2],
            }
            for item in secondary
        ],
        "current_lane": decision.get("current_lane"),
        "next_best_action": {
            "label": next_action.get("label"),
            "reason": next_action.get("reason"),
        },
        "comparison_rows": stage2_decision.get("comparison_rows", [])[:4],
        "bullet_groups": stage2_decision.get("bullet_groups", [])[:2],
    }

    return json.dumps(compact_payload, ensure_ascii=True, separators=(",", ":"))


def _build_answer_generation_guidance(
    query_analysis: dict[str, Any],
    answer_plan: dict[str, Any],
) -> str:
    sections = ", ".join(answer_plan.get("sections", []))
    max_words = answer_plan.get("max_words", 180)
    format_rules = query_analysis.get("format_rules", [])
    anti_bias_rules = query_analysis.get("anti_bias_rules", [])
    return "\n".join(
        [
            f"- Primary intent: {query_analysis.get('primary_intent', 'discovery')}.",
            f"- Tone: {query_analysis.get('tone_mode', 'friendly_professional')}.",
            f"- Depth: {query_analysis.get('depth_mode', 'standard')}.",
            f"- Target structure: {sections or 'direct_answer, why_this_fits'}.",
            f"- Hard target length: about {max_words} words unless the user clearly asked for more depth.",
            "- Answer the user directly first, then explain the ET fit.",
            "- If bullet_groups or comparison_rows are already provided, do not repeat them fully in prose.",
            "- Stay grounded in ET facts. If context is thin, be honest and guide the user cleanly.",
            f"- Format rules from policy: {' | '.join(format_rules) if format_rules else 'No additional format rules.'}",
            f"- Anti-bias reminders from policy: {' | '.join(anti_bias_rules) if anti_bias_rules else 'No additional anti-bias reminders.'}",
        ]
    )


def _reply_has_bullets(text: str) -> bool:
    return any(marker in text for marker in ["\n- ", "\n* ", "\n1. ", "\n2. "])


def _render_bullet_groups(bullet_groups: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for group in bullet_groups:
        title = str(group.get("title") or "").strip()
        items = [str(item).strip() for item in group.get("items", []) if str(item).strip()]
        if not items:
            continue
        if title:
            blocks.append(f"{title}:")
        blocks.extend(f"- {item}" for item in items[:4])
    return "\n".join(blocks).strip()


def _enforce_requested_format(
    reply: str,
    *,
    query_analysis: dict[str, Any],
    bullet_groups: list[dict[str, Any]],
) -> str:
    if query_analysis.get("requires_bullets") and bullet_groups and not _reply_has_bullets(reply):
        bullets = _render_bullet_groups(bullet_groups)
        if bullets:
            return f"{reply}\n\n{bullets}".strip()
    return reply


def _has_explicit_profile_signal(message: str) -> bool:
    normalized = message.lower()
    markers = [
        "i am",
        "i'm",
        "my goal",
        "i want",
        "i would like",
        "i would love",
        "looking to",
        "student",
        "founder",
        "employee",
        "retired",
        "trader",
        "professional",
        "beginner",
        "intermediate",
        "advanced",
    ]
    return any(marker in normalized for marker in markers)


@lru_cache(maxsize=None)
def _llm_for_model(model_name: str) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.google_api_key,
        temperature=0.25,
    )


def _invoke_llm(messages: list[SystemMessage | HumanMessage | AIMessage]):
    settings = get_settings()
    settings.require_external_services()

    last_error: Exception | None = None
    for candidate in settings.chat_model_candidates:
        try:
            return _llm_for_model(candidate).invoke(messages)
        except Exception as exc:  # pragma: no cover - external service fallback
            last_error = exc
            logger.warning("Gemini invocation failed for %s: %s", candidate, exc)

    raise RuntimeError(
        "No configured Google chat model succeeded. Set GOOGLE_CHAT_MODEL in backend/.env."
    ) from last_error


def _response_text(response) -> str:
    content = response.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(str(text))
            elif block:
                parts.append(str(block))
        return "\n".join(parts).strip()
    return str(content).strip()


def _parse_json_payload(text: str) -> dict:
    cleaned = (
        text.replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
    return {}


def _profile_complete(profile: dict) -> bool:
    return all(profile.get(field) for field in REQUIRED_PROFILE_FIELDS)


def _obvious_product_query(message: str) -> bool:
    analysis = analyze_query(message, user_profile={}, journey_history=[])
    return analysis.get("query_mode") in {"concierge_mode", "information_mode", "news_mode"}


def build_visual_hint(
    query: str,
    recommended_products: list[str] | None = None,
    verification_notes: list[str] | None = None,
) -> str | None:
    return select_visual_hint(
        query,
        recommended_products or [],
        verification_notes=verification_notes or [],
    )


def profile_extractor_node(state: AgentState) -> AgentState:
    if _obvious_product_query(state["current_message"]) and not _has_explicit_profile_signal(
        state["current_message"]
    ):
        return state

    extraction_prompt = f"""
You extract user profile signals from one message.

Current profile:
{json.dumps(state["profile"], indent=2)}

User message:
"{state["current_message"]}"

Return JSON only. Use only these exact enums when clearly inferable:
- name: user's first name or preferred name if they explicitly mention it, otherwise null
- intent: investing | news | growing_business | null
- sophistication: beginner | intermediate | expert | null
- goal: wealth_building | saving_specific | protecting_wealth | career_growth | professional_authority | business_scaling | null
- profession: salaried_employee | startup_founder | sme_owner | active_trader | corporate_professional | cxo | marketing_head | policy_maker | student | retired | null
- interests: array of short strings
- existing_products: array chosen from {", ".join(official_product_names())}

Never guess. Only include fields with new evidence.
"""

    extracted: dict = {}
    try:
        extracted = _parse_json_payload(
            _response_text(_invoke_llm([HumanMessage(content=extraction_prompt)]))
        )
    except Exception as exc:
        logger.warning("Profile extraction failed: %s", exc)

    profile = dict(state["profile"])
    extracted_name = _normalize_name(extracted.get("name")) or _extract_name_from_message(
        state["current_message"]
    )
    if extracted_name:
        profile["name"] = extracted_name

    scalar_updates = {
        "intent": _normalize_scalar(extracted.get("intent"), INTENT_ALIASES),
        "sophistication": _normalize_scalar(
            extracted.get("sophistication"), SOPHISTICATION_ALIASES
        ),
        "goal": _normalize_scalar(extracted.get("goal"), GOAL_ALIASES),
        "profession": _normalize_scalar(
            extracted.get("profession"), PROFESSION_ALIASES
        ),
        "age_range": _normalize_scalar(extracted.get("age_range")),
    }

    for key, value in scalar_updates.items():
        if value:
            profile[key] = value

    interests = [
        str(item).strip().lower().replace(" ", "_")
        for item in extracted.get("interests", [])
        if str(item).strip()
    ]
    if interests:
        profile["interests"] = sorted(set(profile.get("interests", []) + interests))

    existing_products = _normalize_products(extracted.get("existing_products"))
    if existing_products:
        profile["existing_products"] = sorted(
            set(profile.get("existing_products", []) + existing_products)
        )

    onboarding_complete = _profile_complete(profile)
    return {**state, "profile": profile, "onboarding_complete": onboarding_complete}


def router_node(state: AgentState) -> AgentState:
    analysis = analyze_query(
        state["current_message"],
        user_profile=state["profile"],
        journey_history=state.get("journey_history", []),
    )

    if _is_followup_guidance_request(
        state["current_message"], state.get("messages", [])
    ):
        return {**state, "intent": "product_query"}

    if analysis.get("query_mode") in {"information_mode", "news_mode"}:
        return {**state, "intent": "product_query"}

    if analysis.get("query_mode") == "concierge_mode" and not state["onboarding_complete"]:
        return {**state, "intent": "profiling"}

    if analysis.get("query_mode") == "concierge_mode":
        return {**state, "intent": "product_query"}

    if analysis.get("query_mode") == "chitchat" and not state["onboarding_complete"]:
        return {**state, "intent": "profiling"}

    routing_prompt = f"""
Classify the following message into exactly one category.

Message: "{state["current_message"]}"

Categories:
- product_query: asking about ET products, subscriptions, features, fit, pricing, recommendations, journeys
- chitchat: greetings, thanks, casual conversation

Return JSON only in this shape:
{{"intent": "product_query" | "chitchat"}}
"""

    try:
        result = _parse_json_payload(
            _response_text(_invoke_llm([HumanMessage(content=routing_prompt)]))
        )
        intent = result.get("intent", "chitchat")
    except Exception as exc:
        logger.warning("Router failed, defaulting to chitchat: %s", exc)
        intent = "chitchat"

    if intent not in {"product_query", "chitchat"}:
        intent = "chitchat"

    return {**state, "intent": intent}


def _generate_profile_followup_message(
    state: AgentState,
    *,
    missing_field: str,
    fallback_prompt: str,
    starter_products: list[str],
    starter_query: bool,
) -> str:
    history_lines: list[str] = []
    for item in state.get("messages", [])[-4:]:
        role = "Assistant" if item.get("role") == "assistant" else "User"
        history_lines.append(f"{role}: {item.get('content', '').strip()}")

    starter_hint = ""
    if starter_query and starter_products:
        starter_hint = (
            f"If it helps, you may briefly mention that {starter_products[0]} is a broad ET "
            "starting point, but do not turn this into a full recommendation yet."
        )

    prompt = f"""
You are LUNA for ET. You are in the profiling stage of an ET concierge conversation.

Current profile:
{json.dumps(state["profile"], indent=2)}

Recent conversation:
{chr(10).join(history_lines) if history_lines else "No recent conversation."}

Latest user message:
"{state["current_message"]}"

The one missing field you still need is: {missing_field}
That field means: {_field_description(missing_field)}

Write one short, natural assistant reply.

Rules:
- First, briefly respond to the user's latest message if it was a greeting, meta question, or personal introduction.
- If the profile already includes the user's name, you may use it naturally.
- End by asking exactly one question that helps collect the missing field.
- Keep it to 1 or 2 sentences.
- No markdown, no bullets, no JSON, no labels.
- Do not sound like a form or repeat robotic phrasing.
- {starter_hint if starter_hint else "Do not over-explain ET products yet."}
"""

    try:
        return _strip_markdown_formatting(
            _response_text(_invoke_llm([HumanMessage(content=prompt)]))
        )
    except Exception as exc:
        logger.warning("Conversational profiler prompt failed: %s", exc)
        profile_name = state["profile"].get("name")
        if profile_name:
            return f"{profile_name}, one quick thing before I guide you properly: {fallback_prompt[0].lower() + fallback_prompt[1:]}"
        return fallback_prompt


def profiler_node(state: AgentState) -> AgentState:
    question_flow = {
        "intent": "What brings you to ET today: investing, staying sharp on business news, or growing a business?",
        "sophistication": "How experienced are you right now: beginner, intermediate, or fairly advanced?",
        "goal": "What is your main goal at the moment: wealth building, saving for something specific, protecting wealth, career growth, professional authority, or business scaling?",
        "profession": "What best describes you right now: salaried employee, founder, SME owner, trader, corporate professional, CXO, policy maker, student, or retired?",
    }

    asked = list(state.get("questions_asked", []))
    next_field = None
    next_prompt = None
    for field, prompt in question_flow.items():
        if not state["profile"].get(field):
            next_field = field
            next_prompt = prompt
            if field not in asked:
                asked.append(field)
            break

    starter_products = route_user_intent_to_products(
        state["current_message"],
        state["profile"],
        state.get("journey_history", []),
    )
    starter_query = analyze_query(
        state["current_message"],
        user_profile=state["profile"],
        journey_history=state.get("journey_history", []),
    ).get("query_mode") == "concierge_mode"

    navigator_summary = (
        build_navigator_summary(
            state["profile"],
            starter_products,
            state["current_message"],
            [],
            onboarding_complete=state["onboarding_complete"],
        )
        if starter_query
        else None
    )
    path_snapshot = build_path_snapshot(
        query=state["current_message"],
        response_type="profiling",
        recommended_products=starter_products if starter_query else [],
        decision=None,
        navigator_summary=navigator_summary,
        profile=state["profile"],
        chips=[],
    )

    if next_prompt:
        message = _generate_profile_followup_message(
            state,
            missing_field=next_field or "intent",
            fallback_prompt=next_prompt,
            starter_products=starter_products,
            starter_query=starter_query,
        )
    else:
        message = (
            "I have enough context to guide you now. Ask me what ET product, pathway, or starting point fits you best."
        )

    return {
        **state,
        "retrieved_chunks": [],
        "questions_asked": asked,
        "response": {
            "type": "profiling",
            "message": message,
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": starter_products if starter_query else [],
            "recommended_products": starter_products if starter_query else [],
            "source_citations": _build_source_citations(
                [],
                starter_products,
                query=state["current_message"],
            )
            if starter_query
            else [],
            "verification_notes": [],
            "navigator_summary": navigator_summary,
            "visual_hint": (
                build_visual_hint(state["current_message"], starter_products, [])
                if starter_query
                else None
            ),
            "path_snapshot": path_snapshot,
            "show_roadmap": False,
        },
    }


def rag_retriever_node(state: AgentState) -> AgentState:
    profile = state["profile"]
    query = state["current_message"]
    analysis = analyze_query(
        query,
        user_profile=profile,
        journey_history=state.get("journey_history", []),
    )
    heavy_structured_query = _looks_like_heavy_structured_query(query)
    broad_product_query = bool(analysis.get("broad_overview"))
    if broad_product_query:
        product_k = 5 if heavy_structured_query else 6
    elif heavy_structured_query:
        product_k = 3
    else:
        product_k = 4

    should_fetch_persona = (
        analysis.get("query_mode") == "concierge_mode"
        and any(profile.get(field) for field in REQUIRED_PROFILE_FIELDS)
        and not broad_product_query
    )

    product_chunks = get_product_chunks(query=query, profile=profile, k=product_k)
    persona_chunks = (
        get_persona_chunks(query=query, profile=profile, k=1)
        if should_fetch_persona
        else []
    )
    all_chunks = product_chunks + persona_chunks

    return {**state, "retrieved_chunks": all_chunks}


def chitchat_node(state: AgentState) -> AgentState:
    return {
        **state,
        "retrieved_chunks": [],
        "response": {
            "type": "chitchat",
            "message": "",
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": [],
            "show_roadmap": False,
        },
    }


def planner_node(state: AgentState) -> AgentState:
    if state.get("response", {}).get("type") == "profiling":
        return {**state, "stage2_decision": None}

    recommended_products = route_user_intent_to_products(
        state["current_message"],
        state["profile"],
        state.get("journey_history", []),
    )
    verification_notes = build_verification_notes(
        state["current_message"],
        recommended_products,
    )
    source_citations = _build_source_citations(
        state["retrieved_chunks"],
        recommended_products,
        query=state["current_message"],
    )
    decision = build_stage2_decision(
        query=state["current_message"],
        profile=state["profile"],
        journey_history=state.get("journey_history", []),
        source_citations=source_citations,
        verification_notes=verification_notes,
        retrieved_chunks=state["retrieved_chunks"],
    )
    return {**state, "stage2_decision": decision}


def _stage2_primary_and_secondary_products(stage2_decision: dict[str, Any]) -> list[str]:
    decision = stage2_decision.get("decision", {})
    primary = decision.get("primary_recommendation", {}).get("product")
    products: list[str] = []

    if primary == "Mixed Path":
        for item in decision.get("secondary_recommendations", [])[:2]:
            product_name = canonical_product_name(item.get("product"))
            if product_name and product_name not in products:
                products.append(product_name)
    else:
        primary_name = canonical_product_name(primary)
        if primary_name:
            products.append(primary_name)

    for item in decision.get("secondary_recommendations", [])[:2]:
        product_name = canonical_product_name(item.get("product"))
        if product_name and product_name not in products:
            products.append(product_name)

    return products


def _stage2_visual_hint(stage2_decision: dict[str, Any]) -> str | None:
    query_analysis = stage2_decision.get("query_analysis", {})
    decision = stage2_decision.get("decision", {})
    primary = (decision.get("primary_recommendation") or {}).get("product")
    verification_notes = stage2_decision.get("retrieval_state", {}).get("conflicts_detected", [])
    query = query_analysis.get("normalized_query") or ""
    return select_visual_hint(
        query,
        [primary] if primary and primary != "Mixed Path" else [],
        verification_notes=verification_notes,
    )


def _stage2_presentation(stage2_decision: dict[str, Any]) -> dict[str, Any]:
    query_analysis = stage2_decision.get("query_analysis", {})
    ui_policy = load_stage2_ui_render_contract()
    concise = query_analysis.get("depth_mode") == "brief"
    has_comparison = bool(stage2_decision.get("comparison_rows"))
    has_bullets = bool(stage2_decision.get("bullet_groups"))
    visual_hint = _stage2_visual_hint(stage2_decision)

    module_count = 0
    if visual_hint:
        module_count += 1
    if has_comparison:
        module_count += 1
    if has_bullets:
        module_count += 1
    if stage2_decision.get("decision", {}).get("next_best_action"):
        module_count += 1

    if concise and module_count > 2:
        visual_hint = None

    return {
        "answer_style": query_analysis.get("depth_mode", "standard"),
        "show_visual_panel": bool(visual_hint),
        "show_recommended_products": True,
        "show_navigator_summary": not concise,
        "show_roadmap": bool(query_analysis.get("requires_roadmap")),
        "show_chips": not concise,
        "show_bullet_groups": has_bullets,
        "show_comparison_table": has_comparison,
        "module_policy": ui_policy.get("default_policy", []),
    }


def _build_markdown_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    header = "| Product | Best For | Why |\n|---|---|---|"
    body = "\n".join(
        f"| {row['item']} | {row['best_for']} | {row['why']} |" for row in rows
    )
    return f"{header}\n{body}"


def response_generator_node(state: AgentState) -> AgentState:
    if state.get("response", {}).get("type") == "profiling":
        return state

    stage2_decision = state.get("stage2_decision") or build_stage2_decision(
        query=state["current_message"],
        profile=state["profile"],
        journey_history=state.get("journey_history", []),
        source_citations=[],
        verification_notes=[],
        retrieved_chunks=state["retrieved_chunks"],
    )
    recommended_products = _stage2_primary_and_secondary_products(stage2_decision)
    verification_notes = build_verification_notes(
        state["current_message"],
        recommended_products,
    )
    source_citations = _build_source_citations(
        state["retrieved_chunks"],
        recommended_products,
        query=state["current_message"],
    )
    direct_response = _direct_verified_response(
        state["current_message"],
        recommended_products,
        verification_notes,
    )
    navigator_summary = build_navigator_summary(
        state["profile"],
        recommended_products,
        state["current_message"],
        verification_notes,
        onboarding_complete=state["onboarding_complete"],
    )
    visual_hint = _stage2_visual_hint(stage2_decision) or build_visual_hint(
        state["current_message"],
        recommended_products,
        verification_notes,
    )
    presentation = _stage2_presentation(stage2_decision)
    comparison_rows = stage2_decision.get("comparison_rows", [])
    bullet_groups = stage2_decision.get("bullet_groups", [])
    ui_modules = stage2_decision.get("ui_modules", [])
    query_analysis = stage2_decision.get("query_analysis", {})
    decision = stage2_decision.get("decision", {})
    answer_plan = stage2_decision.get("answer_plan", {})
    chips = get_chips(state)
    path_snapshot = build_path_snapshot(
        query=state["current_message"],
        response_type=state["intent"],
        recommended_products=recommended_products,
        decision=decision,
        navigator_summary=navigator_summary,
        profile=state["profile"],
        chips=chips,
    )
    heavy_query = _looks_like_heavy_structured_query(
        state["current_message"],
        query_analysis=query_analysis,
    )
    rag_context = _build_generation_context(
        state["retrieved_chunks"],
        heavy_query=heavy_query,
    )
    registry_context = product_registry_context(
        recommended_products[:2] if heavy_query else recommended_products[:3]
    )
    compact_decision = _build_compact_decision_summary(stage2_decision)
    answer_guidance = _build_answer_generation_guidance(query_analysis, answer_plan)
    history = []
    for message in state["messages"][-(4 if heavy_query else 6) :]:
        if message.get("role") == "assistant":
            history.append(AIMessage(content=message.get("content", "")))
        else:
            history.append(HumanMessage(content=message.get("content", "")))

    system_message = SystemMessage(
        content=f"""
You are LUNA for ET, a grounded conversational concierge for The Economic Times ecosystem.

User profile:
{json.dumps(state["profile"], indent=2)}

Recommended ET products:
{json.dumps(recommended_products, indent=2)}

Structured ET registry facts:
{registry_context if registry_context else "No structured registry facts were available for this turn."}

Retrieved ET context:
{rag_context if rag_context else "No retrieved ET context was available for this turn."}

Verification notes:
{json.dumps(verification_notes, indent=2) if verification_notes else "No special verification note for this turn."}

Answer guidance:
{answer_guidance}

Compact decision object:
{compact_decision}

Rules:
- Answer the user's question directly first, then explain why the recommendation fits.
- Keep the answer within the max words from the answer guidance unless the user explicitly asked for more.
- Use the requested format naturally. If comparison_rows or bullet_groups are present, you may briefly introduce them instead of repeating them in prose.
- Use the retrieved ET context and structured registry facts when available and do not invent product features.
- Return markdown-safe text only. No HTML and no code formatting.
- Do not mention discounts, prices, offers, or claims unless they are explicitly present in the ET context or verification notes.
- Make sure the primary recommendation in prose matches the primary recommendation in the decision object.
- If the user asks for an overview of ET products, give a clean working list from the retrieved context and make it clear you are summarizing the main options you found.
- If the message is chitchat, answer naturally and mention that you can guide users across ET products and journeys.
- If context is weak, be honest and give the best available direction.
- If verification notes mention mixed public signals, explicitly say public ET pages show mixed signals and tell the user to verify the latest live ET page or checkout.
- If verification notes mention an activation or eligibility constraint, ask one short follow-up before promising activation.
- Follow the decision object and retrieved ET context. Do not swap in a broader ET fallback unless the decision object itself supports it.
"""
    )

    if direct_response:
        reply = direct_response
    else:
        reply = _strip_markdown_formatting(
            _response_text(
                _invoke_llm(
                    [system_message, *history, HumanMessage(content=state["current_message"])]
                )
            )
        )

    reply = _enforce_requested_format(
        reply,
        query_analysis=query_analysis,
        bullet_groups=bullet_groups,
    )

    if comparison_rows and query_analysis.get("requires_table"):
        table_intro = (
            "Here is the simplest ET comparison for your question:\n\n"
            if query_analysis.get("depth_mode") != "brief"
            else ""
        )
        table_markdown = _build_markdown_table(comparison_rows)
        recommendation_tail = ""
        primary_display = decision.get("primary_recommendation", {}).get("display_product") or to_display_product_name(
            recommended_products[0] if recommended_products else None
        )
        why_items = decision.get("primary_recommendation", {}).get("why", [])
        if primary_display:
            recommendation_tail = (
                f"\n\nRecommendation: {primary_display} is the best first step here"
                + (f" because {why_items[0]}." if why_items else ".")
            )
        reply = f"{reply}\n\n{table_intro}{table_markdown}{recommendation_tail}".strip()

    return {
        **state,
        "response": {
            "type": state["intent"],
            "message": reply,
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": recommended_products,
            "recommended_products": recommended_products,
            "verification_notes": verification_notes,
            "source_citations": source_citations,
            "navigator_summary": navigator_summary,
            "visual_hint": visual_hint,
            "answer_style": query_analysis.get("depth_mode", "standard"),
            "presentation": presentation,
            "decision": decision,
            "comparison_rows": comparison_rows,
            "bullet_groups": bullet_groups,
            "ui_modules": ui_modules,
            "path_snapshot": path_snapshot,
            "html_snippets": stage2_decision.get("html_snippets", []),
            "show_roadmap": False,
        },
    }


def _build_sources(
    retrieved_chunks: list,
    recommended_products: list[str] | None = None,
) -> list[dict[str, str | None]]:
    sources: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for chunk in retrieved_chunks:
        product_name = canonical_product_name(chunk.metadata.get("product_name")) or chunk.metadata.get(
            "product_name"
        )
        if product_name:
            label = product_display_name(product_name) or product_name
            href = product_primary_link(product_name)
        else:
            label = "Persona Journey"
            href = None

        key = f"{label}|{href or ''}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({"label": label, "href": href})

    for product_name in recommended_products or []:
        label = product_display_name(product_name) or product_name
        href = product_primary_link(product_name)
        key = f"{label}|{href or ''}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({"label": label, "href": href})

    return sources


def _build_source_citations(
    retrieved_chunks: list,
    recommended_products: list[str],
    query: str | None = None,
) -> list[dict[str, str | None]]:
    citations: list[dict[str, str | None]] = []
    seen: set[str] = set()

    def add_citation(source: dict | None) -> None:
        if not source:
            return
        key = f"{source.get('source_id', '')}|{source.get('url', '')}"
        if key in seen:
            return
        seen.add(key)
        citations.append(
            {
                "label": source.get("title") or source.get("source_id") or "ET Source",
                "href": source.get("url"),
                "source_id": source.get("source_id"),
                "verification_status": source.get("verification_status"),
                "page_type": source.get("page_type"),
            }
        )

    for chunk in retrieved_chunks:
        add_citation(get_source_metadata(chunk.metadata.get("source_id")))
        add_citation(get_source_by_url(chunk.metadata.get("source_url")))
        for url in chunk.metadata.get("source_urls", []) or []:
            add_citation(get_source_by_url(url))

    for product_name in recommended_products:
        for source in canonical_sources_for_product(product_name)[:3]:
            add_citation(source)

    return citations[:12]


def _direct_verified_response(
    query: str,
    recommended_products: list[str],
    verification_notes: list[str],
) -> str | None:
    normalized_query = query.lower()

    if any(keyword in normalized_query for keyword in ["free trial", "trial", "pricing", "price", "offer"]) and verification_notes:
        return (
            "Public ET pages can show mixed or fast-changing pricing signals for this detail. "
            "Use the latest live ET page or checkout flow as the final confirmation before treating a pricing or trial detail as final."
        )

    if any(keyword in normalized_query for keyword in ["activate", "redeem", "voucher", "benefit"]) and verification_notes:
        return (
            "Some ET benefit flows can have activation or eligibility constraints. "
            "I would confirm the exact live ET page before suggesting a final activation step."
        )

    if any(
        phrase in normalized_query
        for phrase in ["data is uncertain", "if data is uncertain", "uncertain data"]
    ):
        return (
            "If ET data is uncertain, I should say the answer is based on current public ET pages, "
            "call out any mixed public signals clearly, and ask the user to verify the latest live ET page, FAQ, checkout, or terms page before acting on it."
        )

    return None


def build_navigator_summary(
    profile: dict,
    recommended_products: list[str],
    query: str,
    verification_notes: list[str],
    *,
    onboarding_complete: bool,
) -> dict[str, object] | None:
    if not recommended_products:
        return None

    primary_product = recommended_products[0]
    product = get_product_registry(primary_product)
    display_name = product_display_name(primary_product) or primary_product
    lane = product.get("lane") if product else None
    best_for = list(product.get("best_for", [])[:3]) if product else []
    key_features = list(product.get("key_features", [])[:3]) if product else []
    summary = product.get("summary") if product else None

    if not onboarding_complete:
        return {
            "title": "Best ET starting point",
            "summary": (
                f"{display_name} is the strongest lane from the current query, but I still need a little profile context to personalize it properly."
            ),
            "why_this_path": [
                summary or f"{display_name} is a relevant ET starting point for this question.",
                f"Lane: {str(lane).replace('_', ' ')}" if lane else "Luna will refine the lane after one or two more signals.",
            ],
            "next_move": "Answer the next profiling question so I can tighten your ET path.",
        }

    why_this_path = []
    if summary:
        why_this_path.append(summary)
    if best_for:
        why_this_path.append(f"Best for: {', '.join(best_for)}.")
    if key_features:
        why_this_path.append(f"Useful strengths: {', '.join(key_features)}.")
    if verification_notes:
        why_this_path.append(verification_notes[0])

    next_product = recommended_products[1] if len(recommended_products) > 1 else None
    if next_product:
        next_move = f"Ask me how {display_name} compares with {product_display_name(next_product) or next_product} for your exact goal."
    else:
        next_move = f"Ask me how to use {display_name} for your exact goal."

    return {
        "title": f"{display_name} Path",
        "summary": summary or f"Luna is currently steering this conversation toward {display_name}.",
        "why_this_path": why_this_path[:3] or [f"{display_name} is the current best ET fit."],
        "next_move": next_move,
    }


def _node_accent_for_product(product_name: str | None) -> str:
    if not product_name:
        return "black"

    normalized = product_name.lower()
    if "market" in normalized or "portfolio" in normalized:
        return "blue"
    if "masterclass" in normalized or "event" in normalized or "benefit" in normalized:
        return "yellow"
    if "prime" in normalized or "print" in normalized or "wealth" in normalized:
        return "red"
    return "black"


def build_path_snapshot(
    *,
    query: str,
    response_type: str,
    recommended_products: list[str],
    decision: dict[str, Any] | None,
    navigator_summary: dict[str, Any] | None,
    profile: dict[str, Any],
    chips: list[str],
) -> dict[str, Any] | None:
    if not (recommended_products or decision or navigator_summary):
        return None

    decision = decision or {}
    primary_recommendation = decision.get("primary_recommendation", {}) if isinstance(decision, dict) else {}
    primary_product = primary_recommendation.get("product") or (recommended_products[0] if recommended_products else None)
    primary_display = primary_recommendation.get("display_product") or primary_product
    secondary_products = [
        canonical_product_name(item.get("product")) or item.get("product")
        for item in decision.get("secondary_recommendations", [])[:2]
        if isinstance(item, dict) and item.get("product")
    ]
    secondary_products = [product for product in secondary_products if product]

    next_action = None
    if isinstance(decision.get("next_best_action"), dict):
        next_action = decision["next_best_action"].get("label") or decision["next_best_action"].get("reason")
    if not next_action and navigator_summary:
        next_action = navigator_summary.get("next_move")
    if not next_action and chips:
        next_action = chips[0]

    user_goal = profile.get("goal") or profile.get("intent") or "ET discovery"
    nodes: list[dict[str, Any]] = [
        {
            "id": "goal",
            "label": str(user_goal).replace("_", " ").title(),
            "detail": "User goal",
            "accent": "red",
        },
        {
            "id": "route",
            "label": str(response_type).replace("_", " ").title(),
            "detail": "Active route",
            "accent": "black",
        },
    ]

    if primary_display:
        nodes.append(
            {
                "id": "primary",
                "label": str(primary_display),
                "detail": "Primary ET lane",
                "accent": _node_accent_for_product(primary_product),
            }
        )

    for index, product_name in enumerate(secondary_products, start=1):
        nodes.append(
            {
                "id": f"secondary-{index}",
                "label": str(product_display_name(product_name) or product_name),
                "detail": "Support lane",
                "accent": _node_accent_for_product(product_name),
            }
        )

    if next_action:
        nodes.append(
            {
                "id": "action",
                "label": str(next_action)[:54],
                "detail": "Next move",
                "accent": "yellow",
            }
        )

    summary = navigator_summary.get("summary") if navigator_summary else None
    if not summary and primary_display:
        summary = f"Luna is currently steering this conversation toward {primary_display}."

    return {
        "query": query,
        "route": response_type,
        "primary_product": primary_product,
        "primary_display_product": primary_display,
        "secondary_products": secondary_products,
        "signals": list(decision.get("signals", [])[:4]) if isinstance(decision, dict) else [],
        "next_action": next_action,
        "summary": summary,
        "nodes": nodes,
    }


def build_roadmap(profile: dict) -> dict:
    profile_seed = " ".join(
        str(value).replace("_", " ")
        for value in [
            profile.get("intent"),
            profile.get("goal"),
            profile.get("profession"),
            profile.get("sophistication"),
        ]
        if value
    ).strip() or "broad ET discovery"
    recommended = route_user_intent_to_products(
        f"Build an ET roadmap for {profile_seed}",
        profile,
        [],
    )[:3]

    steps = []
    for index, product_name in enumerate(recommended, start=1):
        product = get_product_registry(product_name)
        if not product:
            continue
        steps.append(
            {
                "step": index,
                "product": product_display_name(product_name) or product_name,
                "reason": product.get("summary") or ", ".join(product.get("key_features", [])[:2]) or "Recommended ET lane.",
                "url": product_primary_link(product_name),
            }
        )

    return {
        "title": "Your personalized ET journey",
        "profile_summary": [
            value
            for value in [
                profile.get("intent"),
                profile.get("sophistication"),
                profile.get("profession"),
            ]
            if value
        ],
        "steps": steps,
    }


def get_chips(state: AgentState) -> list[str]:
    query = state.get("current_message", "")
    analysis = analyze_query(
        query,
        user_profile=state["profile"],
        journey_history=state.get("journey_history", []),
    )
    recommended = route_user_intent_to_products(
        query or "show me my ET path",
        state["profile"],
        state.get("journey_history", []),
        analysis=analysis,
    )[:3]

    chips: list[str] = []
    for product_name in recommended[:2]:
        display_name = product_display_name(product_name) or product_name
        chips.append(f"What is {display_name}?")
    if len(recommended) >= 2:
        chips.append(
            f"Compare {product_display_name(recommended[0]) or recommended[0]} and {product_display_name(recommended[1]) or recommended[1]}"
        )
    elif recommended:
        chips.append(f"Build me a roadmap using {product_display_name(recommended[0]) or recommended[0]}")
    if not chips:
        chips.append("Show me my ET roadmap")
    return chips[:3]


def output_formatter_node(state: AgentState) -> AgentState:
    profile = state["profile"]
    response = state["response"]
    presentation = response.get("presentation") or {}
    show_roadmap = (
        presentation.get("show_roadmap")
        if "show_roadmap" in presentation
        else (
            state["onboarding_complete"]
            and response.get("type") in {"product_query", "profiling"}
            and len(state["messages"]) < 12
        )
    )

    structured_response = {
        "session_id": state["session_id"],
        "message": response["message"],
        "profile_update": {
            "name": profile.get("name"),
            "intent": profile.get("intent"),
            "sophistication": profile.get("sophistication"),
            "goal": profile.get("goal"),
            "profession": profile.get("profession"),
            "interests": profile.get("interests", []),
            "onboarding_complete": state["onboarding_complete"],
        },
        "recommendations": response.get("recommendations", []),
        "recommended_products": response.get(
            "recommended_products",
            response.get("recommendations", []),
        ),
        "navigator_summary": response.get("navigator_summary"),
        "roadmap": build_roadmap(profile) if show_roadmap else None,
        "chips": get_chips(state),
        "response_type": response.get("type", "product_query"),
        "sources": _build_sources(
            state["retrieved_chunks"],
            response.get("recommended_products", response.get("recommendations", [])),
        ),
        "source_citations": response.get("source_citations", []),
        "verification_notes": response.get("verification_notes", []),
        "visual_hint": response.get("visual_hint"),
        "answer_style": response.get("answer_style"),
        "presentation": presentation,
        "decision": response.get("decision"),
        "comparison_rows": response.get("comparison_rows", []),
        "bullet_groups": response.get("bullet_groups", []),
        "ui_modules": response.get("ui_modules", []),
        "path_snapshot": response.get("path_snapshot"),
        "html_snippets": response.get("html_snippets", []),
    }

    return {**state, "response": structured_response}


def state_updater_node(state: AgentState) -> AgentState:
    session_title = next(
        (
            message.get("content", "").strip()
            for message in state.get("messages", [])
            if message.get("role") == "user" and message.get("content")
        ),
        state["current_message"].strip(),
    )
    session_title = session_title[:80] or state["session_id"]
    journey_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": state["response"].get("response_type", state["intent"]),
        "user_message": state["current_message"],
        "assistant_message": state["response"]["message"],
        "recommendations": list(state["response"].get("recommendations", [])),
        "recommended_products": list(
            state["response"].get(
                "recommended_products",
                state["response"].get("recommendations", []),
            )
        ),
        "sources": list(state["response"].get("sources", [])),
        "source_citations": list(state["response"].get("source_citations", [])),
        "verification_notes": list(state["response"].get("verification_notes", [])),
        "navigator_summary": state["response"].get("navigator_summary"),
        "roadmap": state["response"].get("roadmap"),
        "chips": list(state["response"].get("chips", [])),
        "visual_hint": state["response"].get("visual_hint"),
        "answer_style": state["response"].get("answer_style"),
        "presentation": state["response"].get("presentation"),
        "decision": state["response"].get("decision"),
        "comparison_rows": list(state["response"].get("comparison_rows", [])),
        "bullet_groups": list(state["response"].get("bullet_groups", [])),
        "ui_modules": list(state["response"].get("ui_modules", [])),
        "path_snapshot": state["response"].get("path_snapshot"),
        "profile_snapshot": {
            "name": state["profile"].get("name"),
            "intent": state["profile"].get("intent"),
            "sophistication": state["profile"].get("sophistication"),
            "goal": state["profile"].get("goal"),
            "profession": state["profile"].get("profession"),
            "interests": list(state["profile"].get("interests", [])),
            "existing_products": list(state["profile"].get("existing_products", [])),
            "age_range": state["profile"].get("age_range"),
        },
    }
    updated_messages = (
        state["messages"]
        + [{"role": "user", "content": state["current_message"]}]
        + [{"role": "assistant", "content": state["response"]["message"]}]
    )[-30:]
    updated_journey_history = (state.get("journey_history", []) + [journey_event])[-50:]

    get_sessions_collection().update_one(
        {"session_id": state["session_id"]},
        {
            "$set": {
                "session_id": state["session_id"],
                "title": session_title,
                "profile": state["profile"],
                "onboarding_complete": state["onboarding_complete"],
                "questions_asked": state.get("questions_asked", []),
                "messages": updated_messages,
                "journey_history": updated_journey_history,
                "recommendations": state["response"].get("recommendations", []),
                "recommended_products": state["response"].get(
                    "recommended_products",
                    state["response"].get("recommendations", []),
                ),
                "response_type": state["response"].get("response_type"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )

    return {
        **state,
        "messages": updated_messages,
        "journey_history": updated_journey_history,
    }
