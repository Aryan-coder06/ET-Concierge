from functools import lru_cache
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .config import get_settings
from .state import AgentState, initial_state


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    settings = get_settings()
    settings.require_external_services()
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )


@lru_cache(maxsize=1)
def get_database() -> Database:
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_db_name]


@lru_cache(maxsize=1)
def get_sessions_collection() -> Collection:
    settings = get_settings()
    collection = get_database()[settings.sessions_collection]
    collection.create_index("session_id", unique=True)
    return collection


@lru_cache(maxsize=1)
def get_knowledge_collection() -> Collection:
    settings = get_settings()
    return get_database()[settings.knowledge_collection]


@lru_cache(maxsize=1)
def get_persona_collection() -> Collection:
    settings = get_settings()
    return get_database()[settings.persona_collection]


def load_session_document(session_id: str) -> dict | None:
    return get_sessions_collection().find_one({"session_id": session_id})


def _serialize_datetime(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value if isinstance(value, str) else None


def serialize_session_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": document.get("session_id", ""),
        "title": document.get("title")
        or document.get("session_id", ""),
        "profile": document.get("profile", {}),
        "onboarding_complete": bool(document.get("onboarding_complete", False)),
        "questions_asked": list(document.get("questions_asked", [])),
        "messages": list(document.get("messages", [])),
        "journey_history": list(document.get("journey_history", [])),
        "recommendations": list(document.get("recommendations", [])),
        "recommended_products": list(
            document.get("recommended_products", document.get("recommendations", []))
        ),
        "response_type": document.get("response_type"),
        "updated_at": _serialize_datetime(document.get("updated_at")),
    }


def list_session_summaries(limit: int = 25) -> list[dict[str, Any]]:
    cursor = (
        get_sessions_collection()
        .find(
            {},
            {
                "_id": 0,
                "session_id": 1,
                "title": 1,
                "updated_at": 1,
                "profile": 1,
                "onboarding_complete": 1,
                "response_type": 1,
                "journey_history": {"$slice": -1},
                "messages": {"$slice": -1},
            },
        )
        .sort("updated_at", -1)
        .limit(limit)
    )

    summaries: list[dict[str, Any]] = []
    for document in cursor:
        last_message = None
        assistant_messages = [
            item.get("content")
            for item in document.get("messages", [])
            if item.get("role") == "assistant" and item.get("content")
        ]
        if assistant_messages:
            last_message = assistant_messages[-1]

        summaries.append(
            {
                "session_id": document.get("session_id", ""),
                "title": document.get("title")
                or document.get("session_id", ""),
                "updated_at": _serialize_datetime(document.get("updated_at")),
                "profile": document.get("profile", {}),
                "onboarding_complete": bool(
                    document.get("onboarding_complete", False)
                ),
                "response_type": document.get("response_type"),
                "last_message": last_message,
                "last_route": (
                    document.get("journey_history", [{}])[-1].get("route")
                    if document.get("journey_history")
                    else None
                ),
            }
        )

    return summaries


def build_state_from_session(session_id: str) -> AgentState:
    return initial_state(session_id, load_session_document(session_id))


def ping_database() -> bool:
    get_mongo_client().admin.command("ping")
    return True
