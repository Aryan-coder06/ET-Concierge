from typing import Any, Literal, TypedDict


class UserProfile(TypedDict):
    name: str | None
    intent: str | None
    sophistication: str | None
    goal: str | None
    profession: str | None
    interests: list[str]
    existing_products: list[str]
    age_range: str | None


class JourneyEvent(TypedDict):
    timestamp: str
    route: str
    user_message: str
    assistant_message: str
    recommendations: list[str]
    recommended_products: list[str]
    sources: list[dict[str, str | None]]
    source_citations: list[dict[str, str | None]]
    verification_notes: list[str]
    navigator_summary: dict[str, Any] | None
    roadmap: dict[str, Any] | None
    chips: list[str]
    visual_hint: str | None
    profile_snapshot: UserProfile


class AgentState(TypedDict):
    session_id: str
    messages: list[dict[str, str]]
    current_message: str
    profile: UserProfile
    onboarding_complete: bool
    questions_asked: list[str]
    journey_history: list[JourneyEvent]
    intent: Literal["profiling", "product_query", "chitchat"]
    retrieved_chunks: list[Any]
    response: dict[str, Any]


REQUIRED_PROFILE_FIELDS = ("intent", "sophistication", "goal", "profession")


def empty_profile() -> UserProfile:
    return {
        "name": None,
        "intent": None,
        "sophistication": None,
        "goal": None,
        "profession": None,
        "interests": [],
        "existing_products": [],
        "age_range": None,
    }


def merge_profile(saved_profile: dict[str, Any] | None) -> UserProfile:
    profile = empty_profile()
    if not saved_profile:
        return profile

    for key in profile:
        value = saved_profile.get(key)
        if key in {"interests", "existing_products"}:
            profile[key] = list(value) if isinstance(value, list) else []
        else:
            profile[key] = value

    return profile


def initial_state(
    session_id: str,
    saved_session: dict[str, Any] | None = None,
) -> AgentState:
    saved_session = saved_session or {}
    profile = merge_profile(saved_session.get("profile"))
    onboarding_complete = all(profile.get(field) for field in REQUIRED_PROFILE_FIELDS)

    return {
        "session_id": session_id,
        "current_message": "",
        "profile": profile,
        "onboarding_complete": onboarding_complete,
        "messages": list(saved_session.get("messages", [])),
        "questions_asked": list(saved_session.get("questions_asked", [])),
        "journey_history": list(saved_session.get("journey_history", [])),
        "retrieved_chunks": [],
        "intent": "profiling",
        "response": {},
    }
