import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymongo import UpdateOne

from .config import get_settings
from .db import get_knowledge_collection, get_persona_collection
from .registry import (
    canonical_product_name,
    get_source_by_url,
    load_bootstrap_chunks,
    load_product_registry,
    load_source_registry,
    source_registry_by_id,
)
from .retriever_service import get_embeddings


SUPPORTED_KINDS = {"knowledge", "persona"}


def _iter_source_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]

    return sorted(
        path
        for path in input_path.rglob("*")
        if path.suffix.lower() in {".json", ".jsonl"}
    )


def _load_records_from_file(file_path: Path) -> list[dict[str, Any]]:
    if file_path.suffix.lower() == ".jsonl":
        records: list[dict[str, Any]] = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return [payload]


def load_source_records(input_path: str | Path) -> list[dict[str, Any]]:
    base_path = Path(input_path)
    files = _iter_source_files(base_path)
    records: list[dict[str, Any]] = []

    for file_path in files:
        records.extend(_load_records_from_file(file_path))

    return records


def _validate_record(record: dict[str, Any]) -> dict[str, Any]:
    kind = str(record.get("kind", "knowledge")).strip().lower()
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"Unsupported source kind '{kind}'.")

    source_id = str(record.get("source_id", "")).strip()
    text = str(record.get("text", "")).strip()
    if not source_id:
        raise ValueError("Every source record must include source_id.")
    if not text:
        raise ValueError(f"Source record '{source_id}' is missing text.")

    if kind == "knowledge" and not str(record.get("product_name", "")).strip():
        raise ValueError(f"Knowledge record '{source_id}' is missing product_name.")

    normalized = dict(record)
    normalized["kind"] = kind
    normalized["source_id"] = source_id
    normalized["text"] = text
    normalized["title"] = str(record.get("title", source_id)).strip()
    normalized["url"] = str(record.get("url", "")).strip() or None
    return normalized


def _splitter_for(kind: str) -> RecursiveCharacterTextSplitter:
    settings = get_settings()
    if kind == "persona":
        chunk_size = settings.persona_chunk_size
        chunk_overlap = settings.persona_chunk_overlap
    else:
        chunk_size = settings.knowledge_chunk_size
        chunk_overlap = settings.knowledge_chunk_overlap

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )


def _base_document(record: dict[str, Any], chunk: str, chunk_index: int, total_chunks: int) -> dict[str, Any]:
    return {
        "_id": f"{record['source_id']}::chunk::{chunk_index}",
        "source_id": record["source_id"],
        "title": record["title"],
        "source_url": record.get("url"),
        "text": chunk.strip(),
        "chunk_index": chunk_index,
        "chunk_total": total_chunks,
        "ingested_at": datetime.now(timezone.utc),
    }


def _knowledge_document(record: dict[str, Any], chunk: str, chunk_index: int, total_chunks: int) -> dict[str, Any]:
    return {
        **_base_document(record, chunk, chunk_index, total_chunks),
        "collection": record.get("collection", "product_cards"),
        "product_name": record["product_name"],
        "product_area": record.get("product_area"),
        "category": record.get("category", "general"),
        "intent_tags": list(record.get("intent_tags", [])),
        "personas": list(record.get("personas", [])),
        "priority": int(record.get("priority", 1)),
        "tags": list(record.get("tags", [])),
        "page_type": record.get("page_type"),
        "source_tier": record.get("source_tier"),
        "source_of_truth": bool(record.get("source_of_truth", False)),
        "verification_status": record.get("verification_status"),
        "last_verified_at": record.get("last_verified_at"),
        "notes": record.get("notes"),
        "recommended_use": list(record.get("recommended_use", [])),
        "evidence_highlights": list(record.get("evidence_highlights", [])),
        "source_urls": list(record.get("source_urls", [])),
    }


