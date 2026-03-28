import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .registry import (
    canonical_product_name,
    detect_products_in_text,
    get_product_registry,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
STAGE2_RESPONSE_CONTRACT_PATH = BACKEND_ROOT / "stage2_response_contract.json"
STAGE2_SCORING_POLICY_PATH = BACKEND_ROOT / "stage2_product_scoring_policy.json"
STAGE2_UI_RENDER_CONTRACT_PATH = BACKEND_ROOT / "stage2_ui_render_contract.json"
STAGE2_ANSWER_STYLE_POLICY_PATH = BACKEND_ROOT / "stage2_answer_style_policy.md"
STAGE2_EVAL_SUITE_PATH = BACKEND_ROOT / "stage2_eval_suite.json"

INTERNAL_PRODUCT_NAME_MAP = {
    "ET Masterclass": "ETMasterclass",
    "ET Benefits": "ET Partner Benefits",
}

DISPLAY_PRODUCT_NAME_MAP = {
    "ETMasterclass": "ET Masterclass",
    "ET Partner Benefits": "ET Benefits",
}

LANE_MAP = {
    "ET Prime": "premium_insights",
    "ET Markets": "markets",
    "ET Portfolio": "markets",
    "ETMasterclass": "learning",
    "ET Events": "events",
    "ET Partner Benefits": "benefits",
    "ET Wealth Edition": "discovery",
    "ET Print Edition": "discovery",
    "Mixed Path": "discovery",
}

DEFAULT_MODULE_PRIORITIES = {
    "recommendation_card": 1,
    "comparison_table": 2,
    "live_context": 2,
    "profile_card": 3,
    "verification_box": 4,
    "next_action": 5,
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_stage2_response_contract() -> dict[str, Any]:
    return _load_json(STAGE2_RESPONSE_CONTRACT_PATH)


@lru_cache(maxsize=1)
def load_stage2_scoring_policy() -> dict[str, Any]:
    return _load_json(STAGE2_SCORING_POLICY_PATH)


@lru_cache(maxsize=1)
def load_stage2_ui_render_contract() -> dict[str, Any]:
    return _load_json(STAGE2_UI_RENDER_CONTRACT_PATH)


@lru_cache(maxsize=1)
def load_stage2_eval_suite() -> dict[str, Any]:
    return _load_json(STAGE2_EVAL_SUITE_PATH)


@lru_cache(maxsize=1)
def load_stage2_answer_style_policy() -> str:
    return STAGE2_ANSWER_STYLE_POLICY_PATH.read_text(encoding="utf-8")


def to_internal_product_name(product_name: str | None) -> str | None:
    if not product_name:
        return None
    mapped = INTERNAL_PRODUCT_NAME_MAP.get(product_name, product_name)
    return canonical_product_name(mapped) or mapped


def to_display_product_name(product_name: str | None) -> str | None:
    if not product_name:
        return None
    return DISPLAY_PRODUCT_NAME_MAP.get(product_name, product_name)


def _normalized_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.lower()).strip()


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _detect_user_type(profile: dict, query: str) -> str:
    normalized = _normalized_query(query)
    profession = profile.get("profession")
    if profession == "student":
        return "student"
    if profession in {"salaried_employee", "corporate_professional", "cxo"}:
        return "working_professional"
    if profession == "active_trader":
        return "active_market_user"
    if profession == "startup_founder":
        return "working_professional"
    if _contains_any(normalized, ["student", "college", "beginner investor", "first time"]):
        return "student"
    if _contains_any(normalized, ["trader", "markets daily", "watchlist", "screeners"]):
        return "active_market_user"
    if _contains_any(normalized, ["new to et", "totally new", "beginner", "start with"]):
        return "beginner_investor"
    if _contains_any(normalized, ["explore", "overwhelming", "where do i begin", "which et product"]):
        return "explorer"
    return "unknown"


def build_query_analysis(query: str, profile: dict) -> dict[str, Any]:
    normalized = _normalized_query(query)
    explicit_products = detect_products_in_text(query)
    secondary_intents: list[str] = []

    if _contains_any(normalized, ["compare", " vs ", "difference between", "or should i use"]):
        primary_intent = "comparison"
        secondary_intents.extend(explicit_products[:2])
    elif _contains_any(normalized, ["roadmap", "7-day", "5-day", "journey", "plan", "timeline"]):
        primary_intent = "roadmap"
    elif _contains_any(normalized, ["event", "events", "summit", "conference", "conclave", "community"]):
        primary_intent = "events"
    elif _contains_any(normalized, ["benefit", "benefits", "times prime", "redeem", "activate", "voucher"]):
        primary_intent = "benefits"
    elif _contains_any(normalized, ["market", "markets", "sensex", "nifty", "trading", "portfolio", "screeners", "watchlist", "market mood"]):
        primary_intent = "markets"
    elif _contains_any(normalized, ["learn", "learning", "masterclass", "course", "student", "education"]):
        primary_intent = "learning"
    elif _contains_any(normalized, ["show my profile", "my profile", "update my path", "sidebar show"]):
        primary_intent = "profile_update"
    elif _contains_any(normalized, ["what is", "tell me about", "explain", "how does", "services do you offer", "what can you do"]):
        primary_intent = "product_explanation"
    elif _contains_any(normalized, ["trial", "price", "pricing", "offer", "for sure", "verify", "confirm"]):
        primary_intent = "support"
    else:
        primary_intent = "discovery"

    if _contains_any(normalized, ["compare", "table"]):
        secondary_intents.append("comparison")
    if _contains_any(normalized, ["bullet", "bullets", "three bullets", "points"]):
        secondary_intents.append("bullets")
    if _contains_any(normalized, ["roadmap", "plan", "journey"]):
        secondary_intents.append("roadmap")
    if _contains_any(normalized, ["live", "today", "snapshot", "sensex", "nifty"]):
        secondary_intents.append("live_context")

    requires_table = _contains_any(normalized, ["table", "compare", "comparison", "vs"])
    requires_bullets = _contains_any(normalized, ["bullet", "bullets", "points", "three bullets"])
    requires_roadmap = _contains_any(normalized, ["roadmap", "7-day", "5-day", "plan", "journey"])
    requires_live_context = primary_intent == "markets" and _contains_any(
        normalized, ["live", "snapshot", "sensex", "nifty", "today", "market mood", "tracker"]
    )

    if _contains_any(normalized, ["short answer", "brief", "concise", "in short", "just tell me quickly"]):
        depth_mode = "brief"
    elif requires_roadmap or requires_table or _contains_any(normalized, ["detailed", "in detail", "deep", "elaborate"]):
        depth_mode = "deep"
    else:
        depth_mode = "standard"

    if _contains_any(normalized, ["executive", "concise but professional", "cxo"]):
        tone_mode = "executive"
    elif profile.get("profession") == "student" or profile.get("sophistication") == "beginner":
        tone_mode = "beginner_guide"
    elif _contains_any(normalized, ["premium", "concierge"]):
        tone_mode = "concierge"
    else:
        tone_mode = "friendly_professional"

    return {
        "primary_intent": primary_intent,
        "secondary_intents": list(dict.fromkeys(secondary_intents)),
        "requires_live_context": requires_live_context,
        "requires_table": requires_table,
        "requires_bullets": requires_bullets,
        "requires_roadmap": requires_roadmap,
        "depth_mode": depth_mode,
        "tone_mode": tone_mode,
        "explicit_products": explicit_products,
    }


def build_profile_state(profile: dict, query: str) -> dict[str, Any]:
    normalized = _normalized_query(query)
    preferences: list[str] = []
    constraints: list[str] = []

    if _contains_any(normalized, ["learn", "learning", "student", "beginner", "guide", "guided"]):
        preferences.append("guided_learning")
    if _contains_any(normalized, ["markets", "trading", "sensex", "nifty", "market mood", "screeners", "watchlist"]):
        preferences.append("markets_tools")
    if _contains_any(normalized, ["prime", "premium", "deeper context", "less noise", "overwhelming"]):
        preferences.append("premium_insights")
    if _contains_any(normalized, ["event", "conference", "summit", "community", "network"]):
        preferences.append("events")
    if _contains_any(normalized, ["less overwhelming", "less noise", "low noise"]):
        preferences.append("low_noise")
    if _contains_any(normalized, ["15 minutes", "short time", "quickly", "time limited"]):
        preferences.append("short_time")

    if profile.get("sophistication") == "beginner" or _contains_any(normalized, ["beginner", "new to et", "totally new"]):
        constraints.append("beginner_friendly")
    if _contains_any(normalized, ["15 minutes", "short time", "time limited"]):
        constraints.append("time_limited")
    if _contains_any(normalized, ["not sure", "uncertain", "confused", "overwhelming"]):
        constraints.append("low_confidence")

    return {
        "user_type": _detect_user_type(profile, query),
        "experience_level": profile.get("sophistication") or "unknown",
        "goal": profile.get("goal") or "",
        "preferences": list(dict.fromkeys(preferences)),
        "constraints": list(dict.fromkeys(constraints)),
    }


def _signal_names(query_analysis: dict[str, Any], profile_state: dict[str, Any], query: str) -> list[str]:
    normalized = _normalized_query(query)
    signals: list[str] = []

    if "guided_learning" in profile_state["preferences"] or query_analysis["primary_intent"] == "learning":
        signals.append("guided_learning")
    if "premium_insights" in profile_state["preferences"] or query_analysis["primary_intent"] in {"discovery", "product_explanation"}:
        signals.append("premium_insights")
    if query_analysis["primary_intent"] == "markets" or "markets_tools" in profile_state["preferences"]:
        signals.append("live_market_tools")
    if profile_state["experience_level"] == "beginner" or "beginner_friendly" in profile_state["constraints"]:
        signals.append("beginner")
    if "short_time" in profile_state["preferences"] or "time_limited" in profile_state["constraints"]:
        signals.append("time_limited")
    if "low_noise" in profile_state["preferences"]:
        signals.append("low_noise")
    if profile_state["user_type"] == "active_market_user":
        signals.append("active_market_user")
    if query_analysis["primary_intent"] == "events" or "events" in profile_state["preferences"]:
        signals.append("events_interest")
    if query_analysis["primary_intent"] == "benefits":
        signals.append("member_value")

    if _contains_any(normalized, ["where should i start", "what should i use first", "totally new", "less overwhelming"]):
        signals.extend(["premium_insights", "low_noise"])

    return list(dict.fromkeys(signals))


def compute_product_scores(
    *,
    query_analysis: dict[str, Any],
    profile_state: dict[str, Any],
    query: str,
    journey_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy = load_stage2_scoring_policy()
    score_map: dict[str, int] = {
        to_internal_product_name(name) or name: 0 for name in policy["products"].keys()
    }
    score_map.setdefault("ET Wealth Edition", 0)
    score_map.setdefault("ET Print Edition", 0)
    reasons: dict[str, list[str]] = {product: [] for product in score_map}
    normalized = _normalized_query(query)
    signals = _signal_names(query_analysis, profile_state, query)

    for signal in signals:
        weights = policy["signal_weights"].get(signal, {})
        for product_name, weight in weights.items():
            internal_name = to_internal_product_name(product_name) or product_name
            if internal_name not in score_map:
                continue
            score_map[internal_name] += int(weight)
            if weight != 0:
                reasons[internal_name].append(f"{signal.replace('_', ' ')} signal")

    for product_name in query_analysis.get("explicit_products", []):
        if product_name in score_map:
            score_map[product_name] += 4
            reasons[product_name].append("explicitly mentioned by the user")

    if query_analysis["primary_intent"] == "comparison" and len(query_analysis.get("explicit_products", [])) >= 2:
        for product_name in query_analysis["explicit_products"][:2]:
            if product_name in score_map:
                score_map[product_name] += 3
                reasons[product_name].append("part of the requested comparison")

    if query_analysis["primary_intent"] == "profile_update":
        score_map["ET Prime"] += 2
        reasons["ET Prime"].append("broad lane for profile-led ET guidance")

    if query_analysis["primary_intent"] == "product_explanation" and _contains_any(normalized, ["services", "all products", "ecosystem"]):
        score_map["ET Prime"] += 3
        reasons["ET Prime"].append("broad ET entry point for ecosystem overview")

    if query_analysis["primary_intent"] == "markets" and not query_analysis["requires_live_context"]:
        score_map["ET Prime"] += 1
        reasons["ET Prime"].append("adds context around market tools")

    if profile_state["user_type"] == "student":
        score_map["ETMasterclass"] += 3
        reasons["ETMasterclass"].append("strong fit for student learning")
        score_map["ET Prime"] += 1
        reasons["ET Prime"].append("helpful broad layer for students")

    if query_analysis["primary_intent"] == "events":
        score_map["ET Events"] += 4
        reasons["ET Events"].append("query is event-first")

    if query_analysis["primary_intent"] == "benefits":
        score_map["ET Partner Benefits"] += 4
        reasons["ET Partner Benefits"].append("query is benefit-first")

    if _contains_any(normalized, ["wealth edition", "personal finance", "mutual fund", "wealth guide"]):
        score_map["ET Wealth Edition"] += 5
        reasons["ET Wealth Edition"].append("query is wealth-content focused")

    if _contains_any(normalized, ["print edition", "epaper", "newspaper", "digital replica"]):
        score_map["ET Print Edition"] += 5
        reasons["ET Print Edition"].append("query is edition-reading focused")

    if query_analysis["primary_intent"] == "discovery" and not query_analysis.get("explicit_products"):
        score_map["ET Prime"] += 3
        reasons["ET Prime"].append("safe broad ET starting point")

    if journey_history:
        previous_products = [
            product
            for event in journey_history[-4:]
            for product in event.get("recommended_products", [])
            if product in score_map
        ]
        for product in previous_products:
            score_map[product] += 1
            reasons[product].append("conversation memory")

    scored_products = sorted(
        (
            {
                "product": product,
                "display_product": to_display_product_name(product) or product,
                "score": score,
                "reasons": list(dict.fromkeys(reasons[product]))[:3],
            }
            for product, score in score_map.items()
        ),
        key=lambda item: item["score"],
        reverse=True,
    )

    top = scored_products[0]
    second = scored_products[1] if len(scored_products) > 1 else None
    low_confidence = top["score"] <= 2
    if second and top["score"] - second["score"] <= 1 and top["score"] >= 4:
        primary_recommendation = {
            "product": "Mixed Path",
            "why": [
                f"{top['display_product']} and {second['display_product']} are both strong fits for this query."
            ]
            + top["reasons"][:1]
            + second["reasons"][:1],
            "confidence": "medium",
        }
        secondary_recommendations = [top, second]
        current_lane = LANE_MAP.get(top["product"], "discovery")
    else:
        primary_recommendation = {
            "product": top["product"],
            "display_product": top["display_product"],
            "why": top["reasons"] or ["best overall fit for the current ET path"],
            "confidence": "low" if low_confidence else ("high" if top["score"] >= 7 else "medium"),
        }
        secondary_recommendations = scored_products[1:3]
        current_lane = LANE_MAP.get(top["product"], "discovery")

    next_target = secondary_recommendations[0] if secondary_recommendations else top
    next_best_action = {
        "label": f"Explore {next_target['display_product']}",
        "href": "/search",
        "reason": f"{next_target['display_product']} is the next strongest ET lane from the current signals.",
    }

    return {
        "signals": signals,
        "scored_products": scored_products,
        "primary_recommendation": primary_recommendation,
        "secondary_recommendations": secondary_recommendations,
        "current_lane": current_lane,
        "next_best_action": next_best_action,
    }


def build_retrieval_state(
    *,
    source_citations: list[dict[str, Any]],
    verification_notes: list[str],
    retrieved_chunks: list[Any],
) -> dict[str, Any]:
    top_sources = []
    for citation in source_citations[:5]:
        top_sources.append(
            {
                "title": citation.get("label", "ET Source"),
                "url": citation.get("href"),
                "source_type": citation.get("page_type") or "other",
                "confidence": 0.85 if citation.get("verification_status") == "official_public" else 0.65,
            }
        )

    missing_information: list[str] = []
    if not retrieved_chunks:
        missing_information.append("retrieval context is thin for this query")
    if verification_notes:
        missing_information.append("some details still need live verification")

    return {
        "top_sources": top_sources,
        "conflicts_detected": verification_notes,
        "missing_information": missing_information,
    }


def build_answer_plan(query_analysis: dict[str, Any]) -> dict[str, Any]:
    sections = ["direct_answer", "why_this_fits"]
    if query_analysis["requires_table"]:
        sections.append("comparison_table")
    if query_analysis["requires_bullets"]:
        sections.append("next_steps")
    if query_analysis["requires_roadmap"]:
        sections.append("next_steps")
    if query_analysis["requires_live_context"]:
        sections.append("assumptions_and_limits")

    max_words = {"brief": 110, "standard": 180, "deep": 260}.get(query_analysis["depth_mode"], 180)
    return {
        "sections": list(dict.fromkeys(sections)),
        "must_answer_all_parts": True,
        "max_words": max_words,
    }


def build_comparison_rows(query: str, scored_products: list[dict[str, Any]]) -> list[dict[str, str]]:
    requested = detect_products_in_text(query)
    comparison_products = requested[:4] or [item["product"] for item in scored_products[:3]]
    rows: list[dict[str, str]] = []
    for product_name in comparison_products:
        product = get_product_registry(product_name)
        if not product:
            continue
        best_for = ", ".join(product.get("who_is_it_for", [])[:2]) or "ET users exploring this lane"
        why = product.get("summary") or ", ".join(product.get("key_features", [])[:2]) or "Relevant ET path"
        rows.append(
            {
                "item": to_display_product_name(product_name) or product_name,
                "best_for": best_for,
                "why": why,
            }
        )
    return rows[:4]


def build_bullet_groups(decision: dict[str, Any], query_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    primary = decision["primary_recommendation"]
    groups = [
        {
            "title": "Why this fits",
            "items": primary.get("why", [])[:3],
        }
    ]

    secondary = decision.get("secondary_recommendations", [])
    if secondary and query_analysis["depth_mode"] != "brief":
        groups.append(
            {
                "title": "Also consider",
                "items": [
                    f"{item['display_product']}: {', '.join(item['reasons'][:2]) or 'secondary ET fit'}"
                    for item in secondary[:2]
                ],
            }
        )
    return groups


def build_ui_modules(
    *,
    query_analysis: dict[str, Any],
    decision_bundle: dict[str, Any],
    comparison_rows: list[dict[str, str]],
    bullet_groups: list[dict[str, Any]],
    roadmap_steps: list[dict[str, Any]],
    verification_notes: list[str],
    profile_state: dict[str, Any],
) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    primary = decision_bundle["primary_recommendation"]
    confidence = primary.get("confidence", "medium")

    modules.append(
        {
            "module_type": "recommendation_card",
            "visible": True,
            "priority": DEFAULT_MODULE_PRIORITIES["recommendation_card"],
            "payload": {
                "product": primary.get("display_product") or primary.get("product"),
                "lane": decision_bundle["current_lane"],
                "confidence": confidence,
                "why": primary.get("why", []),
            },
        }
    )

    if comparison_rows and query_analysis["requires_table"]:
        modules.append(
            {
                "module_type": "comparison_table",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["comparison_table"],
                "payload": {"rows": comparison_rows},
            }
        )

    if query_analysis["requires_live_context"] and decision_bundle["current_lane"] == "markets":
        modules.append(
            {
                "module_type": "live_context",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["live_context"],
                "payload": {"lane": "markets"},
            }
        )

    if verification_notes or confidence == "low":
        modules.append(
            {
                "module_type": "verification_box",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["verification_box"],
                "payload": {
                    "notes": verification_notes
                    or ["The current recommendation is low confidence and should be verified on live ET pages."]
                },
            }
        )

    modules.append(
        {
            "module_type": "next_action",
            "visible": True,
            "priority": DEFAULT_MODULE_PRIORITIES["next_action"],
            "payload": decision_bundle["next_best_action"],
        }
    )

    if query_analysis["primary_intent"] == "profile_update":
        modules.append(
            {
                "module_type": "profile_card",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["profile_card"],
                "payload": {
                    "title": "Your ET Profile",
                    "fields": {
                        "user_type": profile_state["user_type"],
                        "goal": profile_state["goal"] or "still building",
                        "current_lane": decision_bundle["current_lane"],
                        "preferences": ", ".join(profile_state["preferences"][:2]) or "still learning",
                    },
                },
            }
        )

    return sorted(modules, key=lambda item: item["priority"])


def build_stage2_decision(
    *,
    query: str,
    profile: dict[str, Any],
    journey_history: list[dict[str, Any]],
    source_citations: list[dict[str, Any]],
    verification_notes: list[str],
    retrieved_chunks: list[Any],
) -> dict[str, Any]:
    query_analysis = build_query_analysis(query, profile)
    profile_state = build_profile_state(profile, query)
    scoring = compute_product_scores(
        query_analysis=query_analysis,
        profile_state=profile_state,
        query=query,
        journey_history=journey_history,
    )
    retrieval_state = build_retrieval_state(
        source_citations=source_citations,
        verification_notes=verification_notes,
        retrieved_chunks=retrieved_chunks,
    )
    answer_plan = build_answer_plan(query_analysis)
    comparison_rows = build_comparison_rows(query, scoring["scored_products"]) if query_analysis["requires_table"] else []
    bullet_groups = build_bullet_groups(scoring, query_analysis) if query_analysis["requires_bullets"] or query_analysis["depth_mode"] == "deep" else []

    current_lane = scoring["current_lane"]
    ui_modules = build_ui_modules(
        query_analysis=query_analysis,
        decision_bundle=scoring,
        comparison_rows=comparison_rows,
        bullet_groups=bullet_groups,
        roadmap_steps=[],
        verification_notes=verification_notes,
        profile_state=profile_state,
    )

    return {
        "query_analysis": {
            key: value
            for key, value in query_analysis.items()
            if key != "explicit_products"
        },
        "profile_state": profile_state,
        "retrieval_state": retrieval_state,
        "decision": {
            "primary_recommendation": scoring["primary_recommendation"],
            "secondary_recommendations": [
                {
                    "product": item["product"],
                    "display_product": item["display_product"],
                    "why": item["reasons"],
                }
                for item in scoring["secondary_recommendations"]
            ],
            "current_lane": scoring["current_lane"],
            "next_best_action": scoring["next_best_action"],
            "scored_products": scoring["scored_products"],
            "signals": scoring["signals"],
        },
        "answer_plan": answer_plan,
        "comparison_rows": comparison_rows,
        "bullet_groups": bullet_groups,
        "ui_modules": ui_modules,
        "html_snippets": [],
    }
