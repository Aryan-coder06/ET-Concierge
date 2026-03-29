import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BACKEND_ROOT = Path(__file__).resolve().parents[2]
STAGE1_ROOT = BACKEND_ROOT / "STAGE_1"

STAGE1_SOURCE_PACK_PATH = BACKEND_ROOT / "backend_data_et_sources.json"
STAGE1_PRODUCT_PACK_PATH = BACKEND_ROOT / "backend_data_et_product_registry.json"
STAGE1_EVAL_PACK_PATH = BACKEND_ROOT / "backend_data_et_eval_prompts.json"
STAGE1_BOOTSTRAP_CHUNKS_PATH = BACKEND_ROOT / "backend_data_et_chunks.jsonl"

NONPRIME_SOURCE_PACK_PATH = BACKEND_ROOT / "backend_data_et_nonprime_heavy_sources.json"
NONPRIME_PRODUCT_PACK_PATH = BACKEND_ROOT / "backend_data_et_nonprime_heavy_product_registry.json"
NONPRIME_EVAL_PACK_PATH = BACKEND_ROOT / "backend_data_et_nonprime_heavy_eval_prompts.json"
NONPRIME_BOOTSTRAP_CHUNKS_PATH = BACKEND_ROOT / "backend_data_et_nonprime_heavy_chunks.jsonl"
ROUTER_POLICY_PATH = BACKEND_ROOT / "backend_data_et_router_behavior_policy.json"