def _persona_document(record: dict[str, Any], chunk: str, chunk_index: int, total_chunks: int) -> dict[str, Any]:
    return {
        **_base_document(record, chunk, chunk_index, total_chunks),
        "type": record.get("type", "persona_journey"),
        "goal": record.get("goal"),
        "profession": record.get("profession"),
        "sophistication": record.get("sophistication"),
        "journey_steps": list(record.get("journey_steps", [])),
        "avoid": list(record.get("avoid", [])),
        "tags": list(record.get("tags", [])),
    }


def prepare_documents(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    knowledge_documents: list[dict[str, Any]] = []
    persona_documents: list[dict[str, Any]] = []

    for raw_record in records:
        record = _validate_record(raw_record)
        splitter = _splitter_for(record["kind"])
        chunks = splitter.split_text(record["text"])
        if not chunks:
            continue

        for chunk_index, chunk in enumerate(chunks):
            if record["kind"] == "knowledge":
                knowledge_documents.append(
                    _knowledge_document(record, chunk, chunk_index, len(chunks))
                )
            else:
                persona_documents.append(
                    _persona_document(record, chunk, chunk_index, len(chunks))
                )

    return knowledge_documents, persona_documents


def _embed_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not documents:
        return []

    embeddings = get_embeddings().embed_documents([document["text"] for document in documents])
    for document, embedding in zip(documents, embeddings, strict=True):
        document["embedding"] = embedding
    return documents


def _clear_existing_sources(collection, source_ids: list[str]) -> None:
    if source_ids:
        collection.delete_many({"source_id": {"$in": source_ids}})


def _bulk_upsert(collection, documents: list[dict[str, Any]]) -> int:
    if not documents:
        return 0

    operations = [
        UpdateOne({"_id": document["_id"]}, {"$set": document}, upsert=True)
        for document in documents
    ]
    collection.bulk_write(operations, ordered=False)
    return len(documents)


def ingest_records(
    records: list[dict[str, Any]],
    *,
    clear_existing_source: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    knowledge_documents, persona_documents = prepare_documents(records)

    if dry_run:
        return {
            "knowledge_documents": len(knowledge_documents),
            "persona_documents": len(persona_documents),
            "dry_run": True,
        }

    knowledge_collection = get_knowledge_collection()
    persona_collection = get_persona_collection()

    if clear_existing_source:
        _clear_existing_sources(
            knowledge_collection,
            sorted({document["source_id"] for document in knowledge_documents}),
        )
        _clear_existing_sources(
            persona_collection,
            sorted({document["source_id"] for document in persona_documents}),
        )

    knowledge_documents = _embed_documents(knowledge_documents)
    persona_documents = _embed_documents(persona_documents)

    knowledge_count = _bulk_upsert(knowledge_collection, knowledge_documents)
    persona_count = _bulk_upsert(persona_collection, persona_documents)

    return {
        "knowledge_documents": knowledge_count,
        "persona_documents": persona_count,
        "dry_run": False,
    }


def ingest_from_path(
    input_path: str | Path,
    *,
    clear_existing_source: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    records = load_source_records(input_path)
    return ingest_records(
        records,
        clear_existing_source=clear_existing_source,
        dry_run=dry_run,
    )


def _canonical_product_from_area(product_area: str) -> str:
    return canonical_product_name(product_area) or product_area


def _normalize_html(html: str) -> str:
    trimmed = re.sub(
        r"(?is)<(script|style|noscript|svg|iframe).*?>.*?</\1>",
        " ",
        html,
    )
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", trimmed)
    description_match = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        trimmed,
    )
    preferred_blocks = re.findall(
        r"(?is)<(h1|h2|h3|p|li|title)[^>]*>(.*?)</\1>",
        trimmed,
    )

    text_parts: list[str] = []
    if title_match:
        text_parts.append(unescape(re.sub(r"<[^>]+>", " ", title_match.group(1))).strip())
    if description_match:
        text_parts.append(
            unescape(re.sub(r"<[^>]+>", " ", description_match.group(1))).strip()
        )

    if preferred_blocks:
        for _, block in preferred_blocks:
            cleaned = unescape(re.sub(r"<[^>]+>", " ", block))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned and cleaned not in text_parts:
                text_parts.append(cleaned)
    else:
        cleaned = unescape(re.sub(r"<[^>]+>", " ", trimmed))
        text_parts.append(re.sub(r"\s+", " ", cleaned).strip())

    merged = "\n".join(part for part in text_parts if part)
    return merged[:24000]


def fetch_live_source_text(
    source: dict[str, Any],
    *,
    timeout_seconds: int = 20,
) -> str:
    response = requests.get(
        source["url"],
        timeout=timeout_seconds,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; ET-Concierge/1.0; "
                "+https://economictimes.indiatimes.com/)"
            )
        },
    )
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    normalized = _normalize_html(response.text)
    if len(normalized) < 300:
        raise ValueError(
            f"Normalized text for {source['source_id']} was too short to trust."
        )
    return normalized


