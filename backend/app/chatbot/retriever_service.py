import logging
import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch

from .config import get_settings
from .db import get_knowledge_collection, get_persona_collection
from .registry import (
    canonical_product_name,
    detect_products_in_text,
    official_product_names,
    route_user_intent_to_products,
)


logger = logging.getLogger(__name__)

PRODUCT_QUERY_ALIASES = {
    "ET Prime": ["et prime", "etprime"],
    "ET Markets": ["et markets", "etmarkets"],
    "ET Portfolio": ["et portfolio", "portfolio"],
    "ET Wealth Edition": ["et wealth edition", "wealth edition"],
    "ET Print Edition": ["et print edition", "print edition", "epaper"],
    "ETMasterclass": ["et masterclass", "etmasterclass", "masterclass"],
    "ET Events": ["et events", "events"],
    "ET Partner Benefits": ["et benefits", "partner benefits", "times prime", "benefits"],
}

INTENT_HINTS = {
    "investing": [
        "invest",
        "investing",
        "trading",
        "stocks",
        "sip",
        "mutual fund",
        "portfolio",
    ],
    "news": ["news", "updates", "business news", "briefing", "policy"],
    "growing_business": ["startup", "founder", "brand", "marketing", "business growth", "sme"],
    "learning": ["learn", "learning", "masterclass", "course", "workshop", "certification"],
    "events": ["event", "events", "summit", "conference", "community", "register"],
}


def _mongo_doc_to_document(raw: dict) -> Document:
    metadata = {key: value for key, value in raw.items() if key not in {"text", "embedding"}}
    metadata["_id"] = str(metadata.get("_id", ""))
    return Document(page_content=raw.get("text", ""), metadata=metadata)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def _extract_query_signals(query: str, profile: dict) -> dict:
    normalized_query = _normalize_text(query)
    mentioned_products: list[str] = detect_products_in_text(query)
    topic_terms: list[str] = []
    intent_hints: list[str] = []

    for product_name, aliases in PRODUCT_QUERY_ALIASES.items():
        if any(alias in normalized_query for alias in aliases) and product_name not in mentioned_products:
            mentioned_products.append(product_name)

    for intent, keywords in INTENT_HINTS.items():
        if any(keyword in normalized_query for keyword in keywords):
            intent_hints.append(intent)
            topic_terms.extend(keyword for keyword in keywords if keyword in normalized_query)

    if profile.get("intent") and profile["intent"] not in intent_hints:
        intent_hints.append(profile["intent"])

    return {
        "normalized_query": normalized_query,
        "mentioned_products": mentioned_products,
        "intent_hints": intent_hints,
        "topic_terms": sorted(set(topic_terms)),
        "preferred_products": route_user_intent_to_products(query, profile),
    }


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    settings.require_external_services()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


@lru_cache(maxsize=1)
def get_product_store() -> MongoDBAtlasVectorSearch:
    settings = get_settings()
    return MongoDBAtlasVectorSearch(
        collection=get_knowledge_collection(),
        embedding=get_embeddings(),
        index_name=settings.vector_index_name,
        embedding_key="embedding",
        text_key="text",
    )


@lru_cache(maxsize=1)
def get_persona_store() -> MongoDBAtlasVectorSearch:
    settings = get_settings()
    return MongoDBAtlasVectorSearch(
        collection=get_persona_collection(),
        embedding=get_embeddings(),
        index_name=settings.vector_index_name,
        embedding_key="embedding",
        text_key="text",
    )


def _augmented_query(query: str, profile: dict) -> str:
    parts = [query]
    if profile.get("intent"):
        parts.append(f"User intent: {profile['intent']}")
    if profile.get("sophistication"):
        parts.append(f"User sophistication: {profile['sophistication']}")
    if profile.get("goal"):
        parts.append(f"User goal: {profile['goal']}")
    if profile.get("profession"):
        parts.append(f"User profession: {profile['profession']}")
    if profile.get("interests"):
        parts.append(f"User interests: {', '.join(profile['interests'])}")
    return "\n".join(parts)


def _query_variants(query: str, profile: dict, signals: dict) -> list[str]:
    variants = [query, _augmented_query(query, profile)]

    if signals["mentioned_products"]:
        variants.append(
            f"{query}\nFocus ET products: {', '.join(signals['mentioned_products'])}"
        )

    if signals["intent_hints"]:
        variants.append(
            f"{query}\nLikely ET intent: {', '.join(signals['intent_hints'])}"
        )

    if signals["topic_terms"]:
        variants.append(f"{query}\nTopics: {', '.join(signals['topic_terms'])}")

    unique: list[str] = []
    for variant in variants:
        if variant not in unique:
            unique.append(variant)

    return unique[:4]


def _dedupe_documents(documents: list[Document]) -> list[Document]:
    seen: set[str] = set()
    deduped: list[Document] = []

    for document in documents:
        doc_id = str(document.metadata.get("_id") or "")
        key = doc_id or f"{document.metadata.get('product_name', '')}:{document.page_content[:80]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(document)

    return deduped


