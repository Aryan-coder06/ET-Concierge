import logging
import uuid
from typing import AsyncGenerator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from .config import get_settings

logger = logging.getLogger(__name__)

class VoiceAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.google_chat_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            streaming=True
        )
        
        system_prompt = """You are an AI voice assistant for ET. Your goal is to have a natural, concise, and friendly spoken conversation with the user.
Do NOT use emojis, markdown, special characters, or long lists. Your responses will be read by a text-to-speech engine, so keep them conversational and easy to listen to. Use short sentences."""
        
        self.checkpointer = InMemorySaver()
        self.app = create_react_agent(
            model=self.llm,
            tools=[],  # Add tools here if needed later
            prompt=system_prompt,
            checkpointer=self.checkpointer
        )

    async def stream_response(self, text: str, thread_id: str) -> AsyncGenerator[str, None]:
        """
        Takes user text and yields AI text chunks using LangGraph's streaming mode.
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # stream_mode="messages" yields tuples of (message_chunk, metadata)
            async for msg, metadata in self.app.astream(
                {"messages": [HumanMessage(content=text)]}, 
                config, 
                stream_mode="messages"
            ):
                if msg.content and isinstance(msg.content, str):
                    yield msg.content
        except Exception as e:
            logger.error("Voice Agent streaming error: %s", e)
            yield "I'm having trouble thinking right now."
