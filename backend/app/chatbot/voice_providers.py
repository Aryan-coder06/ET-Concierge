import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SarvamSTTProvider:
    """
    Handles Speech-to-Text conversion using Sarvam AI's Saaras v3 REST API.
    """
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.url = "https://api.sarvam.ai/speech-to-text"

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Sends audio bytes to Sarvam AI and returns transcribed text.
        """
        if not audio_bytes:
            return ""

        if not self.api_key:
            logger.warning("SARVAM_API_KEY is not set. Cannot transcribe audio.")
            return ""

        headers = {
            "api-subscription-key": self.api_key,
        }

        # Saaras v3 expects multipart/form-data
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav")
        }
        data = {
            "model": "saaras:v3",
            "mode": "transcribe"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=30.0
                )
                if response.status_code != 200:
                    logger.error("Sarvam STT failed with status %s: %s", response.status_code, response.text)
                response.raise_for_status()
                result = response.json()
                
                return result.get("transcript", "").strip()
        except Exception as exc:
            logger.error("Sarvam STT failed: %s", exc)
            return ""


class SarvamTTSProvider:
    """
    Handles Text-to-Speech conversion using Sarvam AI's REST API.
    """
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.url = "https://api.sarvam.ai/text-to-speech"

    async def synthesize_speech(self, text: str, speaker: str = "shubh") -> Optional[str]:
        """
        Sends text to Sarvam AI and returns the base64 encoded audio string.
        """
        text = text.strip()
        if not text:
            return None

        if not self.api_key:
            logger.warning("SARVAM_API_KEY is not set. Cannot synthesize speech.")
            return None

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Sarvam Bulbul V3 standard payload
        payload = {
            "text": text,
            "target_language_code": "en-IN",
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.0,
            "enable_preprocessing": True
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=15.0
                )
                if response.status_code != 200:
                    logger.error("Sarvam TTS failed with status %s: %s", response.status_code, response.text)
                response.raise_for_status()
                data = response.json()
                
                # According to docs, response has 'audios' array
                audios = data.get("audios", [])
                if audios and len(audios) > 0:
                    return audios[0]
                    
                return None
        except Exception as exc:
            logger.error("Sarvam TTS failed: %s", exc)
            return None
