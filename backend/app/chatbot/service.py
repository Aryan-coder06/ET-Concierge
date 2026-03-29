from typing import Any

from .config import get_settings
from .db import (
    build_state_from_session,
    get_database,
    list_session_summaries,
    load_session_document,
    ping_database,
    serialize_session_document,
)
from .graph import et_graph


class ConciergeService:
    def chat(self, *, session_id: str, query: str) -> dict[str, Any]:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query must not be empty.")
        if not session_id.strip():
            raise ValueError("thread_id must not be empty.")

        state = build_state_from_session(session_id)
        state["current_message"] = clean_query

        final_state = et_graph.invoke(state)
        response = final_state["response"]

        return {
            "answer": response["message"],
            "sources": response.get("sources", []),
            "source_citations": response.get("source_citations", []),
            "session_id": response.get("session_id", session_id),
            "profile_update": response.get("profile_update"),
            "recommendations": response.get("recommendations", []),
            "recommended_products": response.get(
                "recommended_products",
                response.get("recommendations", []),
            ),
            "navigator_summary": response.get("navigator_summary"),
            "roadmap": response.get("roadmap"),
            "chips": response.get("chips", []),
            "verification_notes": response.get("verification_notes", []),
            "visual_hint": response.get("visual_hint"),
            "response_type": response.get("response_type", "product_query"),
            "answer_style": response.get("answer_style"),
            "presentation": response.get("presentation"),
            "decision": response.get("decision"),
            "comparison_rows": response.get("comparison_rows", []),
            "bullet_groups": response.get("bullet_groups", []),
            "ui_modules": response.get("ui_modules", []),
            "path_snapshot": response.get("path_snapshot"),
            "html_snippets": response.get("html_snippets", []),
        }

    def health(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "status": "ok",
            "mongo_connected": ping_database(),
            "database": settings.mongodb_db_name,
            "collections": get_database().list_collection_names(),
            "chat_model_candidates": settings.chat_model_candidates,
            "embedding_model": settings.embedding_model,
        }

    def get_session(self, session_id: str) -> dict[str, Any]:
        document = load_session_document(session_id)
        if not document:
            raise ValueError(f"Session '{session_id}' was not found.")
        return serialize_session_document(document)

    def list_sessions(self, *, limit: int = 25) -> list[dict[str, Any]]:
        return list_session_summaries(limit=limit)


concierge_service = ConciergeService()
