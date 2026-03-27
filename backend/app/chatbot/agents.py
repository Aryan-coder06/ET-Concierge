import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import get_settings
from .db import get_sessions_collection
from .registry import (
    build_verification_notes,
    canonical_product_name,
    canonical_sources_for_product,
    get_product_registry,
    get_source_by_url,
    get_source_metadata,
    official_product_names,
    product_registry_context,
    route_user_intent_to_products,
)
from .retriever_service import get_persona_chunks, get_product_chunks
from .state import AgentState, REQUIRED_PROFILE_FIELDS


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
    "et edge": "ET Events",
    "et edge events": "ET Events",
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


def _is_latest_news_request(message: str) -> bool:
    normalized = message.lower()
    if "news" not in normalized and "headline" not in normalized:
        return False

    live_terms = [
        "latest",
        "breaking",
        "today",
        "current",
        "headline",
        "headlines",
        "top 10",
        "top ten",
        "top news",
        "news in india",
        "india news",
    ]
    ask_terms = ["give me", "show me", "tell me", "provide", "what are", "what is"]
    et_guided_terms = [
        "using et",
        "with et",
        "through et",
        "on et",
        "et product",
        "et products",
        "et app",
        "et prime",
        "et markets",
        "et print edition",
    ]

    return (
        any(term in normalized for term in live_terms)
        and any(term in normalized for term in ask_terms)
        and not any(term in normalized for term in et_guided_terms)
    )


def _detect_answer_style(query: str) -> str:
    normalized = query.lower()

    if _is_latest_news_request(query):
        return "brief"

    if any(
        phrase in normalized
        for phrase in [
            "roadmap",
            "plan",
            "step by step",
            "5 day",
            "5-day",
            "7 day",
            "7-day",
            "day 1",
            "utilise",
            "utilize",
            "how to use et",
        ]
    ):
        return "roadmap"

    if any(
        phrase in normalized
        for phrase in [
            "all products",
            "all et products",
            "what are all the products",
            "what all products",
            "tell me all products",
            "list all products",
            "which products are you aware of",
            "ecosystem",
        ]
    ):
        return "overview"

    if any(
        phrase in normalized
        for phrase in [
            "difference between",
            "compare",
            "vs",
            "versus",
        ]
    ):
        return "compare"

    if any(
        phrase in normalized
        for phrase in [
            "in detail",
            "detailed",
            "elaborate",
            "deep dive",
            "explain properly",
        ]
    ):
        return "detailed"

    return "standard"


def _is_all_products_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        phrase in normalized
        for phrase in [
            "all products",
            "all et products",
            "what are all the products",
            "what all products",
            "tell me all products",
            "list all products",
            "which products are you aware of",
            "what are all the products you are aware of",
            "what all can you do",
            "show the et ecosystem",
        ]
    )


def _starter_path_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        phrase in normalized
        for phrase in [
            "what product is right for me",
            "what et product",
            "which et product",
            "which product fits",
            "where should i start",
            "best place to begin",
            "new to et",
            "what et path",
            "what fits me",
        ]
    )


def _build_news_redirect_sources() -> tuple[list[dict[str, str | None]], list[dict[str, str | None]]]:
    sources = [
        {
            "label": "Economic Times",
            "href": "https://economictimes.indiatimes.com/",
        },
        {
            "label": "ET Markets",
            "href": PRODUCT_LINKS["ET Markets"],
        },
        {
            "label": "ET Mobile Applications",
            "href": "https://economictimes.indiatimes.com/mobile",
        },
    ]
    citations = [
        {
            "label": "ET Markets: Stock Tools & News – Google Play",
            "href": "https://play.google.com/store/apps/details?hl=en_IN&id=com.et.market",
            "source_id": "et_markets_google_play",
            "verification_status": "official_public",
            "page_type": "app_store_listing",
        },
        {
            "label": "ET Mobile Applications",
            "href": "https://economictimes.indiatimes.com/mobile",
            "source_id": "mobile_apps_portal",
            "verification_status": "official_public",
            "page_type": "mobile_apps_portal",
        },
    ]
    return sources, citations


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
        "et edge",
        "et edge events",
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
            "screeners",
            "watchlist",
            "stock tools",
            "markets tools",
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
        ]
    ):
        return "ecosystem_map"

    primary_product = recommended_products[0] if recommended_products else None
    if primary_product == "ET Portfolio":
        return "portfolio_view"
    if primary_product == "ETMasterclass":
        return "learning_lane"
    if primary_product == "ET Events":
        return "events_network"
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
    if _is_latest_news_request(state["current_message"]):
        return {**state, "intent": "news_query"}

    if _obvious_product_query(state["current_message"]):
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


