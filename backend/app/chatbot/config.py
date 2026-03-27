import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=False)


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return str(value).strip().strip("'").strip('"')


def _env_list(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    values = [item.strip() for item in raw_value.split(",")]
    return [item for item in values if item]


class Settings(BaseModel):
    google_api_key: str = Field(default_factory=lambda: _env("GOOGLE_API_KEY"))
    mongodb_uri: str = Field(default_factory=lambda: _env("MONGODB_URI"))
    embedding_model: str = Field(
        default_factory=lambda: _env("EMBEDDING_MODEL", "gemini-embedding-001")
    )
    google_chat_model: str = Field(
        default_factory=lambda: _env("GOOGLE_CHAT_MODEL")
    )
    mongodb_db_name: str = Field(
        default_factory=lambda: _env("MONGODB_DB_NAME", "et_concierge")
    )
    knowledge_collection: str = Field(
        default_factory=lambda: _env("MONGODB_KNOWLEDGE_COLLECTION", "knowledge_base")
    )
    persona_collection: str = Field(
        default_factory=lambda: _env("MONGODB_PERSONA_COLLECTION", "persona_base")
    )
    sessions_collection: str = Field(
        default_factory=lambda: _env("MONGODB_SESSIONS_COLLECTION", "sessions")
    )
    vector_index_name: str = Field(
        default_factory=lambda: _env("MONGODB_VECTOR_INDEX", "vector_index")
    )
    knowledge_chunk_size: int = Field(
        default_factory=lambda: int(_env("KNOWLEDGE_CHUNK_SIZE", "900"))
    )
    knowledge_chunk_overlap: int = Field(
        default_factory=lambda: int(_env("KNOWLEDGE_CHUNK_OVERLAP", "150"))
    )
    persona_chunk_size: int = Field(
        default_factory=lambda: int(_env("PERSONA_CHUNK_SIZE", "650"))
    )
    persona_chunk_overlap: int = Field(
        default_factory=lambda: int(_env("PERSONA_CHUNK_OVERLAP", "100"))
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: _env_list(
            "ALLOWED_ORIGINS",
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
    )

    @property
    def chat_model_candidates(self) -> list[str]:
        candidates = [
            self.google_chat_model,
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.0-flash-lite",
            "gemini-3-flash-preview",
        ]
        unique: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in unique:
                unique.append(candidate)
        return unique

    def require_external_services(self) -> None:
        if not self.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing in backend/.env.")
        if not self.mongodb_uri:
            raise RuntimeError("MONGODB_URI is missing in backend/.env.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
