import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from state import AgentState

load_dotenv()

# Initialize Gemini Client
# Using gemini-2.0-flash for speed and high context accuracy
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3
)

# ─────────────────────────────────────────────────────────
# NODE 1 — Profile Extractor
# ─────────────────────────────────────────────────────────
def profile_extractor_node(state: AgentState) -> AgentState:
    if state["onboarding_complete"]:
        return state
    
    extraction_prompt = f"""
    You are extracting user profile signals from a message.
    Current profile: {json.dumps(state["profile"])}
    User message: "{state["current_message"]}"

    Extract any NEW signals from the message. Only return fields 
    that are clearly inferable. Return JSON only, no explanation.

    Return format:
    {{
      "intent": "investing|news|business|null",
      "sophistication": "beginner|intermediate|advanced|null",
      "goal": "wealth_building|trading|learning|business_growth|null",
      "profession": "salaried|founder|student|retired|null",
      "interests": ["array of strings or empty array"],
      "existing_products": ["etprime|etmoney|etmarkets or empty"]
    }}

    Return null for fields you cannot infer. Never guess.
    """
    
    # Gemini Invoke
    response = llm.invoke([HumanMessage(content=extraction_prompt)])
    
    try:
        # Clean the response in case Gemini adds markdown code blocks
        content = response.content
        if isinstance(content, list):
            # If Gemini returns a list of content blocks, grab the text from the first one
            content = content[0].get("text", "")
        clean_content = str(content).replace("```json", "").replace("```", "").strip()
        extracted = json.loads(clean_content)

    except Exception as e:
        print(f"Extraction Error: {e}")
        extracted = {}

    profile = state["profile"]
    for key, value in extracted.items():
        if value is not None and value != [] and value != "null":
            if key == "interests":
                profile["interests"] = list(set(profile.get("interests", []) + value))
            elif key == "existing_products":
                profile["existing_products"] = list(set(profile.get("existing_products", []) + value))
            else:
                profile[key] = value
    
    required = ["intent", "sophistication", "goal", "profession"]
    onboarding_complete = all(profile.get(field) not in [None, "null"] for field in required)
    
    return {**state, "profile": profile, "onboarding_complete": onboarding_complete}


# ─────────────────────────────────────────────────────────
# NODE 2 — Router
# ─────────────────────────────────────────────────────────
def router_node(state: AgentState) -> AgentState:
    # If onboarding not done, always route to profiling
    if not state["onboarding_complete"]:
        return {**state, "intent": "profiling"}
    
    routing_prompt = f"""
    Classify this user message into exactly one category.
    Message: "{state["current_message"]}"

    Categories:
    - "product_query": asking about ET products, features, pricing, recommendations
    - "chitchat": greetings, thanks, general questions

    Return JSON only: {{"intent": "product_query|chitchat"}}
    """
    
    response = llm.invoke([HumanMessage(content=routing_prompt)])
    
    # 🟢 THE FIX: Handle the list/dict format before calling .replace()
    content = response.content
    if isinstance(content, list):
        content = content[0].get("text", "")
    
    try:
        clean_content = str(content).replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_content)
        return {**state, "intent": result.get("intent", "chitchat")}
    except Exception as e:
        print(f"⚠️ Router Parsing Error: {e}. Content was: {content}")
        return {**state, "intent": "chitchat"} # Fallback

# ─────────────────────────────────────────────────────────
# NODE 3a — Profiler
# ─────────────────────────────────────────────────────────
def profiler_node(state: AgentState) -> AgentState:
    QUESTION_FLOW = {
        "intent": {
            "question": "what brings you to ET today",
            "prompt": "What brings you to ET today — are you here more for investing, staying updated on business news, or growing your own business?"
        },
        "sophistication": {
            "question": "investment experience",
            "prompt": "Are you already investing somewhere — SIPs, stocks, FDs — or are you just starting out?"
        },
        "goal": {
            "question": "financial goal",
            "prompt": "What's your main goal right now — building long-term wealth, active trading, or learning about finance?"
        },
        "profession": {
            "question": "profession",
            "prompt": "Quick one — are you salaried, running your own business, or a student?"
        }
    }
    
    profile = state["profile"]
    asked = state.get("questions_asked", [])
    next_question = None
    
    for field, config in QUESTION_FLOW.items():
        if profile.get(field) in [None, "null"] and config["question"] not in asked:
            next_question = config
            asked.append(config["question"])
            break
    
    if next_question:
        response_prompt = f"""
        You are the ET AI Concierge. You need to ask this question naturally:
        "{next_question['prompt']}"

        Conversation so far:
        {json.dumps(state["messages"][-4:], indent=2)}

        Make it feel like a natural conversation, not a form. 
        Keep it to 1-2 sentences max. Don't say "Question X of Y".
        """
        response = llm.invoke([HumanMessage(content=response_prompt)])
        reply = response.content
    else:
        reply = "I have a good sense of what you need. Let me put together your personalized ET guide..."
    
    return {
        **state,
        "retrieved_chunks": [],
        "questions_asked": asked,
        "response": {
            "type": "profiling",
            "message": reply,
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": [],
            "show_roadmap": False
        }
    }