def profiler_node(state: AgentState) -> AgentState:
    question_flow = {
        "intent": "What brings you to ET today: investing, staying sharp on business news, or growing a business?",
        "sophistication": "How experienced are you right now: beginner, intermediate, or fairly advanced?",
        "goal": "What is your main goal at the moment: wealth building, saving for something specific, protecting wealth, career growth, professional authority, or business scaling?",
        "profession": "What best describes you right now: salaried employee, founder, SME owner, trader, corporate professional, CXO, policy maker, student, or retired?",
    }

    asked = list(state.get("questions_asked", []))
    next_prompt = None
    for field, prompt in question_flow.items():
        if not state["profile"].get(field) and field not in asked:
            next_prompt = prompt
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
        if starter_query and starter_products:
            message = (
                f"{starter_products[0]} is the broadest ET starting point if you want overall ET access. "
                f"To guide you properly from there, {next_prompt[0].lower() + next_prompt[1:]}"
            )
        else:
            message = next_prompt
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


def news_query_node(state: AgentState) -> AgentState:
    sources, citations = _build_news_redirect_sources()
    return {
        **state,
        "retrieved_chunks": [],
        "response": {
            "type": "news_query",
            "message": (
                "I cannot reliably give you live latest India headlines yet because this version of LUNA is "
                "built around the ET product ecosystem, not a live news feed. For current headlines, open the "
                "Economic Times homepage or ET Markets right now. If you want, I can still help you build a "
                "strong ET news-following setup after that."
            ),
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": [],
            "recommended_products": [],
            "verification_notes": [],
            "source_citations": citations,
            "sources": sources,
            "navigator_summary": None,
            "visual_hint": None,
            "show_roadmap": False,
        },
    }


def response_generator_node(state: AgentState) -> AgentState:
    if state.get("response", {}).get("type") == "profiling":
        return state

    answer_style = _detect_answer_style(state["current_message"])
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
    visual_hint = build_visual_hint(
        state["current_message"],
        recommended_products,
        verification_notes,
    )

    context_parts: list[str] = []
    for chunk in state["retrieved_chunks"]:
        product = chunk.metadata.get("product_name") or chunk.metadata.get("type", "ET Context")
        section = chunk.metadata.get("category") or chunk.metadata.get("goal") or "General"
        context_parts.append(f"[{product} | {section}]\n{chunk.page_content}")

    rag_context = "\n\n".join(context_parts)
    registry_context = product_registry_context(recommended_products)
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

Answer style for this turn:
{answer_style}

Rules:
- Be concise and useful. Shape the answer exactly for the requested style.
- If you recommend a product, explain why it fits this user.
- Use the retrieved ET context and structured registry facts when available and do not invent product features.
- Return plain text only. Do not use markdown, asterisks, bold markers, or code formatting.
- Do not mention discounts, prices, offers, or claims unless they are explicitly present in the ET context or verification notes.
- If the user asks for an overview of ET products, give a clean working list from the retrieved context and make it clear you are summarizing the main options you found.
- If the message is chitchat, answer naturally and mention that you can guide users across ET products and journeys.
- If context is weak, be honest and give the best available direction.
- If verification notes mention mixed public signals, explicitly say public ET pages show mixed signals and tell the user to verify the latest live ET page or checkout.
- If verification notes mention an activation or eligibility constraint, ask one short follow-up before promising activation.
- Prefer ET Prime as a broad ET entry point only when the user wants broad ET access. Prefer ET Markets for market tools, ET Portfolio for tracking holdings/goals, ETMasterclass for learning, ET Events for event discovery, and ET Wealth Edition as a Prime benefit lane.
- {_answer_style_rules(answer_style)}
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

    presentation = _build_presentation_hints(
        query=state["current_message"],
        response_type=state["intent"],
        answer_style=answer_style,
        onboarding_complete=state["onboarding_complete"],
        recommended_products=recommended_products,
        navigator_summary=navigator_summary,
        visual_hint=visual_hint,
    )

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
            "answer_style": answer_style,
            "presentation": presentation,
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

    if _is_all_products_query(query):
        lines: list[str] = [
            "Here is the main ET product set I am aware of right now:"
        ]
        for product_name in official_product_names():
            product = get_product_registry(product_name) or {}
            summary = str(product.get("summary", "")).strip()
            short_summary = summary.split(".")[0].strip() if summary else ""
            if short_summary:
                lines.append(f"- {product_name}: {short_summary}.")
            else:
                lines.append(f"- {product_name}")
        lines.append(
            "If you want, I can next group these into news, markets, tracking, learning, events, and partner-benefit lanes."
        )
        return "\n".join(lines)

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


