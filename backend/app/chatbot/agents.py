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
    build_verification_notes,
    canonical_product_name,
    canonical_sources_for_product,
    get_source_by_url,
    get_source_metadata,
    product_registry_context,
    route_user_intent_to_products,
)
from .retriever_service import get_persona_chunks, get_product_chunks
from .state import AgentState, REQUIRED_PROFILE_FIELDS
from .stage2 import (
    build_stage2_decision,
    load_stage2_answer_style_policy,
    load_stage2_ui_render_contract,
    to_display_product_name,
)


logger = logging.getLogger(__name__)

PRODUCT_LINKS = {
    "ET Prime": "https://economictimes.indiatimes.com/prime/about-us",
    "ET Markets": "https://economictimes.indiatimes.com/markets",
    "ET Portfolio": "https://economictimes.indiatimes.com/portfolio-home",
    "ET Wealth Edition": "https://epaper.indiatimes.com/wealth_edition.cms",
    "ET Print Edition": "https://epaper.indiatimes.com/default.cms?pub=et",
    "ETMasterclass": "https://masterclass.economictimes.indiatimes.com/",
    "ET Events": "https://et-edge.com/",
    "ET Partner Benefits": "https://economictimes.indiatimes.com/et_benefits.cms?from=mdr",
}

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

PRODUCT_ALIASES = {
    "etprime": "ET Prime",
    "et prime": "ET Prime",
    "etmarkets": "ET Markets",
    "et markets": "ET Markets",
    "et portfolio": "ET Portfolio",
    "portfolio": "ET Portfolio",
    "et wealth edition": "ET Wealth Edition",
    "wealth edition": "ET Wealth Edition",
    "et print edition": "ET Print Edition",
    "print edition": "ET Print Edition",
    "epaper": "ET Print Edition",
    "et masterclass": "ETMasterclass",
    "etmasterclass": "ETMasterclass",
    "masterclass": "ETMasterclass",
    "et events": "ET Events",
    "et benefits": "ET Partner Benefits",
    "partner benefits": "ET Partner Benefits",
    "times prime": "ET Partner Benefits",
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
        key = str(value).strip().lower()
        normalized_name = PRODUCT_ALIASES.get(key)
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
    text = message.lower()
    product_keywords = [
        "et prime",
        "etprime",
        "et markets",
        "etmarkets",
        "et portfolio",
        "portfolio",
        "et wealth edition",
        "wealth edition",
        "et print edition",
        "print edition",
        "epaper",
        "et masterclass",
        "etmasterclass",
        "et events",
        "et benefits",
        "times prime",
        "subscription",
        "product",
        "membership",
        "recommend",
        "trial",
        "pricing",
        "benefits",
        "market mood",
        "stock reports plus",
        "stock report plus",
        "track my investments",
        "investment tracking",
        "sip",
        "learning program",
        "executive program",
        "executive learning",
        "industry events",
        "summit",
        "event path",
        "community touchpoints",
        "personal finance",
        "market tools",
        "trading tools",
        "what et path",
        "what path fits",
        "what fits me",
        "where do i start",
        "can et help me",
        "does et have",
        "does et offer",
        "what services do you offer",
        "what services do u offer",
        "what can you do",
        "what can u do",
        "what all do you offer",
        "what all can you do",
        "what all can u do",
        "what et can do for me",
        "what et will be of use to me",
        "what will be of use to me",
        "what should i use",
        "which et service",
        "which et services",
        "help me find",
        "beyond articles",
        "data is uncertain",
        "uncertain",
        "verify the latest",
    ]
    return any(keyword in text for keyword in product_keywords)


def build_visual_hint(
    query: str,
    recommended_products: list[str] | None = None,
    verification_notes: list[str] | None = None,
) -> str | None:
    normalized_query = query.lower()
    recommended_products = recommended_products or []
    verification_notes = verification_notes or []

    if verification_notes or any(
        phrase in normalized_query
        for phrase in [
            "free trial",
            "trial",
            "pricing",
            "price",
            "offer",
            "discount",
            "benefits",
            "activate",
            "redeem",
            "voucher",
            "verify the latest",
            "uncertain",
            "mixed signal",
        ]
    ):
        return "trust_signal"

    if any(
        phrase in normalized_query
        for phrase in [
            "portfolio",
            "track investments",
            "track my investments",
            "holdings",
            "sip",
            "goals",
            "alerts",
            "asset allocation",
        ]
    ):
        return "portfolio_view"

    if any(
        phrase in normalized_query
        for phrase in [
            "market mood",
            "stock reports plus",
            "stock report plus",
            "markets",
            "trading",
            "investing",
            "screeners",
            "watchlist",
            "stock tools",
        ]
    ):
        return "markets_tools"

    if any(
        phrase in normalized_query
        for phrase in [
            "masterclass",
            "learning",
            "course",
            "courses",
            "workshop",
            "skill",
            "learn",
            "leadership",
            "executive education",
        ]
    ):
        return "learning_lane"

    if any(
        phrase in normalized_query
        for phrase in [
            "events",
            "event path",
            "summit",
            "conference",
            "conclave",
            "community",
            "enterprise ai",
            "register",
            "portal",
        ]
    ):
        return "events_network"

    if any(
        phrase in normalized_query
        for phrase in [
            "all products",
            "all et products",
            "what all products",
            "major et products",
            "all services",
            "et ecosystem",
            "tell me all",
            "show all products",
            "beyond articles",
            "what product is right for me",
            "what et product",
            "new to et",
            "where should i start",
            "best place to begin",
            "help me find",
        ]
    ):
        return "ecosystem_map"

    primary_product = recommended_products[0] if recommended_products else None
    if primary_product == "ET Markets":
        return "markets_tools"
    if primary_product == "ET Portfolio":
        return "portfolio_view"
    if primary_product == "ETMasterclass":
        return "learning_lane"
    if primary_product == "ET Events":
        return "events_network"
    if primary_product in {"ET Prime", "ET Wealth Edition", "ET Print Edition"}:
        return "ecosystem_map"
    if primary_product == "ET Partner Benefits":
        return "trust_signal"

    return None


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
- existing_products: array chosen from ET Prime, ET Markets, ET Portfolio, ET Wealth Edition, ET Print Edition, ETMasterclass, ET Events, ET Partner Benefits

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
    if _obvious_product_query(state["current_message"]) or _is_followup_guidance_request(
        state["current_message"], state.get("messages", [])
    ):
        return {**state, "intent": "product_query"}

    if not state["onboarding_complete"]:
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
    starter_query = any(
        phrase in state["current_message"].lower()
        for phrase in [
            "where should i start",
            "new to et",
            "what et product is right for me",
            "best place to begin",
        ]
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
            "navigator_summary": (
                build_navigator_summary(
                    state["profile"],
                    starter_products,
                    state["current_message"],
                    [],
                    onboarding_complete=state["onboarding_complete"],
                )
                if starter_query
                else None
            ),
            "visual_hint": (
                build_visual_hint(state["current_message"], starter_products, [])
                if starter_query
                else None
            ),
            "show_roadmap": False,
        },
    }


