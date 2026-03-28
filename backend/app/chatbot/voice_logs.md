# Voice Agent Implementation Log

## Session 1: Setup and Basic Providers
*   **Added Dependencies**: Updated `backend/requirements.txt` to include `websockets`, `groq`, `httpx`, and `pydub`.
*   **Created Voice Providers**: Created `backend/app/chatbot/voice_providers.py`
    *   Added `GroqSTTProvider` utilizing `AsyncGroq` for translating audio bytes to text using `whisper-large-v3-turbo`.
    *   Added `SarvamTTSProvider` utilizing `httpx` and Sarvam AI REST API for translating text sentences into `base64` audio strings.
*   **Created Voice Agent**: Created `backend/app/chatbot/voice_agent.py`
    *   Set up a simple LangGraph agent (`create_react_agent`) using `ChatGoogleGenerativeAI`.
    *   Configured it to yield streamed string chunks from the Gemini API using `astream(stream_mode="messages")`.

## Session 2: Backend WebSocket Pipeline
*   **Added WebSocket Endpoint**: Implemented `@app.websocket("/ws/voice")` in `backend/app/main.py`.
*   **Pipeline Logic (Chunked Sandwich)**:
    *   Receives audio frames from client over WS and buffers them.
    *   Triggered by `{"event": "stop_speaking"}` WS message.
    *   **Listen**: Flushes buffer to `GroqSTTProvider`.
    *   **Think**: Streams tokens from `VoiceAgent`.
    *   **Speak**: Buffers streamed tokens into sentences (using regex split on `.?!`) and passes them to `SarvamTTSProvider`.
    *   Sends `base64` audio frames and statuses back to the client over WS.

## Session 3: Frontend Voice Client
*   **Created VoiceChatButton**: Created `src/components/search/VoiceChatButton.tsx`.
    *   Uses `MediaRecorder` to capture audio chunks every 250ms and sends them over WebSocket.
    *   Listens to WS events (`status`, `error`, `turn_complete`, `audio`).
    *   Decodes and plays base64 `audio` chunks sequentially using Web Audio API `AudioContext`.
*   **Integrated into UI**: Added `VoiceChatButton` to `src/app/search/page.tsx` right next to the Send button.