def _answer_style_rules(answer_style: str) -> str:
    if answer_style == "brief":
        return (
            "Use 2 to 3 short sentences. Do not add extra product lanes, side explanations, or long follow-ups unless the user asked for them."
        )
    if answer_style == "roadmap":
        return (
            "Return a day-wise or step-wise roadmap in plain text. Use short numbered lines such as Day 1, Day 2, Step 3. Keep each line practical and specific."
        )
    if answer_style == "overview":
        return (
            "Return a clean product overview in plain text. List the main ET products one by one, and give one short purpose line for each."
        )
    if answer_style == "compare":
        return (
            "Return a compact comparison. Name each option clearly and explain the difference in one short line per option."
        )
    if answer_style == "detailed":
        return (
            "Return a fuller explanation with multiple short paragraphs or numbered points. Stay grounded in ET context and avoid fluff."
        )
    return (
        "Use a balanced answer: short opening, direct answer, then one or two practical next steps only if they help."
    )


def _build_presentation_hints(
    *,
    query: str,
    response_type: str,
    answer_style: str,
    onboarding_complete: bool,
    recommended_products: list[str],
    navigator_summary: dict[str, object] | None,
    visual_hint: str | None,
) -> dict[str, object]:
    normalized_query = query.lower()
    show_visual_panel = visual_hint in {"markets_tools", "portfolio_view", "trust_signal"}
    show_recommended_products = bool(recommended_products)
    show_navigator_summary = navigator_summary is not None
    show_roadmap = "et roadmap" in normalized_query or "show me my roadmap" in normalized_query
    show_chips = onboarding_complete and response_type == "product_query"

    if response_type in {"news_query", "chitchat"}:
        return {
            "answer_style": answer_style,
            "show_visual_panel": False,
            "show_recommended_products": False,
            "show_navigator_summary": False,
            "show_roadmap": False,
            "show_chips": False,
        }

    if answer_style in {"brief", "overview", "roadmap", "compare"}:
        show_visual_panel = False

    if answer_style in {"overview", "roadmap", "compare"}:
        show_recommended_products = False

    if answer_style in {"brief", "overview", "roadmap", "compare", "detailed"}:
        show_navigator_summary = False

    if answer_style != "roadmap":
        show_roadmap = False

    if answer_style in {"overview", "roadmap", "compare", "detailed"}:
        show_chips = False

    if not _starter_path_query(query):
        show_navigator_summary = False

    return {
        "answer_style": answer_style,
        "show_visual_panel": show_visual_panel,
        "show_recommended_products": show_recommended_products,
        "show_navigator_summary": show_navigator_summary,
        "show_roadmap": show_roadmap,
        "show_chips": show_chips,
    }


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
    wants_path_guidance = _starter_path_query(query) or any(
        phrase in normalized_query
        for phrase in [
            "trial",
            "pricing",
            "benefits",
            "activate",
            "redeem",
            "voucher",
        ]
    )

    if not wants_path_guidance:
        return None

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
    answer_style = response.get("answer_style") or _detect_answer_style(state["current_message"])
    presentation = response.get("presentation") or _build_presentation_hints(
        query=state["current_message"],
        response_type=response.get("type", "product_query"),
        answer_style=answer_style,
        onboarding_complete=state["onboarding_complete"],
        recommended_products=response.get(
            "recommended_products",
            response.get("recommendations", []),
        ),
        navigator_summary=response.get("navigator_summary"),
        visual_hint=response.get("visual_hint"),
    )
    show_roadmap = (
        state["onboarding_complete"]
        and response.get("type") in {"product_query", "profiling"}
        and bool(presentation.get("show_roadmap"))
        and len(state["messages"]) < 12
    )
    recommended_products = response.get(
        "recommended_products",
        response.get("recommendations", []),
    )
    if not presentation.get("show_recommended_products"):
        recommended_products = []
    navigator_summary = (
        response.get("navigator_summary")
        if presentation.get("show_navigator_summary")
        else None
    )
    visual_hint = response.get("visual_hint") if presentation.get("show_visual_panel") else None
    chips = get_chips(state) if presentation.get("show_chips") else []
    sources = response.get("sources")
    if not sources:
        sources = _build_sources(
            state["retrieved_chunks"],
            response.get("recommended_products", response.get("recommendations", [])),
        )

    structured_response = {
        "session_id": state["session_id"],
        "message": response["message"],
        "profile_update": {
            "intent": profile.get("intent"),
            "sophistication": profile.get("sophistication"),
            "goal": profile.get("goal"),
            "profession": profile.get("profession"),
            "interests": profile.get("interests", []),
            "onboarding_complete": state["onboarding_complete"],
        },
        "recommendations": response.get("recommendations", []),
        "recommended_products": recommended_products,
        "navigator_summary": navigator_summary,
        "roadmap": build_roadmap(profile) if show_roadmap else None,
        "chips": chips,
        "response_type": response.get("type", "product_query"),
        "sources": sources,
        "source_citations": response.get("source_citations", []),
        "verification_notes": response.get("verification_notes", []),
        "visual_hint": visual_hint,
        "answer_style": answer_style,
        "presentation": presentation,
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
        "profile_snapshot": {
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