def _score_product_document(document: Document, profile: dict, signals: dict) -> int:
    score = 0
    intent_tags = set(document.metadata.get("intent_tags") or [])
    personas = set(document.metadata.get("personas") or [])
    product_name = str(document.metadata.get("product_name", ""))
    canonical_name = canonical_product_name(product_name) or product_name
    query_products = set(profile.get("existing_products") or [])
    normalized_product_name = canonical_name.lower()
    page_content = document.page_content.lower()
    verification_status = str(document.metadata.get("verification_status") or "")
    source_tier = str(document.metadata.get("source_tier") or "")
    page_type = str(document.metadata.get("page_type") or "")

    if profile.get("intent") and profile["intent"] in intent_tags:
        score += 3
    if any(intent_hint in intent_tags for intent_hint in signals["intent_hints"]):
        score += 2
    if profile.get("profession") and profile["profession"] in personas:
        score += 2
    if canonical_name in signals["mentioned_products"]:
        score += 6
    if query_products and canonical_name in query_products:
        score += 1
    if canonical_name in signals.get("preferred_products", []):
        score += 4
    if signals["topic_terms"]:
        score += min(
            2,
            sum(1 for term in signals["topic_terms"] if term in page_content),
        )
    priority = document.metadata.get("priority")
    if isinstance(priority, int):
        score += max(0, 3 - min(priority, 3))
    if normalized_product_name and normalized_product_name in signals["normalized_query"]:
        score += 2
    if canonical_name in official_product_names():
        score += 2
    if verification_status == "official_public":
        score += 2
    elif verification_status == "conflicting_public_signals":
        if any(
            keyword in signals["normalized_query"]
            for keyword in ("trial", "pricing", "price", "offer")
        ):
            score += 1
        else:
            score -= 1
    if document.metadata.get("source_of_truth"):
        score += 2
    if source_tier == "primary":
        score += 1
    if page_type in {
        "faq",
        "about",
        "plans",
        "product_home",
        "tool_page",
        "benefits_portal",
        "events_portal",
        "edition_page",
    }:
        score += 1
    if canonical_name not in official_product_names() and not signals["mentioned_products"]:
        score -= 1

    return score


def _score_persona_document(document: Document, profile: dict, signals: dict) -> int:
    score = 0
    for field in ("goal", "profession", "sophistication"):
        if profile.get(field) and document.metadata.get(field) == profile[field]:
            score += 2
    if profile.get("intent") and profile["intent"] in signals["intent_hints"]:
        score += 1
    if signals["topic_terms"]:
        page_content = document.page_content.lower()
        score += min(
            2,
            sum(1 for term in signals["topic_terms"] if term in page_content),
        )
    return score


def _sort_documents(
    documents: list[Document],
    scorer,
    limit: int,
) -> list[Document]:
    scored = [(scorer(document), document) for document in documents]
    scored.sort(key=lambda item: item[0], reverse=True)
    ranked = [document for _, document in scored]
    return _dedupe_documents(ranked)[:limit]


def _keyword_fallback(
    *,
    collection_name: str,
    query: str,
    limit: int,
    signals: dict,
) -> list[Document]:
    collection = (
        get_knowledge_collection() if collection_name == "knowledge" else get_persona_collection()
    )
    tokens = [re.escape(token) for token in query.split() if len(token) > 2][:4]
    for product_name in signals["mentioned_products"]:
        tokens.extend(re.escape(alias) for alias in PRODUCT_QUERY_ALIASES.get(product_name, []))
    if not tokens:
        return []

    regex = "|".join(tokens)
    cursor = collection.find(
        {
            "$or": [
                {"text": {"$regex": regex, "$options": "i"}},
                {"product_name": {"$regex": regex, "$options": "i"}},
                {"title": {"$regex": regex, "$options": "i"}},
                {"source_id": {"$regex": regex, "$options": "i"}},
            ]
        },
        {"embedding": 0},
    ).limit(limit)

    return [_mongo_doc_to_document(raw) for raw in cursor]


def _vector_candidates(
    *,
    collection_name: str,
    variants: list[str],
    limit: int,
) -> list[Document]:
    store = get_product_store() if collection_name == "knowledge" else get_persona_store()
    all_documents: list[Document] = []

    for variant in variants:
        try:
            all_documents.extend(store.similarity_search(variant, k=limit))
        except Exception as exc:
            logger.warning("Vector search failed for variant '%s': %s", variant, exc)

    return _dedupe_documents(all_documents)


def get_product_chunks(query: str, profile: dict, k: int = 4) -> list[Document]:
    signals = _extract_query_signals(query, profile)
    vector_documents = _vector_candidates(
        collection_name="knowledge",
        variants=_query_variants(query, profile, signals),
        limit=max(k * 2, 6),
    )
    keyword_documents = _keyword_fallback(
        collection_name="knowledge",
        query=query,
        limit=max(k, 4),
        signals=signals,
    )
    documents = _dedupe_documents(vector_documents + keyword_documents)

    return _sort_documents(
        documents,
        lambda document: _score_product_document(document, profile, signals),
        k,
    )


def get_persona_chunks(query: str, profile: dict, k: int = 1) -> list[Document]:
    signals = _extract_query_signals(query, profile)
    vector_documents = _vector_candidates(
        collection_name="persona",
        variants=_query_variants(query, profile, signals),
        limit=max(k * 3, 3),
    )
    keyword_documents = _keyword_fallback(
        collection_name="persona",
        query=query,
        limit=max(k, 2),
        signals=signals,
    )
    documents = _dedupe_documents(vector_documents + keyword_documents)

    return _sort_documents(
        documents,
        lambda document: _score_persona_document(document, profile, signals),
        k,
    )
