# state.py
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph

class UserProfile(TypedDict):
    intent: Optional[str]           # "investing" | "news" | "business" | None
    sophistication: Optional[str]   # "beginner" | "intermediate" | "advanced"
    goal: Optional[str]             # "wealth_building" | "trading" | "learning"
    profession: Optional[str]       # "salaried" | "founder" | "student"
    interests: list[str]            # ["mutual_funds", "startups", ...]
    existing_products: list[str]    # ["etprime", "etmoney", ...]
    age_range: Optional[str]        # "18-24" | "25-35" | "35-50" | "50+"

class AgentState(TypedDict):
    # ── Core conversation ─────────────────────────────
    session_id: str
    messages: list[dict]            # full conversation history
    current_message: str            # latest user message
    
    # ── Profile ───────────────────────────────────────
    profile: UserProfile
    onboarding_complete: bool
    questions_asked: list[str]      # track which questions already asked
    
    # ── Routing ───────────────────────────────────────
    intent: Literal[
        "profiling",        # user answering a profile question
        "product_query",    # asking about ET products
        "chitchat"          # general conversation
    ]
    
    # ── RAG results ───────────────────────────────────
    retrieved_chunks: list[dict]    # what came back from MongoDB
    
    # ── Output ────────────────────────────────────────
    response: dict                  # final structured response to frontend