def _first_existing_path(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    path_list = ", ".join(str(path) for path in paths)
    raise FileNotFoundError(f"None of the expected ET data pack files were found: {path_list}")


def _pack_path(root_path: Path, stage1_path: Path) -> Path:
    return _first_existing_path(root_path, stage1_path)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", value.lower())).strip()


def _slugify(value: str) -> str:
    normalized = _normalize_text(value).replace(" ", "_")
    return normalized or "item"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> Any | None:
    return _read_json(path) if path.exists() else None


def _split_terms(values: list[Any] | None) -> list[str]:
    terms: list[str] = []
    for value in values or []:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            terms.append(normalized)
    return terms


def _coalesce_str(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _derive_display_name(product_name: str) -> str:
    if product_name == "ETMasterclass":
        return "ET Masterclass"
    if product_name == "ET Partner Benefits":
        return "ET Benefits"
    return product_name


def _derive_stage1_lane(product: dict[str, Any]) -> str:
    product_name = str(product.get("product_name") or "")
    category = _normalize_text(str(product.get("category") or ""))
    summary = _normalize_text(str(product.get("summary") or ""))
    features = " ".join(_split_terms(product.get("key_features")))
    feature_text = _normalize_text(features)

    if "masterclass" in product_name.lower() or "workshop" in summary or "course" in summary:
        return "learning_and_upskilling"
    if "markets" in category or "market" in summary or "portfolio" in summary:
        return "markets_and_tracking"
    if "event" in category or "summit" in summary or "conference" in summary:
        return "events_and_community"
    if "benefit" in category or "times prime" in summary or "partner" in summary:
        return "membership_benefits"
    if "learn" in summary or "course" in summary or "workshop" in feature_text:
        return "learning_and_upskilling"
    if "wealth" in product_name.lower():
        return "wealth_and_personal_finance_content"
    if "print" in product_name.lower() or "edition" in product_name.lower():
        return "edition_and_reading"
    return "premium_insights"


def _derive_stage1_aliases(product_name: str) -> list[str]:
    aliases = {
        product_name,
        product_name.lower(),
        product_name.replace(" ", ""),
        product_name.lower().replace(" ", ""),
    }

    lowered = product_name.lower()
    if lowered == "etmasterclass":
        aliases.update({"et masterclass", "masterclass"})
    if lowered == "et partner benefits":
        aliases.update({"et benefits", "partner benefits", "times prime", "benefits"})
    if lowered == "et wealth edition":
        aliases.update({"wealth edition"})
    if lowered == "et print edition":
        aliases.update({"print edition", "epaper", "e paper"})
    return sorted(alias for alias in aliases if alias)


def _normalize_stage1_product(product: dict[str, Any]) -> dict[str, Any]:
    product_name = str(product["product_name"]).strip()
    return {
        "product_name": product_name,
        "display_name": _derive_display_name(product_name),
        "aliases": _derive_stage1_aliases(product_name),
        "lane": _derive_stage1_lane(product),
        "summary": _coalesce_str(product.get("summary")) or "",
        "best_for": _split_terms(product.get("who_is_it_for")) + _split_terms(product.get("benefits")),
        "retrieval_keywords": (
            _split_terms(product.get("key_features"))
            + _split_terms(product.get("benefits"))
            + _split_terms(product.get("partner_or_service_types"))
            + _split_terms(product.get("events_or_courses"))
            + _split_terms(product.get("cta_labels"))
        ),
        "source_priority": _split_terms(product.get("canonical_sources")),
        "who_is_it_for": _split_terms(product.get("who_is_it_for")),
        "key_features": _split_terms(product.get("key_features")),
        "benefits": _split_terms(product.get("benefits")),
        "category": _coalesce_str(product.get("category")) or "",
        "canonical_sources": _split_terms(product.get("canonical_sources")),
        "verification_status": _coalesce_str(product.get("verification_status")) or "official_public",
        "source_pack": "stage1",
    }


def _normalize_nonprime_product(product: dict[str, Any]) -> dict[str, Any]:
    product_name = str(product["product_name"]).strip()
    return {
        "product_name": product_name,
        "display_name": _derive_display_name(product_name),
        "aliases": _split_terms(product.get("aliases")) or _derive_stage1_aliases(product_name),
        "lane": _coalesce_str(product.get("lane")) or "information_lane",
        "summary": _coalesce_str(product.get("summary")) or "",
        "best_for": _split_terms(product.get("best_for")),
        "retrieval_keywords": _split_terms(product.get("retrieval_keywords")) + _split_terms(product.get("sub_lanes")),
        "source_priority": _split_terms(product.get("source_priority")),
        "who_is_it_for": _split_terms(product.get("best_for")),
        "key_features": _split_terms(product.get("sub_lanes")),
        "benefits": [],
        "category": _coalesce_str(product.get("lane")) or "",
        "canonical_sources": _split_terms(product.get("source_priority")),
        "verification_status": "official_public",
        "reason_not_to_route_to_prime": _coalesce_str(product.get("reason_not_to_route_to_prime")),
        "source_pack": "nonprime",
    }


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            normalized = value.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    return merged


def _merge_product_records(stage1: dict[str, Any] | None, nonprime: dict[str, Any] | None) -> dict[str, Any]:
    source = nonprime or stage1 or {}
    product_name = str(source.get("product_name") or "")
    return {
        "product_name": product_name,
        "display_name": _coalesce_str(
            nonprime.get("display_name") if nonprime else None,
            stage1.get("display_name") if stage1 else None,
            _derive_display_name(product_name),
        )
        or product_name,
        "aliases": _merge_unique_strings(
            stage1.get("aliases", []) if stage1 else [],
            nonprime.get("aliases", []) if nonprime else [],
        ),
        "lane": _coalesce_str(
            nonprime.get("lane") if nonprime else None,
            stage1.get("lane") if stage1 else None,
            "information_lane",
        )
        or "information_lane",
        "summary": _coalesce_str(
            nonprime.get("summary") if nonprime else None,
            stage1.get("summary") if stage1 else None,
        )
        or "",
        "best_for": _merge_unique_strings(
            stage1.get("best_for", []) if stage1 else [],
            nonprime.get("best_for", []) if nonprime else [],
        ),
        "retrieval_keywords": _merge_unique_strings(
            stage1.get("retrieval_keywords", []) if stage1 else [],
            nonprime.get("retrieval_keywords", []) if nonprime else [],
        ),
        "source_priority": _merge_unique_strings(
            stage1.get("source_priority", []) if stage1 else [],
            nonprime.get("source_priority", []) if nonprime else [],
        ),
        "who_is_it_for": _merge_unique_strings(
            stage1.get("who_is_it_for", []) if stage1 else [],
            nonprime.get("who_is_it_for", []) if nonprime else [],
        ),
        "key_features": _merge_unique_strings(
            stage1.get("key_features", []) if stage1 else [],
            nonprime.get("key_features", []) if nonprime else [],
        ),
        "benefits": _merge_unique_strings(
            stage1.get("benefits", []) if stage1 else [],
            nonprime.get("benefits", []) if nonprime else [],
        ),
        "category": _coalesce_str(
            stage1.get("category") if stage1 else None,
            nonprime.get("category") if nonprime else None,
        )
        or "",
        "canonical_sources": _merge_unique_strings(
            stage1.get("canonical_sources", []) if stage1 else [],
            nonprime.get("canonical_sources", []) if nonprime else [],
        ),
        "verification_status": _coalesce_str(
            stage1.get("verification_status") if stage1 else None,
            nonprime.get("verification_status") if nonprime else None,
            "official_public",
        )
        or "official_public",
        "reason_not_to_route_to_prime": _coalesce_str(
            nonprime.get("reason_not_to_route_to_prime") if nonprime else None
        ),
        "source_pack": ",".join(
            value
            for value in [stage1.get("source_pack") if stage1 else None, nonprime.get("source_pack") if nonprime else None]
            if value
        ),
    }


def _normalize_stage1_source(source: dict[str, Any]) -> dict[str, Any]:
    source_id = str(source["source_id"]).strip()
    product_name = str(source.get("product_area") or "").strip()
    title = _coalesce_str(source.get("title")) or source_id
    return {
        "source_id": source_id,
        "product_name": product_name or None,
        "product_area": product_name or None,
        "title": title,
        "url": _coalesce_str(source.get("url")),
        "page_type": _coalesce_str(source.get("page_type")) or "source_page",
        "source_tier": _coalesce_str(source.get("source_tier")) or "primary",
        "verification_status": _coalesce_str(source.get("verification_status")) or "official_public",
        "priority": int(source.get("priority", 50)) if str(source.get("priority", "")).strip() else 50,
        "tags": _split_terms(source.get("recommended_use")) + _split_terms(source.get("evidence_highlights")),
        "source_of_truth": bool(source.get("source_of_truth")),
        "last_verified_at": _coalesce_str(source.get("last_verified_at")),
        "notes": _coalesce_str(source.get("notes")),
        "recommended_use": _split_terms(source.get("recommended_use")),
        "evidence_highlights": _split_terms(source.get("evidence_highlights")),
    }


def _generate_nonprime_source_id(source: dict[str, Any]) -> str:
    product = _slugify(str(source.get("product") or "source"))
    page_type = _slugify(str(source.get("page_type") or "page"))
    parsed = urlparse(str(source.get("url") or ""))
    slug = _slugify((parsed.path or "").strip("/").replace("/", "_") or "home")
    return f"{product}::{page_type}::{slug}"


def _generate_nonprime_title(source: dict[str, Any]) -> str:
    product = str(source.get("product") or "ET Source").strip()
    page_type = str(source.get("page_type") or "page").replace("_", " ").title()
    return f"{product} {page_type}".strip()


def _normalize_nonprime_source(source: dict[str, Any]) -> dict[str, Any]:
    product_name = str(source.get("product") or "").strip()
    priority = source.get("priority", 50)
    return {
        "source_id": _generate_nonprime_source_id(source),
        "product_name": product_name,
        "product_area": product_name,
        "title": _generate_nonprime_title(source),
        "url": _coalesce_str(source.get("url")),
        "page_type": _coalesce_str(source.get("page_type")) or "source_page",
        "source_tier": _coalesce_str(source.get("source_tier")) or "official_public",
        "verification_status": "official_public",
        "priority": int(priority) if isinstance(priority, (int, float, str)) and str(priority).strip() else 50,
        "tags": _split_terms(source.get("tags")),
        "lane": _coalesce_str(source.get("lane")),
        "source_of_truth": True,
        "last_verified_at": None,
        "notes": None,
        "recommended_use": _split_terms(source.get("tags")),
        "evidence_highlights": [],
    }


def _merge_source_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        merged[record["source_id"]] = record
    return list(merged.values())


def _stage1_eval_path() -> Path:
    return _pack_path(STAGE1_EVAL_PACK_PATH, STAGE1_ROOT / "backend_data_et_eval_prompts.json")


def _stage1_bootstrap_path() -> Path:
    return _pack_path(STAGE1_BOOTSTRAP_CHUNKS_PATH, STAGE1_ROOT / "backend_data_et_chunks.jsonl")


@lru_cache(maxsize=1)
def load_router_behavior_policy() -> dict[str, Any]:
    payload = _read_json_if_exists(ROUTER_POLICY_PATH)
    return payload if isinstance(payload, dict) else {}


def load_router_anti_bias_rules() -> list[str]:
    return list(load_router_behavior_policy().get("anti_bias_rules", []))


def load_router_format_rules() -> list[str]:
    return list(load_router_behavior_policy().get("format_rules", []))


@lru_cache(maxsize=1)
def _policy_anti_bias_targets() -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for rule in load_router_anti_bias_rules():
        normalized_rule = _normalize_text(rule)
        targets.append(
            {
                "rule": rule,
                "products": detect_products_in_text(rule),
                "lanes": list(detect_lanes_in_text(rule).keys()),
                "text": normalized_rule,
            }
        )
    return targets


@lru_cache(maxsize=1)
def load_product_registry() -> list[dict[str, Any]]:
    stage1_payload = _read_json(_pack_path(STAGE1_PRODUCT_PACK_PATH, STAGE1_ROOT / "backend_data_et_product_registry.json"))
    stage1_products = {
        item["product_name"]: _normalize_stage1_product(item)
        for item in stage1_payload
    }

    nonprime_payload = _read_json_if_exists(NONPRIME_PRODUCT_PACK_PATH) or {}
    nonprime_products = {
        item["product_name"]: _normalize_nonprime_product(item)
        for item in nonprime_payload.get("products", [])
    }

    merged_names = sorted(set(stage1_products) | set(nonprime_products))
    return [
        _merge_product_records(stage1_products.get(name), nonprime_products.get(name))
        for name in merged_names
    ]


@lru_cache(maxsize=1)
def load_source_registry() -> list[dict[str, Any]]:
    stage1_payload = _read_json(_pack_path(STAGE1_SOURCE_PACK_PATH, STAGE1_ROOT / "backend_data_et_sources.json"))
    stage1_sources = [_normalize_stage1_source(item) for item in stage1_payload]

    nonprime_payload = _read_json_if_exists(NONPRIME_SOURCE_PACK_PATH) or {}
    nonprime_sources = [_normalize_nonprime_source(item) for item in nonprime_payload.get("sources", [])]

    canonicalized: list[dict[str, Any]] = []
    for source in stage1_sources + nonprime_sources:
        normalized = dict(source)
        product_name = canonical_product_name(normalized.get("product_name"))
        if product_name:
            normalized["product_name"] = product_name
        canonicalized.append(normalized)

    return _merge_source_records(canonicalized)


@lru_cache(maxsize=1)
def load_eval_prompts() -> list[dict[str, Any]]:
    payload = _read_json(_stage1_eval_path())
    return payload if isinstance(payload, list) else []


@lru_cache(maxsize=1)
def load_nonprime_eval_prompts() -> dict[str, Any]:
    payload = _read_json_if_exists(NONPRIME_EVAL_PACK_PATH)
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def load_bootstrap_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    paths = [_stage1_bootstrap_path()]
    if NONPRIME_BOOTSTRAP_CHUNKS_PATH.exists():
        paths.append(NONPRIME_BOOTSTRAP_CHUNKS_PATH)

    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


@lru_cache(maxsize=1)
def source_registry_by_id() -> dict[str, dict[str, Any]]:
    return {item["source_id"]: item for item in load_source_registry()}


@lru_cache(maxsize=1)
def source_registry_by_url() -> dict[str, dict[str, Any]]:
    return {item["url"]: item for item in load_source_registry() if item.get("url")}


@lru_cache(maxsize=1)
def source_registry_by_product() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in load_source_registry():
        product_name = item.get("product_name")
        if not product_name:
            continue
        grouped.setdefault(product_name, []).append(item)
    for product_name, sources in grouped.items():
        grouped[product_name] = sorted(
            sources,
            key=lambda source: int(source.get("priority") or 50),
            reverse=True,
        )
    return grouped


@lru_cache(maxsize=1)
def product_registry_by_name() -> dict[str, dict[str, Any]]:
    return {item["product_name"]: item for item in load_product_registry()}


@lru_cache(maxsize=1)
def product_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for product in load_product_registry():
        product_name = product["product_name"]
        raw_aliases = _merge_unique_strings(
            product.get("aliases", []),
            [product_name, product_name.lower(), product_name.replace(" ", ""), product_name.lower().replace(" ", "")],
        )
        for alias in raw_aliases:
            normalized = _normalize_text(alias)
            compact = normalized.replace(" ", "")
            if normalized and len(compact) >= 4:
                aliases[normalized] = product_name
                aliases[compact] = product_name
    return aliases


@lru_cache(maxsize=1)
def product_lane_map() -> dict[str, str]:
    return {product["product_name"]: str(product.get("lane") or "information_lane") for product in load_product_registry()}


@lru_cache(maxsize=1)
def lane_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for product in load_product_registry():
        lane = str(product.get("lane") or "information_lane")
        bucket = catalog.setdefault(
            lane,
            {
                "lane": lane,
                "products": [],
                "keywords": [],
            },
        )
        bucket["products"].append(product["product_name"])
        bucket["keywords"] = _merge_unique_strings(
            bucket["keywords"],
            product.get("aliases", []),
            product.get("retrieval_keywords", []),
            product.get("best_for", []),
            product.get("who_is_it_for", []),
            product.get("key_features", []),
            [product.get("summary", "")],
        )
    return catalog


def official_product_names() -> list[str]:
    return list(product_registry_by_name().keys())


def canonical_product_name(product_name: str | None) -> str | None:
    if not product_name:
        return None
    normalized = _normalize_text(product_name)
    return product_alias_map().get(normalized) or product_alias_map().get(normalized.replace(" ", ""))


def get_product_registry(product_name: str | None) -> dict[str, Any] | None:
    canonical_name = canonical_product_name(product_name)
    if not canonical_name:
        return None
    return product_registry_by_name().get(canonical_name)


def get_product_lane(product_name: str | None) -> str | None:
    canonical_name = canonical_product_name(product_name)
    if not canonical_name:
        return None
    return product_lane_map().get(canonical_name)


def product_display_name(product_name: str | None) -> str | None:
    product = get_product_registry(product_name)
    if not product:
        return product_name
    return str(product.get("display_name") or product["product_name"])


def get_source_metadata(source_id: str | None) -> dict[str, Any] | None:
    if not source_id:
        return None
    return source_registry_by_id().get(source_id)


def get_source_by_url(source_url: str | None) -> dict[str, Any] | None:
    if not source_url:
        return None
    return source_registry_by_url().get(source_url)


def product_primary_link(product_name: str | None) -> str | None:
    product = get_product_registry(product_name)
    if not product:
        return None

    source_ids = product.get("source_priority") or product.get("canonical_sources") or []
    for source_ref in source_ids:
        source = get_source_metadata(source_ref) or get_source_by_url(source_ref)
        if source and source.get("url"):
            return str(source["url"])

    sources = source_registry_by_product().get(product["product_name"], [])
    for source in sources:
        if source.get("url"):
            return str(source["url"])
    return None


def list_products_by_category(category: str) -> list[dict[str, Any]]:
    normalized_category = category.strip().lower()
    return [
        product
        for product in load_product_registry()
        if str(product.get("category", "")).strip().lower() == normalized_category
    ]


def detect_products_in_text(text: str) -> list[str]:
    normalized = _normalize_text(text)
    query_tokens = set(normalized.split())
    matches: list[str] = []
    for alias, canonical_name in product_alias_map().items():
        if not alias:
            continue
        alias_hit = (
            alias in normalized
            if " " in alias
            else alias in query_tokens
        )
        if alias_hit and canonical_name not in matches:
            matches.append(canonical_name)
    return matches


def source_registry_by_lane() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in load_source_registry():
        lane = _coalesce_str(item.get("lane"))
        if not lane and item.get("product_name"):
            lane = get_product_lane(item.get("product_name"))
        if not lane:
            continue
        grouped.setdefault(lane, []).append(item)
    for lane, sources in grouped.items():
        grouped[lane] = sorted(
            sources,
            key=lambda source: int(source.get("priority") or 50),
            reverse=True,
        )
    return grouped


def product_signal_terms(product_name: str | None) -> list[str]:
    product = get_product_registry(product_name)
    if not product:
        return []
    return _merge_unique_strings(
        product.get("aliases", []),
        product.get("retrieval_keywords", []),
        product.get("best_for", []),
        product.get("who_is_it_for", []),
        product.get("key_features", []),
        [product.get("summary", ""), product.get("lane", ""), product.get("category", "")],
    )


def lane_signal_terms(lane: str | None) -> list[str]:
    if not lane:
        return []
    details = lane_catalog().get(lane, {})
    source_tags = []
    for source in source_registry_by_lane().get(lane, []):
        source_tags = _merge_unique_strings(
            source_tags,
            source.get("tags", []),
            source.get("recommended_use", []),
            source.get("evidence_highlights", []),
            [source.get("title", ""), source.get("page_type", "")],
        )
    return _merge_unique_strings(
        details.get("keywords", []),
        source_tags,
        [lane.replace("_", " ")],
    )


def detect_lanes_in_text(text: str) -> dict[str, int]:
    normalized = _normalize_text(text)
    query_tokens = set(normalized.split())
    scores: dict[str, int] = {}
    for lane in lane_catalog():
        lane_terms = lane_signal_terms(lane)
        hits = 0
        for keyword in lane_terms:
            normalized_keyword = _normalize_text(keyword)
            compact_keyword = normalized_keyword.replace(" ", "")
            if len(compact_keyword) < 4:
                continue
            if (" " in normalized_keyword and normalized_keyword in normalized) or compact_keyword in query_tokens:
                hits += 1
        if hits:
            scores[lane] = hits
    return scores


def product_registry_context(product_names: list[str]) -> str:
    blocks: list[str] = []
    for product_name in product_names:
        product = get_product_registry(product_name)
        if not product:
            continue
        sources = canonical_sources_for_product(product_name, include_download_links=False)[:3]
        source_labels = ", ".join(source.get("title", "") for source in sources if source.get("title"))
        blocks.append(
            "\n".join(
                [
                    f"Product: {product_display_name(product_name)}",
                    f"Lane: {product.get('lane', '')}",
                    f"Summary: {product.get('summary', '')}",
                    f"Best for: {', '.join(product.get('best_for', [])[:4]) or 'General ET users'}",
                    f"Keywords: {', '.join(product_signal_terms(product_name)[:8]) or 'None'}",
                    f"Source priorities: {', '.join(product.get('source_priority', [])[:4]) or 'Not specified'}",
                    f"Representative sources: {source_labels or 'No direct sources loaded'}",
                    f"Verification status: {product.get('verification_status', 'unknown')}",
                ]
            )
        )
    return "\n\n".join(blocks)


def canonical_sources_for_product(
    product_name: str,
    *,
    include_download_links: bool = True,
) -> list[dict[str, Any]]:
    product = get_product_registry(product_name)
    if not product:
        return []

    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    refs = product.get("source_priority") or product.get("canonical_sources") or []
    for ref in refs:
        source = get_source_metadata(ref) or get_source_by_url(ref)
        if source and source.get("url") and source["url"] not in seen:
            if not include_download_links and source.get("page_type") in {"app_store_listing", "download", "app_download"}:
                continue
            seen.add(source["url"])
            citations.append(source)

    for source in source_registry_by_product().get(product["product_name"], []):
        url = source.get("url")
        if not url or url in seen:
            continue
        if not include_download_links and source.get("page_type") in {"app_store_listing", "download", "app_download"}:
            continue
        seen.add(url)
        citations.append(source)
    return citations


def load_policy_query_modes() -> dict[str, dict[str, Any]]:
    return dict(load_router_behavior_policy().get("query_modes", {}))


def load_nonprime_product_defaults() -> dict[str, Any]:
    payload = _read_json_if_exists(NONPRIME_PRODUCT_PACK_PATH)
    if isinstance(payload, dict):
        return payload.get("router_defaults", {})
    return {}


def _query_tokens(query: str) -> set[str]:
    return set(_normalize_text(query).split())


def _has_any_phrase(normalized_query: str, phrases: list[str]) -> bool:
    return any(_normalize_text(phrase) in normalized_query for phrase in phrases if phrase)


def _generic_flags(normalized_query: str) -> dict[str, bool]:
    direct_patterns = [
        "what is",
        "what are",
        "what does",
        "tell me about",
        "show me",
        "give me",
        "explain",
        "list",
        "summarize",
        "compare",
        "difference between",
        "does ",
        "can you tell me",
    ]
    personalization_patterns = [
        "for me",
        "fit me",
        "fits me",
        "my path",
        "where should i start",
        "best place to begin",
        "which et product",
        "what et product",
        "what should i use",
        "recommend",
    ]
    broad_overview_patterns = [
        "all products",
        "all services",
        "what services do you offer",
        "what services do u offer",
        "what do you offer",
        "what do u offer",
        "what can you do",
        "what can u do",
        "tell me all",
        "et ecosystem",
        "beyond articles",
    ]
    news_patterns = [
        "news",
        "headlines",
        "current affairs",
        "world affairs",
        "global news",
        "international updates",
        "latest news",
        "today",
        "just give me the news",
    ]
    greeting_patterns = ["hi", "hello", "hola", "hey", "good morning", "good evening"]

    greeting_only = normalized_query in greeting_patterns or (
        len(normalized_query.split()) <= 4 and any(normalized_query.startswith(term) for term in greeting_patterns)
    )

    return {
        "direct_ask": _has_any_phrase(normalized_query, direct_patterns) or "?" in normalized_query,
        "wants_bullets": _has_any_phrase(normalized_query, ["bullet", "bullets", "points", "list"]),
        "wants_table": _has_any_phrase(normalized_query, ["table", "compare", "comparison", " vs "]),
        "wants_roadmap": _has_any_phrase(
            normalized_query,
            ["roadmap", "journey", "plan", "timeline", "week by week", "5 day", "7 day", "2 month", "2-month"],
        ),
        "wants_personalization": _has_any_phrase(normalized_query, personalization_patterns),
        "broad_overview": _has_any_phrase(normalized_query, broad_overview_patterns),
        "news_language": _has_any_phrase(normalized_query, news_patterns),
        "wants_brief": _has_any_phrase(normalized_query, ["short answer", "brief", "concise", "in short"]),
        "wants_deep": _has_any_phrase(normalized_query, ["detailed", "elaborate", "in detail", "deep dive"]),
        "greeting_only": greeting_only,
    }


def _generic_lane_boosts(normalized_query: str) -> dict[str, int]:
    boosts: dict[str, int] = {}
    generic_lane_terms = {
        "learning_and_upskilling": ["learn", "learning", "student", "course", "courses", "upskill", "education"],
        "events_and_community": ["event", "events", "summit", "conference", "community", "network"],
        "membership_benefits": ["benefit", "benefits", "redeem", "activate", "voucher", "membership"],
        "markets_and_tracking": ["market", "markets", "trading", "investing", "portfolio", "watchlist", "sensex", "nifty", "sip"],
        "world_news_current_affairs": ["world affairs", "current affairs", "global news", "international updates", "world news"],
        "policy_governance_public_sector": ["policy", "governance", "government", "public sector"],
        "marketing_advertising_media": ["marketing", "advertising", "brand", "media", "cmo"],
        "small_business_entrepreneurship": ["sme", "msme", "small business", "entrepreneur", "founder"],
    }
    for lane, phrases in generic_lane_terms.items():
        hits = sum(1 for phrase in phrases if phrase in normalized_query)
        if hits:
            boosts[lane] = hits
    return boosts


def _lane_intent(lane: str | None, query_mode: str, *, wants_table: bool, wants_roadmap: bool, broad_overview: bool) -> str:
    if query_mode == "chitchat":
        return "chitchat"
    if lane in {"markets_and_tracking", "live_video_business_news"}:
        return "markets"
    if lane in {"learning_and_upskilling"}:
        return "learning"
    if lane in {"events_and_community"}:
        return "events"
    if lane in {"membership_benefits"}:
        return "benefits"
    if lane in {"world_news_current_affairs"} or query_mode == "news_mode":
        return "news"
    if wants_table:
        return "comparison"
    if wants_roadmap:
        return "roadmap"
    if broad_overview or query_mode == "concierge_mode":
        return "discovery"
    return "product_explanation"


def _product_term_hits(
    *,
    normalized_query: str,
    query_tokens: set[str],
    terms: list[str],
) -> int:
    hits = 0
    for term in terms:
        normalized_term = _normalize_text(term)
        compact_term = normalized_term.replace(" ", "")
        if len(compact_term) < 4:
            continue
        if " " in normalized_term:
            if normalized_term in normalized_query:
                hits += 2
        elif compact_term in query_tokens:
            hits += 1
    return hits


def _widget_for_analysis(
    analysis: dict[str, Any],
    *,
    primary_product: str | None = None,
    verification_notes: list[str] | None = None,
) -> str | None:
    lane = get_product_lane(primary_product) or analysis.get("top_lane")
    verification_notes = verification_notes or []

    if verification_notes:
        return "trust_signal"
    if analysis.get("query_mode") == "news_mode":
        return None
    if analysis.get("requires_live_context") and lane in {"markets_and_tracking", "live_video_business_news"}:
        if any(term in analysis.get("normalized_query", "") for term in ["portfolio", "holdings", "sip", "alerts", "watchlist"]):
            return "portfolio_view"
        return "markets_tools"
    if lane == "learning_and_upskilling" and analysis.get("depth_mode") != "brief":
        return "learning_lane"
    if lane == "events_and_community" and analysis.get("depth_mode") != "brief":
        return "events_network"
    if lane == "membership_benefits":
        return "trust_signal"
    if analysis.get("broad_overview") or analysis.get("query_mode") == "concierge_mode":
        return "ecosystem_map"
    return None


def analyze_query(
    query: str,
    user_profile: dict[str, Any] | None = None,
    journey_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    user_profile = user_profile or {}
    normalized = _normalize_text(query)
    explicit_products = detect_products_in_text(query)
    lane_scores = detect_lanes_in_text(query)
    for lane, boost in _generic_lane_boosts(normalized).items():
        lane_scores[lane] = lane_scores.get(lane, 0) + boost
    matched_lanes = [lane for lane, _ in sorted(lane_scores.items(), key=lambda item: item[1], reverse=True)]
    flags = _generic_flags(normalized)
    policy = load_router_behavior_policy()

    news_mode = flags["news_language"] or "world_news_current_affairs" in matched_lanes
    concierge_mode = flags["wants_personalization"] or (
        flags["broad_overview"] and any(token in normalized for token in [" me", " my ", " i "])
    )

    if news_mode:
        query_mode = "news_mode"
    elif concierge_mode:
        query_mode = "concierge_mode"
    elif flags["greeting_only"] and not explicit_products and not matched_lanes:
        query_mode = "chitchat"
    else:
        query_mode = "information_mode"

    top_lane = matched_lanes[0] if matched_lanes else None
    primary_intent = _lane_intent(
        top_lane,
        query_mode,
        wants_table=flags["wants_table"],
        wants_roadmap=flags["wants_roadmap"],
        broad_overview=flags["broad_overview"],
    )

    if flags["wants_deep"] or flags["wants_roadmap"]:
        depth_mode = "deep"
    elif flags["wants_brief"]:
        depth_mode = "brief"
    elif flags["broad_overview"]:
        depth_mode = "overview"
    else:
        depth_mode = "standard"

    requires_live_context = bool(
        top_lane in {"markets_and_tracking", "live_video_business_news"}
        and _has_any_phrase(
            normalized,
            ["live", "today", "snapshot", "sensex", "nifty", "market mood", "tracker", "watchlist", "portfolio", "alerts"],
        )
    )
    secondary_intents: list[str] = []
    if flags["wants_table"]:
        secondary_intents.append("comparison")
    if flags["wants_bullets"]:
        secondary_intents.append("bullets")
    if flags["wants_roadmap"]:
        secondary_intents.append("roadmap")
    if requires_live_context:
        secondary_intents.append("live_context")

    tone_mode = (
        "beginner_guide"
        if user_profile.get("profession") == "student" or user_profile.get("sophistication") == "beginner"
        else "friendly_professional"
    )

    return {
        "normalized_query": normalized,
        "explicit_products": explicit_products,
        "matched_lanes": matched_lanes,
        "lane_scores": lane_scores,
        "top_lane": top_lane,
        "query_mode": query_mode,
        "profiling_allowed": bool(load_policy_query_modes().get(query_mode, {}).get("profiling_allowed", query_mode == "concierge_mode")),
        "primary_intent": primary_intent,
        "secondary_intents": secondary_intents,
        "concierge_request": concierge_mode,
        "broad_overview": flags["broad_overview"],
        "requires_bullets": flags["wants_bullets"],
        "requires_table": flags["wants_table"],
        "requires_roadmap": flags["wants_roadmap"],
        "requires_live_context": requires_live_context,
        "depth_mode": depth_mode,
        "tone_mode": tone_mode,
        "should_answer_directly": query_mode in {"information_mode", "news_mode"} or bool(explicit_products),
        "policy": policy,
        "anti_bias_rules": load_router_anti_bias_rules(),
        "format_rules": load_router_format_rules(),
    }


def _profile_signal_terms(user_profile: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ["intent", "goal", "profession", "sophistication"]:
        value = user_profile.get(key)
        if isinstance(value, str) and value.strip():
            terms.append(value.replace("_", " "))
    for value in user_profile.get("interests", []) or []:
        if isinstance(value, str) and value.strip():
            terms.append(value.replace("_", " "))
    return terms


def score_products_for_query(
    query: str,
    user_profile: dict[str, Any] | None = None,
    journey_history: list[dict[str, Any]] | None = None,
    analysis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    user_profile = user_profile or {}
    journey_history = journey_history or []
    analysis = analysis or analyze_query(query, user_profile=user_profile, journey_history=journey_history)
    normalized_query = analysis["normalized_query"]
    query_tokens = _query_tokens(query)
    broad_default_entry = canonical_product_name(load_nonprime_product_defaults().get("broad_default_entry")) or "ET Prime"

    recent_products = {
        canonical_product_name(product_name)
        for event in journey_history[-4:]
        for product_name in (event.get("recommended_products") or event.get("recommendations") or [])
        if canonical_product_name(product_name)
    }

    profile_terms = _profile_signal_terms(user_profile)
    anti_bias_targets = _policy_anti_bias_targets()
    scored: list[dict[str, Any]] = []

    for product in load_product_registry():
        product_name = product["product_name"]
        lane = str(product.get("lane") or "")
        reasons: list[str] = []
        score = 0

        if product_name in analysis["explicit_products"]:
            score += 18
            reasons.append("explicitly named by the user")

        alias_hits = _product_term_hits(
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            terms=product.get("aliases", []),
        )
        if alias_hits:
            score += alias_hits * 4
            reasons.append("alias match")

        keyword_hits = _product_term_hits(
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            terms=product.get("retrieval_keywords", []),
        )
        if keyword_hits:
            score += min(keyword_hits, 4) * 2
            reasons.append("query topics match this ET lane")

        audience_hits = _product_term_hits(
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            terms=product.get("best_for", []) + product.get("who_is_it_for", []),
        )
        if audience_hits:
            score += min(audience_hits, 3) * 2
            reasons.append("audience fit")

        lane_score = int(analysis["lane_scores"].get(lane, 0))
        if lane_score:
            score += lane_score * 4
            reasons.append("lane-level match")

        source_hits = _product_term_hits(
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            terms=[
                term
                for source in source_registry_by_product().get(product_name, [])[:6]
                for term in source.get("tags", []) + source.get("recommended_use", [])
            ],
        )
        if source_hits:
            score += min(source_hits, 4)
            reasons.append("source metadata match")

        profile_hits = _product_term_hits(
            normalized_query=" ".join(profile_terms),
            query_tokens=_query_tokens(" ".join(profile_terms)),
            terms=product_signal_terms(product_name),
        )
        if profile_hits:
            score += min(profile_hits, 3)
            reasons.append("profile match")

        if product_name in recent_products:
            score += 1
            reasons.append("conversation memory")

        if product_name == broad_default_entry:
            if analysis["query_mode"] == "concierge_mode" and not analysis["explicit_products"] and not analysis["top_lane"]:
                score += 4
                reasons.append("broad concierge entry point")
            elif analysis["broad_overview"] and not analysis["explicit_products"]:
                score += 3
                reasons.append("broad ET overview entry")
            elif analysis["query_mode"] in {"information_mode", "news_mode"} and (
                analysis["explicit_products"] or analysis["top_lane"]
            ):
                score -= 7
            elif analysis["query_mode"] != "concierge_mode" and analysis["top_lane"] and lane != analysis["top_lane"]:
                score -= 5

            if analysis["query_mode"] != "concierge_mode":
                for target in anti_bias_targets:
                    rule_products = set(target["products"])
                    rule_lanes = set(target["lanes"])
                    explicit_product_match = bool(rule_products.intersection(analysis["explicit_products"]))
                    lane_match = bool(rule_lanes.intersection(analysis.get("matched_lanes", [])))
                    if explicit_product_match or lane_match:
                        score -= 6
                        reasons.append("policy anti-bias rule")
                        break
        elif analysis["query_mode"] == "news_mode" and lane in {"world_news_current_affairs", "live_video_business_news"}:
            score += 5
            reasons.append("news-mode lane fit")

        if analysis["requires_live_context"] and lane in {"markets_and_tracking", "live_video_business_news"}:
            score += 3
            reasons.append("live market context requested")

        if product.get("reason_not_to_route_to_prime") and product_name != broad_default_entry and product_name in analysis["explicit_products"]:
            score += 2
            reasons.append("explicit product should outrank a broad fallback")

        if score > 0:
            scored.append(
                {
                    "product": product_name,
                    "display_product": product_display_name(product_name) or product_name,
                    "lane": lane,
                    "score": score,
                    "reasons": list(dict.fromkeys(reasons))[:3] or ["relevant ET match"],
                    "primary_link": product_primary_link(product_name),
                }
            )

    scored.sort(key=lambda item: (item["score"], item["product"] != broad_default_entry), reverse=True)
    return scored


def route_user_intent_to_products(
    query: str,
    user_profile: dict[str, Any],
    journey_history: list[dict[str, Any]] | None = None,
    analysis: dict[str, Any] | None = None,
) -> list[str]:
    analysis = analysis or analyze_query(query, user_profile=user_profile, journey_history=journey_history or [])
    scored = score_products_for_query(
        query,
        user_profile=user_profile,
        journey_history=journey_history or [],
        analysis=analysis,
    )
    if not scored:
        broad_default = canonical_product_name(load_nonprime_product_defaults().get("broad_default_entry")) or "ET Prime"
        if analysis.get("query_mode") == "concierge_mode" or analysis.get("broad_overview"):
            return [broad_default]
        return []
    limit = 8 if analysis.get("broad_overview") else 4
    return [item["product"] for item in scored[:limit]]


def select_visual_hint(
    query: str,
    product_names: list[str],
    *,
    user_profile: dict[str, Any] | None = None,
    journey_history: list[dict[str, Any]] | None = None,
    verification_notes: list[str] | None = None,
) -> str | None:
    analysis = analyze_query(query, user_profile=user_profile or {}, journey_history=journey_history or [])
    primary_product = product_names[0] if product_names else None
    return _widget_for_analysis(
        analysis,
        primary_product=primary_product,
        verification_notes=verification_notes,
    )


def build_verification_notes(query: str, product_names: list[str]) -> list[str]:
    normalized_query = _normalize_text(query)
    notes: list[str] = []
    seen: set[str] = set()

    asks_price_or_trial = _has_any_phrase(normalized_query, ["trial", "pricing", "price", "offer", "discount"])
    asks_activation = _has_any_phrase(normalized_query, ["benefit", "benefits", "activate", "redeem", "voucher"])
    asks_uncertainty = _has_any_phrase(normalized_query, ["verify", "uncertain", "mixed signals", "latest live page"])

    for product_name in product_names:
        product = get_product_registry(product_name)
        if not product:
            continue

        sources = canonical_sources_for_product(product_name)
        has_conflict = any(
            str(source.get("verification_status")) == "conflicting_public_signals"
            for source in sources
        )

        message = None
        if asks_price_or_trial and has_conflict:
            message = (
                "Public ET pages can show mixed live signals for pricing or trial details. Verify the latest live ET page or checkout before treating a pricing detail as final."
            )
        elif asks_activation and product.get("lane") == "membership_benefits":
            message = (
                "Some ET member benefits can have activation or eligibility constraints, so the exact live ET page should be checked before activation."
            )
        elif asks_uncertainty and has_conflict:
            message = (
                "Current public ET pages show mixed signals here, so the latest live ET source should be treated as the final confirmation."
            )

        if message and message not in seen:
            seen.add(message)
            notes.append(message)

    return notes
