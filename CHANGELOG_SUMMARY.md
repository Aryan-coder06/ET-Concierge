# Project Log: ET-Concierge Development Summary

This log summarizes the key architectural changes, feature integrations, and frontend enhancements implemented to transform the ET-Concierge from a basic chatbot into a sophisticated AI guide.

## 1. LangGraph Workflow Integration
We transitioned the chatbot logic into a structured **LangGraph** workflow to manage stateful, multi-turn conversations and complex routing.

- **Graph Structure**:
    - `profile_extractor`: Automatically identifies user interests and persona signals from messages.
    - `router`: Determines the next step based on intent (Profiling, Product Query, or Chitchat).
    - `rag_retriever`: Performs hybrid search across the ET knowledge base and product registry.
    - `response_generator`: Synthesizes grounded answers using retrieved context.
    - `output_formatter`: Cleans and structures the final response for the UI.
    - `state_updater`: Persists the journey history and profile updates to MongoDB.
- **Workflow Explanation**: Every message is first analyzed for profile data, then routed. Product-specific questions trigger the RAG flow, while general greetings use the chitchat flow. The "profiler" node is triggered when the system needs more info to make a recommendation.

## 2. Voice Agent Integration
A dedicated voice-first experience was built to allow hands-free interaction with LUNA.

- **Backend Architecture**:
    - **VoiceAgent Class**: Uses `create_react_agent` with a specialized `search_et_knowledge` tool to ensure voice responses are grounded.
    - **Voice Formatting**: A dedicated LLM pass converts complex RAG answers into concise (under 150 words), conversational scripts without markdown.
- **Service Providers**:
    - **STT (Speech-to-Text)**: Integrated **Sarvam AI (Saaras v3)** for high-accuracy audio transcription via REST API.
    - **TTS (Text-to-Speech)**: Integrated **Sarvam AI (Bulbul v3)** to generate natural-sounding voice responses.
- **Workflow**: Audio is captured in the frontend -> Sent to `/chat/voice` -> Transcribed -> Processed through the LangGraph -> Formatted for voice -> Converted to speech -> Returned as Base64 audio to the client.

## 3. RAG (Retrieval-Augmented Generation) Enhancements
Significant upgrades were made to the retrieval system to ensure accuracy and trust.

- **RAG Flag**: Implemented a `used_rag` flag in the backend that signals to the UI whenever the assistant utilizes the knowledge base.
- **Product Registry**: Added a verified "Source of Truth" layer for ET products (Prime, Markets, Portfolio, etc.) to prevent hallucinations.
- **Hybrid Retrieval**: Combined vector similarity search with keyword-based retrieval for better handling of specific product names.
- **Evaluation**: Created a 40-prompt evaluation suite (`run_et_eval.py`) to benchmark RAG performance, achieving a 1.0/1.0 score on core ET queries.

## 4. Frontend & UI Changes
The UI was overhauled to support the new concierge and voice features.

- **Voice Controls**:
    - **VoiceChatButton**: A specialized component with a "Record/Stop" toggle.
    - **Visual Feedback**: The button pulses red while recording and turns solid black while LUNA is speaking.
    - **Status Indicators**: Real-time status text shown during voice chat: *"Listening..."*, *"Processing..."*, and *"Speaking..."*.
- **Message Interface**:
    - **RAG Badge**: A small "RAG" tag appears on AI messages that were grounded in ET data.
    - **Rich Cards**: Added support for rendering `recommended_products`, `roadmaps`, and `source_citations` directly in the chat bubble.
- **Visual Hinting**: The UI now reacts to `visual_hint` signals from the backend (e.g., `markets_tools`, `learning_lane`) to show relevant widgets or panels alongside the text.

## 5. Backend Infrastructure
- **Session Management**: Implemented `journey_history` to track the user's path across the ET ecosystem over time.
- **Market Data**: Added a `/market-snapshot` service to provide live-style context for Nifty, Sensex, and Gold, linking back to ET's market tools.
