import logging
import json
from typing import AsyncGenerator, List, Tuple, Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from .config import get_settings
from .retriever_service import get_product_chunks, get_persona_chunks

logger = logging.getLogger(__name__)

@tool
def search_et_knowledge(query: str) -> str:
    """
    Search for information about ET (The Economic Times) products, features, subscriptions, 
    and general knowledge from the official ET knowledge base.
    Use this tool whenever the user asks about ET Prime, ET Markets, ET Portfolio, 
    ET Wealth, ETMasterclass, or any other ET service.
    """
    profile = {} 
    
    try:
        product_chunks = get_product_chunks(query=query, profile=profile, k=3)
        persona_chunks = get_persona_chunks(query=query, profile=profile, k=1)
        all_chunks = product_chunks + persona_chunks
        
        if not all_chunks:
            return "No specific ET information found for this query."
            
        context_parts = []
        for chunk in all_chunks:
            product = chunk.metadata.get("product_name") or "ET Context"
            context_parts.append(f"[{product}]\n{chunk.page_content}")
            
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error in search_et_knowledge tool: {e}")
        return f"Error retrieving information: {str(e)}"

class VoiceAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.google_chat_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            streaming=True
        )
        
        system_prompt = """You are LUNA, an AI voice assistant for ET (The Economic Times). Your goal is to have a natural, concise, and friendly spoken conversation.

KNOWLEDGE BASE:
Always use the 'search_et_knowledge' tool to answer questions about ET products (Prime, Markets, Portfolio, etc.), features, or company info. 

STRICT RULES:
1. WORD LIMIT: Your response MUST be under 150-200 words. Be extremely concise.
2. SYNTHESIZE: Do NOT repeat the raw chunks from the search tool. Digest the information and provide a helpful, human-like summary.
3. NO FORMATTING: Do NOT use emojis, markdown, asterisks (**), or long lists. Your output is for text-to-speech.
4. CONVERSATIONAL: Speak naturally. Use short sentences.

VOICE-FIRST:
Avoid technical jargon. If information is complex, simplify it for a listener."""
        
        self.checkpointer = InMemorySaver()
        self.tools = [search_et_knowledge]
        
        self.app = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt,
            checkpointer=self.checkpointer
        )

    async def format_response_for_voice(self, text: str) -> str:
        """
        Takes a potentially long/formatted RAG response and converts it 
        into a concise, easy-to-read, and conversational voice response.
        """
        formatting_prompt = f"""You are a voice formatting specialist. Your task is to take the following AI response and convert it into a highly readable, natural-sounding conversational script for a voice assistant.

STRICT RULES:
1. MAX 150 WORDS: Keep it very concise.
2. NO MARKDOWN: Remove all asterisks, bolding, lists, and special characters.
3. CLEAR FLOW: Use simple, short sentences.
4. SYNTHESIZE: If there is data or meta-information, summarize it into a helpful sentence.
5. NO URLS: Do not read out URLs unless they are extremely simple (like "et prime dot com").

Input Response:
"{text}"

Formatted Script:"""

        try:
            response = await self.llm.ainvoke([SystemMessage(content=formatting_prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error("Error formatting voice response: %s", e)
            # Fallback: simple cleanup of the input text
            import re
            cleaned = re.sub(r"[*_#`]", "", text)
            return cleaned[:500]

    async def stream_response(self, text: str, thread_id: str) -> AsyncGenerator[Union[str, bool], None]:
        """
        Takes user text and yields AI text chunks or a boolean flag for RAG usage.
        Yields:
            str: Text tokens for the agent's response.
            bool: True if RAG tool was used during this turn.
        """
        config = {"configurable": {"thread_id": thread_id}}
        used_rag = False
        
        try:
            # We use stream_mode="messages" to get content as it's generated
            async for msg, metadata in self.app.astream(
                {"messages": [HumanMessage(content=text)]}, 
                config, 
                stream_mode="messages"
            ):
                # Check for tool calls to detect RAG usage
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc["name"] == "search_et_knowledge":
                            used_rag = True
                            yield True # Signal RAG usage early

                if msg.content and isinstance(msg.content, str):
                    yield msg.content
                    
            if not used_rag:
                yield False
                
        except Exception as e:
            logger.error("Voice Agent streaming error: %s", e)
            yield "I'm having trouble thinking right now."
            yield False
