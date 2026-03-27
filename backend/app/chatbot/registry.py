import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PACK_PATH = BACKEND_ROOT / "backend_data_et_sources.json"
PRODUCT_PACK_PATH = BACKEND_ROOT / "backend_data_et_product_registry.json"
EVAL_PACK_PATH = BACKEND_ROOT / "backend_data_et_eval_prompts.json"
BOOTSTRAP_CHUNKS_PATH = BACKEND_ROOT / "backend_data_et_chunks.jsonl"

PRODUCT_NAME_OVERRIDES = {
    "et masterclass": "ETMasterclass",
    "masterclass": "ETMasterclass",
    "et edge": "ET Events",
    "et edge events": "ET Events",
    "et benefits": "ET Partner Benefits",
    "partner benefits": "ET Partner Benefits",
    "times prime": "ET Partner Benefits",
    "benefits": "ET Partner Benefits",
    "wealth edition": "ET Wealth Edition",
    "print edition": "ET Print Edition",
    "e paper": "ET Print Edition",
    "epaper": "ET Print Edition",
}

ROUTE_KEYWORDS = {
    "ET Prime": [
        "new to et",
        "where should i start",
        "start with et",
        "et prime",
        "membership",
        "subscribe",
        "analysis",
        "premium stories",
        "ecosystem",
        "beyond articles",
    ],
    "ET Markets": [
        "markets",
        "trading",
        "stocks",
        "investing",
        "screeners",
        "watchlist",
        "market mood",
        "stock reports plus",
        "stock report plus",
        "stock reports",
        "stock tools",
        "live stream",
    ],
    "ET Portfolio": [
        "portfolio",
        "track investments",
        "track my investments",
        "investment tracking",
        "holdings",
        "sip",
        "sip updates",
        "goals",
        "alerts",
        "watchlists",
    ],
    "ET Wealth Edition": [
        "wealth edition",
        "money management",
        "wealth guide",
        "personal finance",
        "mutual fund",
    ],
    "ET Print Edition": [
        "print edition",
        "epaper",
        "newspaper",
        "digital replica",
    ],
    "ETMasterclass": [
        "masterclass",
        "learning",
        "course",
        "courses",
        "workshop",
        "certification",
        "skill",
        "learn",
        "leadership",
        "ai innovation",
        "executive education",
    ],
    "ET Events": [
        "events",
        "event path",
        "summit",
        "conference",
        "conclave",
        "community",
        "register",
        "portal",
    ],
    "ET Partner Benefits": [
        "benefits",
        "times prime",
        "partner offers",
        "redeem",
        "activate",
        "voucher",
        "complimentary",
    ],
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", value.lower())).strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_source_registry() -> list[dict[str, Any]]:
    return _load_json(SOURCE_PACK_PATH)


@lru_cache(maxsize=1)
def load_product_registry() -> list[dict[str, Any]]:
    return _load_json(PRODUCT_PACK_PATH)


@lru_cache(maxsize=1)
def load_eval_prompts() -> list[dict[str, Any]]:
    return _load_json(EVAL_PACK_PATH)


@lru_cache(maxsize=1)
def load_bootstrap_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for line in BOOTSTRAP_CHUNKS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            chunks.append(json.loads(line))
    return chunks


@lru_cache(maxsize=1)
def source_registry_by_id() -> dict[str, dict[str, Any]]:
    return {item["source_id"]: item for item in load_source_registry()}


@lru_cache(maxsize=1)
def source_registry_by_url() -> dict[str, dict[str, Any]]:
    return {item["url"]: item for item in load_source_registry()}


@lru_cache(maxsize=1)
def product_registry_by_name() -> dict[str, dict[str, Any]]:
    return {item["product_name"]: item for item in load_product_registry()}


@lru_cache(maxsize=1)
def product_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for product_name in product_registry_by_name():
        normalized = _normalize_text(product_name)
        aliases[normalized] = product_name
        aliases[normalized.replace(" ", "")] = product_name
        aliases[product_name.lower()] = product_name

    aliases.update(PRODUCT_NAME_OVERRIDES)
    return aliases


def official_product_names() -> list[str]:
    return list(product_registry_by_name().keys())


def canonical_product_name(product_name: str | None) -> str | None:
    if not product_name:
        return None
    normalized = _normalize_text(product_name)
    return product_alias_map().get(normalized) or product_alias_map().get(
        normalized.replace(" ", "")
    )


def get_product_registry(product_name: str | None) -> dict[str, Any] | None:
    canonical_name = canonical_product_name(product_name)
    if not canonical_name:
        return None
    return product_registry_by_name().get(canonical_name)


def get_source_metadata(source_id: str | None) -> dict[str, Any] | None:
    if not source_id:
        return None
    return source_registry_by_id().get(source_id)


def get_source_by_url(source_url: str | None) -> dict[str, Any] | None:
    if not source_url:
        return None
    return source_registry_by_url().get(source_url)


def list_products_by_category(category: str) -> list[dict[str, Any]]:
    normalized_category = category.strip().lower()
    return [
        product
        for product in load_product_registry()
        if str(product.get("category", "")).strip().lower() == normalized_category
    ]


def detect_products_in_text(text: str) -> list[str]:
    normalized = _normalize_text(text)
    matches: list[str] = []
    for alias, canonical_name in product_alias_map().items():
        if alias and alias in normalized and canonical_name not in matches:
            matches.append(canonical_name)
    return matches


def product_registry_context(product_names: list[str]) -> str:
    blocks: list[str] = []
    for product_name in product_names:
        product = get_product_registry(product_name)
        if not product:
            continue
        pricing_notes = [
            f"{note.get('fact')}: {note.get('details') or note.get('value')}"
            for note in product.get("pricing_notes", [])
        ]
        blocks.append(
            "\n".join(
                [
                    f"Product: {product['product_name']}",
                    f"Summary: {product.get('summary', '')}",
                    f"Who it fits: {', '.join(product.get('who_is_it_for', []))}",
                    f"Key features: {', '.join(product.get('key_features', []))}",
                    f"Benefits: {', '.join(product.get('benefits', []))}",
                    f"Verification status: {product.get('verification_status', 'unknown')}",
                    (
                        f"Pricing and access notes: {'; '.join(pricing_notes)}"
                        if pricing_notes
                        else "Pricing and access notes: none"
                    ),
                ]
            )
        )
    return "\n\n".join(blocks)


def canonical_sources_for_product(product_name: str) -> list[dict[str, Any]]:
    product = get_product_registry(product_name)
    if not product:
        return []
    citations: list[dict[str, Any]] = []
    for source_id in product.get("canonical_sources", []):
        source = get_source_metadata(source_id)
        if source:
            citations.append(source)
    return citations


def route_user_intent_to_products(
    query: str,
    user_profile: dict[str, Any],
    journey_history: list[dict[str, Any]] | None = None,
) -> list[str]:
    journey_history = journey_history or []
    normalized_query = _normalize_text(query)
    scores = {product_name: 0 for product_name in official_product_names()}
    broad_overview_query = any(
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
            "beyond just articles",
        ]
    )

    explicit_products = detect_products_in_text(query)
    for product_name in explicit_products:
        scores[product_name] += 8

    for product_name, keywords in ROUTE_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in normalized_query)
        if hits:
            scores[product_name] += hits * 2

    if any(
        phrase in normalized_query
        for phrase in [
            "what product is right for me",
            "what et product",
            "new to et",
            "where should i start",
            "best place to begin",
            "et ecosystem",
        ]
    ):
        scores["ET Prime"] += 4

    if "beginner investor" in normalized_query:
        scores["ET Markets"] += 4
        scores["ET Prime"] += 3
        scores["ET Portfolio"] += 2

    if "market mood" in normalized_query:
        scores["ET Markets"] += 6

    if "stock reports plus" in normalized_query or "stock report plus" in normalized_query:
        scores["ET Markets"] += 6
        scores["ET Prime"] += 2

    if "enterprise ai" in normalized_query and any(
        term in normalized_query for term in ["event", "events", "summit", "conference", "path"]
    ):
        scores["ET Events"] += 6

    if broad_overview_query:
        overview_boosts = {
            "ET Prime": 6,
            "ET Markets": 5,
            "ET Portfolio": 4,
            "ETMasterclass": 4,
            "ET Events": 4,
            "ET Partner Benefits": 3,
            "ET Wealth Edition": 3,
            "ET Print Edition": 3,
        }
        for product_name, boost in overview_boosts.items():
            scores[product_name] += boost

    profile_intent = user_profile.get("intent")
    if profile_intent == "investing":
        scores["ET Markets"] += 3
        scores["ET Portfolio"] += 2
    elif profile_intent == "news":
        scores["ET Prime"] += 2
        scores["ET Print Edition"] += 1
    elif profile_intent == "growing_business":
        scores["ET Events"] += 2
        scores["ETMasterclass"] += 2

    profession = str(user_profile.get("profession") or "")
    if profession == "student":
        scores["ETMasterclass"] += 1
        scores["ET Markets"] += 1

    for event in journey_history[-3:]:
        for product_name in event.get("recommended_products", []) or event.get(
            "recommendations", []
        ):
            canonical_name = canonical_product_name(product_name)
            if canonical_name in scores:
                scores[canonical_name] += 1

    if scores["ET Wealth Edition"] > 0:
        scores["ET Prime"] += 2
    if scores["ET Partner Benefits"] > 0:
        scores["ET Prime"] += 2
    if scores["ET Events"] > 0:
        scores["ET Prime"] += 1
    if scores["ET Portfolio"] > 0:
        scores["ET Markets"] += 1

    ranked = [
        product_name
        for product_name, score in sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if score > 0
    ]

    if not ranked:
        ranked = ["ET Prime"]

    return ranked[:8] if broad_overview_query else ranked[:4]