def rag_retriever_node(state: AgentState) -> AgentState:
    profile = state["profile"]
    query = state["current_message"]
    normalized_query = query.lower()
    broad_product_query = any(
        phrase in normalized_query
        for phrase in [
            "all products",
            "what all products",
            "all et products",
            "major et products",
            "tell me all",
            "ecosystem",
            "beyond articles",
        ]
    )
    product_k = 8 if broad_product_query else 4
    should_fetch_persona = any(profile.get(field) for field in REQUIRED_PROFILE_FIELDS)

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
    current_lane = stage2_decision.get("decision", {}).get("current_lane")
    requires_live_context = query_analysis.get("requires_live_context", False)

    if query_analysis.get("primary_intent") == "markets":
        return "markets_tools" if requires_live_context else None
    if current_lane == "markets" and requires_live_context:
        return "portfolio_view"
    if query_analysis.get("primary_intent") == "learning":
        return "learning_lane"
    if query_analysis.get("primary_intent") == "events":
        return "events_network"
    if query_analysis.get("primary_intent") == "benefits":
        return "trust_signal"
    if query_analysis.get("primary_intent") in {"discovery", "comparison", "product_explanation"}:
        return "ecosystem_map"
    return None


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

    context_parts: list[str] = []
    for chunk in state["retrieved_chunks"]:
        product = chunk.metadata.get("product_name") or chunk.metadata.get("type", "ET Context")
        section = chunk.metadata.get("category") or chunk.metadata.get("goal") or "General"
        context_parts.append(f"[{product} | {section}]\n{chunk.page_content}")

    rag_context = "\n\n".join(context_parts)
    registry_context = product_registry_context(recommended_products)
    stage2_style_policy = load_stage2_answer_style_policy()
    query_analysis = stage2_decision.get("query_analysis", {})
    decision = stage2_decision.get("decision", {})
    history = []
    for message in state["messages"][-8:]:
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