def build_live_source_records(
    *,
    limit: int | None = None,
    source_ids: list[str] | None = None,
    include_fallback_summary: bool = True,
) -> list[dict[str, Any]]:
    selected_sources = load_source_registry()
    if source_ids:
        source_id_set = set(source_ids)
        selected_sources = [
            source for source in selected_sources if source["source_id"] in source_id_set
        ]
    if limit is not None:
        selected_sources = selected_sources[:limit]

    def build_record(source: dict[str, Any]) -> dict[str, Any]:
        live_text = ""
        fetch_error = None
        try:
            live_text = fetch_live_source_text(source)
        except Exception as exc:
            fetch_error = exc

        summary_parts = [source["title"], source.get("notes", "")]
        summary_parts.extend(source.get("evidence_highlights", []))
        summary_parts.extend(source.get("recommended_use", []))
        fallback_text = "\n".join(part for part in summary_parts if part).strip()

        text = live_text.strip() if live_text else ""
        if include_fallback_summary and fallback_text:
            text = f"{fallback_text}\n\n{text}".strip()
        if not text:
            if fetch_error:
                raise RuntimeError(
                    f"Failed to build text for {source['source_id']}: {fetch_error}"
                ) from fetch_error
        return {
            "kind": "knowledge",
            "source_id": source["source_id"],
            "product_name": _canonical_product_from_area(source["product_area"]),
            "product_area": source["product_area"],
            "title": source["title"],
            "url": source["url"],
            "text": text,
            "category": source.get("page_type", "source_page"),
            "page_type": source.get("page_type"),
            "source_tier": source.get("source_tier"),
            "source_of_truth": source.get("source_of_truth"),
            "verification_status": source.get("verification_status"),
            "last_verified_at": source.get("last_verified_at"),
            "priority": 1 if source.get("source_of_truth") else 2,
            "tags": [
                source.get("product_area", ""),
                source.get("page_type", ""),
                source.get("verification_status", ""),
            ],
            "recommended_use": list(source.get("recommended_use", [])),
            "evidence_highlights": list(source.get("evidence_highlights", [])),
            "notes": source.get("notes"),
            "source_urls": [source["url"]],
        }

    if not selected_sources:
        return []

    ordered_records: list[dict[str, Any] | None] = [None] * len(selected_sources)
    worker_count = min(6, len(selected_sources))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(build_record, source): index
            for index, source in enumerate(selected_sources)
        }
        for future in as_completed(futures):
            ordered_records[futures[future]] = future.result()

    return [record for record in ordered_records if record is not None]


def build_bootstrap_chunk_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in load_bootstrap_chunks():
        linked_sources = [
            source["source_id"]
            for source_url in chunk.get("source_urls", [])
            if (source := get_source_by_url(source_url))
        ]
        records.append(
            {
                "kind": "knowledge",
                "source_id": f"bootstrap::{chunk['chunk_id']}",
                "product_name": chunk["product_name"],
                "product_area": chunk["product_name"],
                "title": chunk["title"],
                "url": chunk.get("source_urls", [None])[0],
                "text": chunk["text"],
                "category": "bootstrap_chunk",
                "page_type": "bootstrap_chunk",
                "source_tier": "bootstrap",
                "source_of_truth": False,
                "verification_status": chunk.get("verification_status", "official_public"),
                "last_verified_at": None,
                "priority": 2,
                "tags": list(chunk.get("tags", [])),
                "recommended_use": [],
                "evidence_highlights": [],
                "notes": (
                    "Paraphrased bootstrap chunk from ET research pack. "
                    f"Linked sources: {', '.join(linked_sources) if linked_sources else 'none'}."
                ),
                "source_urls": list(chunk.get("source_urls", [])),
            }
        )
    return records