# ─────────────────────────────────────────────────────────
# NODE 3b — RAG Retriever
# Queries MongoDB with user profile context
# ─────────────────────────────────────────────────────────
def rag_retriever_node(state: AgentState) -> AgentState:
    from retriever_service import get_product_chunks  # your retrieval.py from before

    print("\n🔍 [DEBUG] --- STARTING RAG RETRIEVAL ---")
    
    # Build a rich query from profile + current message
    profile = state["profile"]
    query = f"""
{state["current_message"]}
User profile: {profile.get("intent")} focused, 
{profile.get("sophistication")} level investor,
goal is {profile.get("goal")},
profession: {profile.get("profession")}
"""
    
    # Query both collections
    product_chunks = get_product_chunks(
        profile=profile,
        query=query,
        k=3
    )
    
    # Also query persona journeys collection
    from retriever_service import get_persona_chunks
    persona_chunks = get_persona_chunks(
        query=query,
        k=1
    )
    
    all_chunks = product_chunks + persona_chunks

    print("✅ [DEBUG] --- RETRIEVAL COMPLETE ---\n")
    
    return {**state, "retrieved_chunks": all_chunks}


# ─────────────────────────────────────────────────────────
# NODE 3c — Chitchat
# General responses that don't need RAG
# ─────────────────────────────────────────────────────────
def chitchat_node(state: AgentState) -> AgentState:
    return {
        **state,
        "retrieved_chunks": [],
        "response": {
            "type": "chitchat",
            "message": None,  # response generator handles this
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": [],
            "show_roadmap": False
        }
    }


def response_generator_node(state: AgentState) -> AgentState:
    if state.get("response", {}).get("type") == "profiling":
        return state
    
    # ✅ NEW (Using Document attributes)
    rag_context = ""
    if state["retrieved_chunks"]:
        context_parts = []
        for c in state["retrieved_chunks"]:
        # Use .metadata and .page_content instead of ['metadata'] and ['content']
            product = c.metadata.get("product_name", "ET Product")
            section = c.metadata.get("section", "General")
            text = c.page_content
            context_parts.append(f"[{product} — {section}]\n{text}")
    
        rag_context = "\n\n".join(context_parts)
    
    system_msg = f"""You are the ET AI Concierge — a friendly, knowledgeable 
    guide to everything The Economic Times offers. You help users discover the 
    right ET products for their specific needs.

    User profile:
    {json.dumps(state["profile"], indent=2)}

    Onboarding complete: {state["onboarding_complete"]}

    ET Product Knowledge:
    {rag_context if rag_context else "Use your general knowledge about ET products."}

    Rules:
    - Be conversational and warm, not robotic
    - Always ground recommendations in the user's specific profile
    - If recommending a product, say WHY it fits them specifically
    - Keep responses concise — max 3-4 sentences
    - Never make up features or pricing"""

    # Format history for Gemini
    history = []
    for m in state["messages"]:
        history.append(HumanMessage(content=m["content"]) if m["role"] == "user" else HumanMessage(content=m["content"]))
    
    history.append(HumanMessage(content=state["current_message"]))
    
    # Send System Message + History to Gemini
    response = llm.invoke([SystemMessage(content=system_msg)] + history)
    if isinstance(response.content, list):
        reply = response.content[0].get("text", "")
    else:
        reply = response.content
    
    mentioned_products = []
    product_map = {"ET Prime": "etprime", "ET Money": "etmoney", "ET Markets": "etmarkets", "ET Now": "etnow"}
    for name, pid in product_map.items():
        if name.lower() in reply.lower():
            mentioned_products.append(pid)
    
    return {
        **state,
        "response": {
            "type": "product_query",
            "message": reply,
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "recommendations": mentioned_products,
            "show_roadmap": False
        }
    }

# (The rest of your functions—output_formatter, state_updater—remain the same 
# as they are logic-based, not LLM-based)