Stage 2 answer style policy:
{stage2_style_policy}

Stage 2 decision object:
{json.dumps(stage2_decision, indent=2)}

Rules:
- Answer the user's question directly first, then explain why the recommendation fits.
- Keep the answer within the max words from answer_plan unless the user explicitly asked for more.
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
- Prefer ET Prime as a broad ET entry point only when the user wants broad ET access. Prefer ET Markets for market tools, ET Portfolio for tracking holdings/goals, ETMasterclass for learning, ET Events for event discovery, and ET Wealth Edition as a Prime benefit lane.
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
            label = product_name
            href = PRODUCT_LINKS.get(product_name)
        else:
            label = "Persona Journey"
            href = None

        key = f"{label}|{href or ''}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({"label": label, "href": href})

    for product_name in recommended_products or []:
        label = product_name
        href = PRODUCT_LINKS.get(product_name)
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
        for source in canonical_sources_for_product(product_name)[:2]:
            add_citation(source)

    normalized_query = (query or "").lower()

    if "market mood" in normalized_query:
        add_citation(get_source_metadata("market_mood"))

    if "stock reports plus" in normalized_query or "stock report plus" in normalized_query:
        add_citation(get_source_metadata("stock_reports_plus"))

    if "portfolio" in normalized_query or "track my investments" in normalized_query:
        add_citation(get_source_metadata("et_portfolio_home"))
        add_citation(get_source_metadata("et_portfolio_mobile"))

    if any(
        phrase in normalized_query
        for phrase in [
            "what kind of et events",
            "industry events",
            "event path",
            "community touchpoints",
        ]
    ):
        for source_id in [
            "et_b2b_events",
            "enterprise_ai_events",
            "cio_events",
            "bfsi_events",
            "government_events",
        ]:
            add_citation(get_source_metadata(source_id))

    if "enterprise ai" in normalized_query:
        add_citation(get_source_metadata("enterprise_ai_events"))

    if any(keyword in normalized_query for keyword in ["free trial", "trial", "pricing"]):
        add_citation(get_source_metadata("et_prime_trial_paywall"))
        add_citation(get_source_metadata("et_terms"))

    if any(
        phrase in normalized_query
        for phrase in [
            "data is uncertain",
            "if data is uncertain",
            "uncertain data",
            "verify the latest",
            "current public pages",
        ]
    ):
        add_citation(get_source_metadata("et_terms"))
        add_citation(get_source_metadata("et_prime_faq"))

    if "beginner investor" in normalized_query:
        add_citation(get_source_metadata("et_prime_faq"))
        add_citation(get_source_metadata("et_markets_google_play"))

    if "beyond articles" in normalized_query:
        for source_id in [
            "et_prime_faq",
            "et_markets_google_play",
            "et_portfolio_home",
            "et_wealth_edition",
            "et_masterclass_home",
            "et_b2b_events",
            "et_benefits",
        ]:
            add_citation(get_source_metadata(source_id))

    return citations[:12]