def build_product_registry_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    source_index = source_registry_by_id()

    for product in load_product_registry():
        canonical_sources = [
            source_index[source_id]["url"]
            for source_id in product.get("canonical_sources", [])
            if source_id in source_index
        ]
        pricing_text = [
            (
                f"{note.get('fact')}: "
                f"{note.get('details') or note.get('value')}"
            ).strip()
            for note in product.get("pricing_notes", [])
        ]
        text = "\n".join(
            part
            for part in [
                f"{product['product_name']}",
                product.get("summary", ""),
                (
                    "Who it is for: "
                    + ", ".join(product.get("who_is_it_for", []))
                )
                if product.get("who_is_it_for")
                else "",
                (
                    "Key features: "
                    + ", ".join(product.get("key_features", []))
                )
                if product.get("key_features")
                else "",
                (
                    "Benefits: "
                    + ", ".join(product.get("benefits", []))
                )
                if product.get("benefits")
                else "",
                (
                    "Platforms: "
                    + ", ".join(product.get("platforms", []))
                )
                if product.get("platforms")
                else "",
                (
                    "Pricing and access notes: "
                    + " | ".join(pricing_text)
                )
                if pricing_text
                else "",
                (
                    "Events or courses: "
                    + ", ".join(product.get("events_or_courses", []))
                )
                if product.get("events_or_courses")
                else "",
                (
                    "Partner or service types: "
                    + ", ".join(product.get("partner_or_service_types", []))
                )
                if product.get("partner_or_service_types")
                else "",
                (
                    "CTA labels: "
                    + ", ".join(product.get("cta_labels", []))
                )
                if product.get("cta_labels")
                else "",
            ]
            if part
        ).strip()

        records.append(
            {
                "kind": "knowledge",
                "source_id": f"registry::{product['product_name'].lower().replace(' ', '_')}",
                "product_name": product["product_name"],
                "product_area": product["product_name"],
                "title": f"{product['product_name']} Registry Summary",
                "url": canonical_sources[0] if canonical_sources else None,
                "text": text,
                "category": "product_registry",
                "page_type": "product_registry",
                "source_tier": "registry",
                "source_of_truth": True,
                "verification_status": product.get("verification_status"),
                "last_verified_at": product.get("last_verified_at"),
                "priority": 1,
                "tags": [
                    product.get("category", ""),
                    "product_registry",
                    product.get("verification_status", ""),
                ],
                "recommended_use": ["product_summary", "routing", "verification"],
                "evidence_highlights": [],
                "notes": "Structured ET product registry summary derived from the verified research pack.",
                "source_urls": canonical_sources,
            }
        )

    return records


def ingest_et_research_pack(
    *,
    include_live_sources: bool = True,
    include_bootstrap_chunks: bool = True,
    include_registry_records: bool = True,
    limit: int | None = None,
    clear_existing_source: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    if include_live_sources:
        records.extend(build_live_source_records(limit=limit))
    if include_bootstrap_chunks:
        records.extend(build_bootstrap_chunk_records())
    if include_registry_records:
        records.extend(build_product_registry_records())

    summary = ingest_records(
        records,
        clear_existing_source=clear_existing_source,
        dry_run=dry_run,
    )
    summary["live_source_records"] = (
        len(
            [
                record
                for record in records
                if record.get("source_tier") not in {"bootstrap", "registry"}
            ]
        )
    )
    summary["bootstrap_chunk_records"] = (
        len([record for record in records if record["source_id"].startswith("bootstrap::")])
    )
    summary["product_registry_records"] = (
        len([record for record in records if record["source_id"].startswith("registry::")])
    )
    return summary
