import json
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel, Field

from .chatbot.config import get_settings
from .chatbot.market_data import get_market_snapshot
from .chatbot.service import concierge_service

# Initialize the new voice modules
from .chatbot.voice_providers import SarvamSTTProvider, SarvamTTSProvider
from .chatbot.voice_agent import VoiceAgent

logger = logging.getLogger(__name__)

stt_provider = SarvamSTTProvider()
tts_provider = SarvamTTSProvider()
voice_agent = VoiceAgent()


class VoiceChatResponse(BaseModel):
    user_text: str
    agent_text: str
    audio: str | None = None


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


class MarketSnapshotItem(BaseModel):
    symbol: str
    label: str
    price: float
    change: float
    change_pct: float
    sparkline: list[float] = Field(default_factory=list)
    et_route: str
    href: str


class MarketSnapshotLink(BaseModel):
    label: str
    href: str
    note: str


class MarketSnapshotResponse(BaseModel):
    as_of: str
    source_label: str
    items: list[MarketSnapshotItem] = Field(default_factory=list)
    et_links: list[MarketSnapshotLink] = Field(default_factory=list)


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


from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form

@app.post("/chat/voice", response_model=VoiceChatResponse)
async def voice_chat_rest(
    thread_id: str = Form("default-voice-thread"),
    audio_file: UploadFile = File(...)
):
    try:
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # 1. Normalize/Convert audio for STT if needed
        # We can use pydub here to ensure it's WAV as Sarvam expects
        from pydub import AudioSegment
        import io
        
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            processed_audio = wav_io.getvalue()
        except Exception as e:
            logger.warning(f"Audio conversion failed: {e}. Attempting raw.")
            processed_audio = audio_bytes

        # 2. STT
        user_text = await stt_provider.transcribe_audio(processed_audio)
        if not user_text:
            return VoiceChatResponse(user_text="", agent_text="I couldn't hear you.", audio=None)

        # 3. Agent
        agent_text = ""
        async for token in voice_agent.stream_response(user_text, thread_id):
            agent_text += token
        
        # 4. TTS
        audio_base64 = await tts_provider.synthesize_speech(agent_text)
        
        return VoiceChatResponse(
            user_text=user_text,
            agent_text=agent_text,
            audio=audio_base64
        )
    except Exception as e:
        logger.error(f"Voice chat REST error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/market-snapshot", response_model=MarketSnapshotResponse)
def market_snapshot() -> MarketSnapshotResponse:
    try:
        return MarketSnapshotResponse(**get_market_snapshot())
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The market snapshot service is temporarily unavailable.",
        ) from exc


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


@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    audio_buffer = bytearray()
    
    # Simple function to split text into sentences
    def split_into_sentences(text: str) -> tuple[list[str], str]:
        import re
        # Split on sentence boundaries
        parts = re.split(r'([.?!])', text)
        sentences = []
        for i in range(0, len(parts)-1, 2):
            sentences.append(parts[i] + parts[i+1])
        
        remainder = parts[-1] if len(parts) % 2 != 0 else ""
        return sentences, remainder

    try:
        while True:
            # We explicitly await a frame, which can be text or bytes
            message = await websocket.receive()
            
            if message.get("type") == "websocket.disconnect":
                logger.info("Voice WebSocket disconnect received")
                break
                
            if "bytes" in message:
                audio_buffer.extend(message["bytes"])
            elif "text" in message:
                data = json.loads(message["text"])
                if data.get("event") == "stop_speaking":
                    if not audio_buffer:
                        logger.warning("Stop speaking received but audio buffer is empty")
                        await websocket.send_json({"event": "turn_complete"})
                        continue
                        
                    thread_id = data.get("thread_id", "default-voice-thread")
                    
                    try:
                        # 1. STT
                        audio_bytes = bytes(audio_buffer)
                        logger.info("Processing audio turn: %d bytes", len(audio_bytes))
                        audio_buffer.clear()
                        
                        await websocket.send_json({"event": "status", "message": "transcribing"})
                        user_text = await stt_provider.transcribe_audio(audio_bytes)
                        
                        if not user_text:
                            await websocket.send_json({"event": "error", "message": "Could not hear you clearly."})
                            await websocket.send_json({"event": "turn_complete"})
                            continue
                            
                        await websocket.send_json({"event": "user_text", "text": user_text})
                        await websocket.send_json({"event": "status", "message": "thinking"})
                        
                        # 2. Agent & 3. TTS
                        text_buffer = ""
                        async for token in voice_agent.stream_response(user_text, thread_id):
                            text_buffer += token
                            sentences, remainder = split_into_sentences(text_buffer)
                            
                            for sentence in sentences:
                                sentence = sentence.strip()
                                if sentence:
                                    await websocket.send_json({"event": "agent_text", "text": sentence})
                                    audio_base64 = await tts_provider.synthesize_speech(sentence)
                                    if audio_base64:
                                        await websocket.send_json({"event": "audio", "audio": audio_base64})
                                        
                            text_buffer = remainder
                        
                        # Flush remainder
                        if text_buffer.strip():
                            sentence = text_buffer.strip()
                            await websocket.send_json({"event": "agent_text", "text": sentence})
                            audio_base64 = await tts_provider.synthesize_speech(sentence)
                            if audio_base64:
                                await websocket.send_json({"event": "audio", "audio": audio_base64})
                                
                        await websocket.send_json({"event": "status", "message": "listening"})
                    except Exception as e:
                        logger.error(f"Error during voice processing: {e}")
                        await websocket.send_json({"event": "error", "message": "Something went wrong."})
                    finally:
                        await websocket.send_json({"event": "turn_complete"})
                    
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