def _direct_verified_response(
    query: str,
    recommended_products: list[str],
    verification_notes: list[str],
) -> str | None:
    normalized_query = query.lower()

    if (
        any(keyword in normalized_query for keyword in ["free trial", "trial", "pricing"])
        and "ET Prime" in recommended_products
        and verification_notes
    ):
        return (
            "Public ET pages show mixed signals on ET Prime trials right now. "
            "The FAQ says there is no trial, while other public ET surfaces have shown free-trial language. "
            "Use the latest live ET checkout screen as the final confirmation before treating a trial as available."
        )

    if (
        any(keyword in normalized_query for keyword in ["activate", "redeem", "voucher"])
        and "ET Partner Benefits" in recommended_products
        and verification_notes
    ):
        return (
            "ET partner benefits are available through ET Prime, but some offers have activation constraints. "
            "For example, Times Prime activation is limited to an Indian mobile number, so I would first confirm that eligibility before suggesting the exact benefit to activate."
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
    intent = profile.get("intent")
    profession = profile.get("profession")
    sophistication = profile.get("sophistication")
    normalized_query = query.lower()

    if not onboarding_complete:
        return {
            "title": "Best ET starting point",
            "summary": (
                f"{primary_product} is the best broad lane to start with right now. "
                "I still need one or two quick answers to narrow your ET journey properly."
            ),
            "why_this_path": [
                "It gives the widest useful ET entry point.",
                "It helps us narrow into markets, wealth, learning, or events next.",
            ],
            "next_move": "Answer the next profiling question so I can tighten your ET path.",
        }

    if primary_product == "ET Markets":
        return {
            "title": "Markets Discovery Path",
            "summary": (
                "You look like someone who should start with ET Markets for active discovery, "
                "then use ET Prime for deeper context and ET Portfolio once you begin tracking decisions."
            ),
            "why_this_path": [
                "Best fit for market tools, research discovery, and live signals.",
                "Strong match for investing or trading-oriented questions.",
                (
                    "Good learning bridge for early-stage users."
                    if profession == "student" or sophistication == "beginner"
                    else "Useful when you want faster, tool-led decisions."
                ),
            ],
            "next_move": "Ask me which ET Markets tools fit your exact investing style.",
        }

    if primary_product == "ET Portfolio":
        return {
            "title": "Tracking and Goals Path",
            "summary": (
                "You are moving from discovery into monitoring. "
                "ET Portfolio fits when you want one place for holdings, goals, alerts, and SIP-linked visibility."
            ),
            "why_this_path": [
                "Best fit for tracking instead of only reading or searching.",
                "Useful if your questions are about holdings, SIPs, goals, or alerts.",
                "Pairs naturally with ET Markets discovery.",
            ],
            "next_move": "Ask me how ET Portfolio and ET Markets work together for you.",
        }

    if primary_product == "ETMasterclass":
        return {
            "title": "Learning and Skill-Building Path",
            "summary": (
                "Your current ET lane looks more like structured learning than immediate product usage. "
                "ETMasterclass fits when you want workshops, executive learning, or guided skill development."
            ),
            "why_this_path": [
                "Best fit for learning, courses, and guided upskilling.",
                "Useful for working professionals, students, and business leaders.",
                "Good complement to ET Prime when you want deeper knowledge, not just content.",
            ],
            "next_move": "Ask me which ETMasterclass lane fits your goal best.",
        }

    if primary_product == "ET Events":
        return {
            "title": "Events and Community Path",
            "summary": (
                "You seem better matched to ET's events ecosystem right now. "
                "This lane fits when you want summits, conferences, industry touchpoints, and live discovery."
            ),
            "why_this_path": [
                "Best fit for conferences, portals, and community-driven ET experiences.",
                "Useful for founders, professionals, enterprise users, and policy-focused audiences.",
                "Can also connect with ET Prime virtual invites depending on context.",
            ],
            "next_move": "Ask me which ET event lane fits your industry or goal.",
        }

    if primary_product == "ET Partner Benefits":
        return {
            "title": "Membership Benefits Path",
            "summary": (
                "This query is really about ET Prime value and activation flow. "
                "ET Partner Benefits is the right lane, but activation rules matter."
            ),
            "why_this_path": [
                "Best fit for redeeming or understanding bundled member offers.",
                "Some benefits have eligibility constraints.",
                "Should be handled more carefully than a normal product overview.",
            ],
            "next_move": (
                "Ask me which benefit you want to activate first."
                if not verification_notes
                else verification_notes[0]
            ),
        }

    if primary_product == "ET Wealth Edition":
        return {
            "title": "Wealth Content Path",
            "summary": (
                "This is a wealth-content lane more than a separate standalone product lane. "
                "It works best when paired with ET Prime access."
            ),
            "why_this_path": [
                "Best fit for wealth-focused reading and personal-finance guidance.",
                "Useful if you want mutual fund and stock learning in a weekly edition format.",
                "Usually connected to ET Prime membership value.",
            ],
            "next_move": "Ask me how ET Wealth Edition fits into the wider ET Prime path.",
        }

    if primary_product == "ET Print Edition":
        return {
            "title": "Edition Reading Path",
            "summary": (
                "This lane fits if you prefer the newspaper-style ET reading experience digitally."
            ),
            "why_this_path": [
                "Best fit for edition-style reading, not tool-led discovery.",
                "Useful for users who want ET in digital newspaper form.",
                "Often part of the wider ET Prime value story.",
            ],
            "next_move": "Ask me how ET Print Edition differs from ET Prime and Wealth Edition.",
        }

    return {
        "title": "Broad ET Access Path",
        "summary": (
            "ET Prime is the broadest ET path when you want deeper access across the ecosystem instead of only one narrow tool."
        ),
        "why_this_path": [
            "Best broad starting point for ET product discovery.",
            "Useful when your need is not limited to one specific ET tool.",
            (
                "Good fit for news and context-led exploration."
                if intent == "news"
                else "Good fit when you want wider ET value before narrowing down."
            ),
        ],
        "next_move": (
            "Ask me whether ET Markets, ET Portfolio, ETMasterclass, or ET Events fits you next."
            if "where should i start" in normalized_query or "new to et" in normalized_query
            else "Ask me what the best ET next step is for your exact goal."
        ),
    }


def build_roadmap(profile: dict) -> dict:
    roadmap_rules = {
        ("beginner", "investing"): [
            {
                "step": 1,
                "product": "ET Markets",
                "reason": "Start with market tools, watchlists, and research-oriented discovery.",
                "url": PRODUCT_LINKS["ET Markets"],
            },
            {
                "step": 2,
                "product": "ET Prime",
                "reason": "Layer in deeper context, premium analysis, and broader ET access.",
                "url": PRODUCT_LINKS["ET Prime"],
            },
            {
                "step": 3,
                "product": "ET Portfolio",
                "reason": "Track holdings, goals, and SIP-linked progress in one place.",
                "url": PRODUCT_LINKS["ET Portfolio"],
            },
        ],
        ("intermediate", "investing"): [
            {
                "step": 1,
                "product": "ET Markets",
                "reason": "Track opportunities and understand markets more actively.",
                "url": PRODUCT_LINKS["ET Markets"],
            },
            {
                "step": 2,
                "product": "ET Portfolio",
                "reason": "Connect discovery with portfolio tracking and alerts.",
                "url": PRODUCT_LINKS["ET Portfolio"],
            },
            {
                "step": 3,
                "product": "ET Prime",
                "reason": "Use premium analysis and benefits when you want broader ET coverage.",
                "url": PRODUCT_LINKS["ET Prime"],
            },
        ],
        ("beginner", "news"): [
            {
                "step": 1,
                "product": "ET Prime",
                "reason": "Start with clearer, deeper business context.",
                "url": PRODUCT_LINKS["ET Prime"],
            },
            {
                "step": 2,
                "product": "ET Print Edition",
                "reason": "Use edition-style reading if you prefer the newspaper format digitally.",
                "url": PRODUCT_LINKS["ET Print Edition"],
            },
        ],
        ("expert", "growing_business"): [
            {
                "step": 1,
                "product": "ET Events",
                "reason": "Use ET's event ecosystem for industry access, summits, and community touchpoints.",
                "url": PRODUCT_LINKS["ET Events"],
            },
            {
                "step": 2,
                "product": "ETMasterclass",
                "reason": "Add structured executive learning for leadership, AI, or business skill growth.",
                "url": PRODUCT_LINKS["ETMasterclass"],
            },
        ],
    }

    key = (
        profile.get("sophistication", "beginner"),
        profile.get("intent", "news"),
    )
    steps = roadmap_rules.get(key, roadmap_rules[("beginner", "news")])

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
    if not state["onboarding_complete"]:
        return []

    intent = state["profile"].get("intent")
    if intent == "investing":
        return [
            "What should I use first: ET Prime or ET Markets?",
            "Can ET help me track my portfolio?",
            "Show me a beginner ET path",
        ]
    if intent == "growing_business":
        return [
            "Which ET product fits events and community discovery?",
            "How can ET help with executive learning?",
            "Show me my ET roadmap",
        ]
    return [
        "What is ET Prime?",
        "Which ET product is right for me?",
        "Show me my ET roadmap",
    ]


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
