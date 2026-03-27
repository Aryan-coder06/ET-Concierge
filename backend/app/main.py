from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .chatbot.config import get_settings
from .chatbot.service import concierge_service


class SourceItem(BaseModel):
    label: str
    href: str | None = None


class SourceCitation(BaseModel):
    label: str
    href: str | None = None
    source_id: str | None = None
    verification_status: str | None = None
    page_type: str | None = None


class ChatRequest(BaseModel):
    query: str
    thread_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    session_id: str | None = None
    profile_update: dict[str, Any] | None = None
    recommendations: list[str] = Field(default_factory=list)
    recommended_products: list[str] = Field(default_factory=list)
    navigator_summary: dict[str, Any] | None = None
    roadmap: dict[str, Any] | None = None
    chips: list[str] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)
    visual_hint: str | None = None
    response_type: str = "product_query"


class SessionSummary(BaseModel):
    session_id: str
    title: str
    updated_at: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    onboarding_complete: bool = False
    response_type: str | None = None
    last_message: str | None = None
    last_route: str | None = None


class SessionDocumentResponse(BaseModel):
    session_id: str
    title: str
    profile: dict[str, Any] = Field(default_factory=dict)
    onboarding_complete: bool = False
    questions_asked: list[str] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    journey_history: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    recommended_products: list[str] = Field(default_factory=list)
    response_type: str | None = None
    updated_at: str | None = None


settings = get_settings()

app = FastAPI(title="ET Luna Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ET Luna FastAPI backend is running"}


@app.get("/health")
def health() -> dict[str, Any]:
    return concierge_service.health()


@app.get("/sessions", response_model=list[SessionSummary])
def list_sessions(limit: int = 25) -> list[SessionSummary]:
    return [SessionSummary(**item) for item in concierge_service.list_sessions(limit=limit)]


@app.get("/sessions/{session_id}", response_model=SessionDocumentResponse)
def get_session(session_id: str) -> SessionDocumentResponse:
    try:
        session = concierge_service.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SessionDocumentResponse(**session)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        result = concierge_service.chat(
            session_id=payload.thread_id,
            query=payload.query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The ET concierge pipeline failed to process this request.",
        ) from exc

    return ChatResponse(**result)