# ─────────────────────────────────────────────────────────
# NODE 5 — Output Formatter
# Produces the final structured JSON for the frontend
# ─────────────────────────────────────────────────────────
def output_formatter_node(state: AgentState) -> AgentState:
    
    profile = state["profile"]
    response = state["response"]
    
    # Decide if we should show the roadmap card
    # Show it when onboarding just completed
    show_roadmap = (
        state["onboarding_complete"] and
        response.get("type") in ["product_query", "profiling"] and
        len(state["messages"]) < 12  # early in conversation
    )
    
    # Build roadmap if needed
    roadmap = None
    if show_roadmap:
        roadmap = build_roadmap(profile)  # see helper below
    
    # Final structured output
    structured_response = {
        "session_id": state["session_id"],
        
        # What the frontend renders in the chat bubble
        "message": response["message"],
        
        # Sidebar profile panel
        "profile_update": {
            "intent": profile.get("intent"),
            "sophistication": profile.get("sophistication"),
            "goal": profile.get("goal"),
            "profession": profile.get("profession"),
            "interests": profile.get("interests", []),
            "onboarding_complete": state["onboarding_complete"]
        },
        
        # Sidebar recommendations panel
        "recommendations": response.get("recommendations", []),
        
        # Roadmap card — shown once after profiling done
        "roadmap": roadmap,
        
        # Quick reply chips to show below message
        "chips": get_chips(state),
        
        # Response type for frontend to handle differently
        "response_type": response.get("type", "product_query")
    }
    
    return {**state, "response": structured_response}


def build_roadmap(profile: dict) -> dict:
    """Build a personalized ET journey based on profile."""
    
    # Simple rule-based roadmap — deterministic, fast, no API call needed
    roadmap_rules = {
        ("beginner", "investing"): [
            {"step": 1, "product": "ET Money", "reason": "Set up your first SIP in 10 minutes", "url": "etmoney.com"},
            {"step": 2, "product": "ET Prime", "reason": "Beginner-friendly investing columns", "url": "etprime.com"},
            {"step": 3, "product": "ET Masterclass", "reason": "Investing 101 when you're ready", "url": "etmasterclass.com"}
        ],
        ("intermediate", "investing"): [
            {"step": 1, "product": "ET Prime", "reason": "Stock Reports Plus for deep analysis", "url": "etprime.com"},
            {"step": 2, "product": "ET Markets", "reason": "Portfolio tracker and screeners", "url": "etmarkets.com"},
            {"step": 3, "product": "ET Masterclass", "reason": "Advanced portfolio strategies", "url": "etmasterclass.com"}
        ],
        ("beginner", "news"): [
            {"step": 1, "product": "ET Prime", "reason": "Curated daily briefings, no noise", "url": "etprime.com"},
            {"step": 2, "product": "ET Now", "reason": "Video explainers for breaking news", "url": "etnow.com"},
        ],
    }
    
    key = (
        profile.get("sophistication", "beginner"),
        profile.get("intent", "news")
    )
    steps = roadmap_rules.get(key, roadmap_rules[("beginner", "news")])
    
    return {
        "title": f"Your personalized ET journey",
        "profile_summary": [
            profile.get("intent", ""),
            profile.get("sophistication", ""),
            profile.get("profession", "")
        ],
        "steps": steps
    }


def get_chips(state: AgentState) -> list[str]:
    """Return quick reply suggestions based on context."""
    if not state["onboarding_complete"]:
        return []  # no chips during profiling
    
    intent = state["profile"].get("intent")
    if intent == "investing":
        return ["Tell me about ET Prime", "How do I start SIPs?", "What's Stock Reports Plus?"]
    elif intent == "news":
        return ["What's in ET Prime?", "Tell me about ET Now", "Show me my roadmap"]
    return ["What does ET offer?", "Show me my roadmap"]


# ─────────────────────────────────────────────────────────
# NODE 6 — State Updater
# Persists everything back to MongoDB
# ─────────────────────────────────────────────────────────
def state_updater_node(state: AgentState) -> AgentState:
    from db import sessions_collection  # your MongoDB sessions collection
    
    # Append the exchange to conversation history
    updated_messages = state["messages"] + [
        {"role": "user", "content": state["current_message"]},
        {"role": "assistant", "content": state["response"]["message"]}
    ]
    
    sessions_collection.update_one(
        {"session_id": state["session_id"]},
        {"$set": {
            "profile": state["profile"],
            "onboarding_complete": state["onboarding_complete"],
            "questions_asked": state.get("questions_asked", []),
            "messages": updated_messages[-20:],  # keep last 20 turns only
            "recommendations": state["response"].get("recommendations", []),
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {**state, "messages": updated_messages}