def build_verification_notes(query: str, product_names: list[str]) -> list[str]:
    normalized_query = _normalize_text(query)
    notes: list[str] = []
    seen: set[str] = set()

    price_or_trial_query = any(
        keyword in normalized_query
        for keyword in ["trial", "price", "pricing", "offer", "discount", "free trial"]
    )
    benefits_query = any(
        keyword in normalized_query
        for keyword in ["benefit", "benefits", "activate", "redeem", "voucher"]
    )
    wealth_query = any(
        keyword in normalized_query
        for keyword in ["wealth", "wealth edition", "money management", "personal finance"]
    )

    for product_name in product_names:
        product = get_product_registry(product_name)
        if not product:
            continue

        for note in product.get("pricing_notes", []):
            verification_status = note.get("verification_status")
            fact = str(note.get("fact", ""))
            details = str(note.get("details") or note.get("value") or "").strip()

            if (
                price_or_trial_query
                and verification_status == "conflicting_public_signals"
                and fact == "trial_status"
            ):
                message = (
                    "ET Prime trial information has mixed public signals right now. "
                    "Use the official checkout or latest live ET page to confirm the current offer."
                )
            elif benefits_query and "activation_constraint" in fact:
                message = (
                    "Some ET partner benefits have activation constraints. "
                    "For example, Times Prime activation is limited to an Indian mobile number."
                )
            elif wealth_query and details and "free with ET Prime membership" in details:
                message = (
                    "ET Wealth Edition is best treated as an ET Prime benefit lane, "
                    "not a separate standalone membership."
                )
            else:
                continue

            if message not in seen:
                seen.add(message)
                notes.append(message)

    return notes
