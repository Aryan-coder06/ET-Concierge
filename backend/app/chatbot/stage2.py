import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .registry import (
    analyze_query,
    canonical_product_name,
    get_product_lane,
    get_product_registry,
    product_display_name,
    score_products_for_query,
    select_visual_hint,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
STAGE2_RESPONSE_CONTRACT_PATH = BACKEND_ROOT / "stage2_response_contract.json"
STAGE2_SCORING_POLICY_PATH = BACKEND_ROOT / "stage2_product_scoring_policy.json"
STAGE2_UI_RENDER_CONTRACT_PATH = BACKEND_ROOT / "stage2_ui_render_contract.json"
STAGE2_ANSWER_STYLE_POLICY_PATH = BACKEND_ROOT / "stage2_answer_style_policy.md"
STAGE2_EVAL_SUITE_PATH = BACKEND_ROOT / "stage2_eval_suite.json"

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
    return canonical_product_name(product_name) or product_name


def to_display_product_name(product_name: str | None) -> str | None:
    if not product_name:
        return None
    return product_display_name(product_name) or product_name


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _detect_user_type(profile: dict, query: str) -> str:
    normalized = " ".join(str(query).lower().split())
    profession = profile.get("profession")
    if profession == "student":
        return "student"
    if profession in {"salaried_employee", "corporate_professional", "cxo"}:
        return "working_professional"
    if profession == "active_trader":
        return "active_market_user"
    if profession in {"startup_founder", "sme_owner"}:
        return "business_builder"
    if _contains_any(normalized, ["student", "college", "campus"]):
        return "student"
    if _contains_any(normalized, ["trader", "watchlist", "screeners", "markets daily"]):
        return "active_market_user"
    if _contains_any(normalized, ["founder", "entrepreneur", "business owner", "sme"]):
        return "business_builder"
    if _contains_any(normalized, ["new to et", "beginner", "first time"]):
        return "beginner_investor"
    if _contains_any(normalized, ["explore", "overwhelming", "where do i begin"]):
        return "explorer"
    return "unknown"


def build_query_analysis(query: str, profile: dict) -> dict[str, Any]:
    analysis = analyze_query(query, user_profile=profile, journey_history=[])
    return {
        "normalized_query": analysis.get("normalized_query", query),
        "primary_intent": analysis.get("primary_intent", "product_explanation"),
        "secondary_intents": analysis.get("secondary_intents", []),
        "requires_live_context": analysis.get("requires_live_context", False),
        "requires_table": analysis.get("requires_table", False),
        "requires_bullets": analysis.get("requires_bullets", False),
        "requires_roadmap": analysis.get("requires_roadmap", False),
        "depth_mode": analysis.get("depth_mode", "standard"),
        "tone_mode": analysis.get("tone_mode", "friendly_professional"),
        "explicit_products": analysis.get("explicit_products", []),
        "query_mode": analysis.get("query_mode", "information_mode"),
        "matched_lanes": analysis.get("matched_lanes", []),
        "lane_scores": analysis.get("lane_scores", {}),
        "top_lane": analysis.get("top_lane"),
        "broad_overview": analysis.get("broad_overview", False),
        "format_rules": analysis.get("format_rules", []),
        "anti_bias_rules": analysis.get("anti_bias_rules", []),
    }


def build_profile_state(profile: dict, query: str) -> dict[str, Any]:
    query_analysis = analyze_query(query, user_profile=profile, journey_history=[])
    normalized = query_analysis.get("normalized_query", " ".join(str(query).lower().split()))
    preferences: list[str] = []
    constraints: list[str] = []

    matched_lanes = set(query_analysis.get("matched_lanes", []))

    if "learning_and_upskilling" in matched_lanes or _contains_any(normalized, ["learn", "learning", "student", "guide", "guided", "course", "masterclass"]):
        preferences.append("guided_learning")
    if "markets_and_tracking" in matched_lanes or "live_video_business_news" in matched_lanes or query_analysis.get("requires_live_context"):
        preferences.append("markets_tools")
    if query_analysis.get("broad_overview") or _contains_any(normalized, ["deeper context", "less noise", "overwhelming"]):
        preferences.append("premium_insights")
    if "events_and_community" in matched_lanes or _contains_any(normalized, ["event", "conference", "summit", "community", "network"]):
        preferences.append("events")
    if _contains_any(normalized, ["short time", "quickly", "time limited", "30 minutes"]):
        preferences.append("short_time")

    if profile.get("sophistication") == "beginner" or _contains_any(normalized, ["beginner", "new to et", "totally new"]):
        constraints.append("beginner_friendly")
    if _contains_any(normalized, ["time limited", "short time", "quickly"]):
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


def compute_product_scores(
    *,
    query_analysis: dict[str, Any],
    profile_state: dict[str, Any],
    query: str,
    profile: dict[str, Any],
    journey_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scored_products = score_products_for_query(
        query,
        user_profile=profile,
        journey_history=journey_history or [],
        analysis=query_analysis,
    )

    if not scored_products:
        return {
            "signals": [],
            "scored_products": [],
            "primary_recommendation": {
                "product": None,
                "display_product": None,
                "why": ["No strong ET lane could be determined from the current query."],
                "confidence": "low",
            },
            "secondary_recommendations": [],
            "current_lane": query_analysis.get("top_lane"),
            "next_best_action": None,
        }

    top = scored_products[0]
    second = scored_products[1] if len(scored_products) > 1 else None
    low_confidence = top["score"] <= 4
    mixed_path = bool(second and top["score"] - second["score"] <= 1 and second["score"] >= 5)

    if mixed_path:
        primary_recommendation = {
            "product": "Mixed Path",
            "display_product": "Mixed Path",
            "why": [
                f"{top['display_product']} and {second['display_product']} are both strong fits for this query."
            ]
            + top["reasons"][:1]
            + second["reasons"][:1],
            "confidence": "medium",
        }
        secondary_recommendations = scored_products[:2]
        current_lane = top["lane"] or second["lane"]
    else:
        primary_recommendation = {
            "product": top["product"],
            "display_product": top["display_product"],
            "why": top["reasons"][:3] or ["Best overall ET fit for the current query."],
            "confidence": "low" if low_confidence else ("high" if top["score"] >= 10 else "medium"),
        }
        secondary_recommendations = scored_products[1:3]
        current_lane = top["lane"]

    next_target = secondary_recommendations[0] if secondary_recommendations else top
    next_best_action = {
        "label": f"Explore {next_target['display_product']}",
        "href": "/search",
        "reason": f"{next_target['display_product']} is the next strongest ET lane from the current signals.",
    }

    return {
        "signals": query_analysis.get("matched_lanes", [])[:4],
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
    if query_analysis["requires_bullets"] or query_analysis["requires_roadmap"]:
        sections.append("next_steps")
    if query_analysis["requires_live_context"]:
        sections.append("assumptions_and_limits")

    max_words = {"brief": 110, "standard": 180, "overview": 220, "deep": 260}.get(
        query_analysis["depth_mode"],
        180,
    )
    return {
        "sections": list(dict.fromkeys(sections)),
        "must_answer_all_parts": True,
        "max_words": max_words,
    }


def build_comparison_rows(query: str, scored_products: list[dict[str, Any]]) -> list[dict[str, str]]:
    requested = analyze_query(query, user_profile={}, journey_history=[]).get("explicit_products", [])
    comparison_products = requested[:4] or [item["product"] for item in scored_products[:3]]
    rows: list[dict[str, str]] = []
    for product_name in comparison_products:
        product = get_product_registry(product_name)
        if not product:
            continue
        best_for = ", ".join(product.get("best_for", [])[:2]) or "ET users exploring this lane"
        why = product.get("summary") or ", ".join(product.get("key_features", [])[:2]) or "Relevant ET path"
        rows.append(
            {
                "item": to_display_product_name(product_name) or product_name,
                "best_for": best_for,
                "why": why,
            }
        )
    return rows[:4]


def build_bullet_groups(
    decision: dict[str, Any],
    query_analysis: dict[str, Any],
    profile_state: dict[str, Any],
) -> list[dict[str, Any]]:
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

    if profile_state.get("constraints") and query_analysis["depth_mode"] != "brief":
        groups.append(
            {
                "title": "Watch-outs",
                "items": [
                    constraint.replace("_", " ").title()
                    for constraint in profile_state["constraints"][:3]
                ],
            }
        )

    return groups


def build_ui_modules(
    *,
    query: str,
    query_analysis: dict[str, Any],
    decision_bundle: dict[str, Any],
    comparison_rows: list[dict[str, str]],
    verification_notes: list[str],
    profile_state: dict[str, Any],
) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    primary = decision_bundle["primary_recommendation"]
    confidence = primary.get("confidence", "medium")
    primary_product = primary.get("product")
    has_primary_product = bool(primary_product and primary_product != "Mixed Path")
    query_mode = query_analysis.get("query_mode")
    visual_hint = select_visual_hint(
        query,
        [primary_product] if has_primary_product else [],
        user_profile={"profession": profile_state.get("user_type"), "sophistication": profile_state.get("experience_level")},
        verification_notes=verification_notes,
    )

    if primary.get("display_product") or primary.get("product"):
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

    if visual_hint:
        modules.append(
            {
                "module_type": "live_context",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["live_context"],
                "payload": {"hint": visual_hint, "lane": decision_bundle["current_lane"]},
            }
        )

    if verification_notes or (has_primary_product and confidence == "low"):
        modules.append(
            {
                "module_type": "verification_box",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["verification_box"],
                "payload": {
                    "notes": verification_notes
                    or ["The current recommendation is low confidence and should be checked against live ET pages."]
                },
            }
        )

    if decision_bundle.get("next_best_action") and query_mode != "chitchat":
        modules.append(
            {
                "module_type": "next_action",
                "visible": True,
                "priority": DEFAULT_MODULE_PRIORITIES["next_action"],
                "payload": decision_bundle["next_best_action"],
            }
        )

    if query_analysis["query_mode"] == "concierge_mode":
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
        profile=profile,
        journey_history=journey_history,
    )
    retrieval_state = build_retrieval_state(
        source_citations=source_citations,
        verification_notes=verification_notes,
        retrieved_chunks=retrieved_chunks,
    )
    answer_plan = build_answer_plan(query_analysis)
    comparison_rows = (
        build_comparison_rows(query, scoring["scored_products"])
        if query_analysis["requires_table"]
        else []
    )
    bullet_groups = (
        build_bullet_groups(scoring, query_analysis, profile_state)
        if query_analysis["requires_bullets"] or query_analysis["depth_mode"] in {"deep", "overview"}
        else []
    )
    ui_modules = build_ui_modules(
        query=query,
        query_analysis=query_analysis,
        decision_bundle=scoring,
        comparison_rows=comparison_rows,
        verification_notes=verification_notes,
        profile_state=profile_state,
    )

    return {
        "query_analysis": query_analysis,
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
