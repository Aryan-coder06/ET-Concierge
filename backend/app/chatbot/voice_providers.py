import os
import httpx
import logging
from typing import Optional
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class GroqSTTProvider:
    """
    Handles Speech-to-Text conversion using Groq's whisper endpoints.
    """
    def __init__(self):
        # We rely on the GROQ_API_KEY environment variable being set.
        self.client = AsyncGroq()  # Automatically picks up GROQ_API_KEY
        self.model = "whisper-large-v3-turbo"

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Sends audio bytes to Groq API and returns transcribed text.
        Converts audio to WAV using pydub for maximum compatibility.
        """
        if not audio_bytes:
            return ""

        logger.info("Transcribing audio: %d bytes. First 16 bytes: %s", len(audio_bytes), audio_bytes[:16].hex())

        try:
            from pydub import AudioSegment
            import io
            
            # Load audio from bytes
            audio_file = io.BytesIO(audio_bytes)
            
            # Pydub can usually infer the format if it's common (webm, mp4, ogg)
            # but sometimes we need to help it if the header is tricky.
            try:
                audio = AudioSegment.from_file(audio_file)
            except Exception as e:
                logger.warning("Pydub failed to load audio from file: %s. Trying direct format hints.", e)
                # Try common formats as fallbacks
                for fmt in ["webm", "mp4", "ogg", "aac"]:
                    try:
                        audio_file.seek(0)
                        audio = AudioSegment.from_file(audio_file, format=fmt)
                        logger.info("Successfully loaded audio using format hint: %s", fmt)
                        break
                    except:
                        continue
                else:
                    # If all failed, let's just try to send the raw bytes to Groq as a last resort
                    # using our magic bytes detection from before.
                    return await self._transcribe_raw(audio_bytes)

            # Export to WAV
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_bytes = wav_io.getvalue()
            
            logger.info("Converted audio to WAV: %d bytes", len(wav_bytes))

            transcription = await self.client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model=self.model,
                response_format="text",
                language="en",
                temperature=0.0
            )
            # When response_format="text", the API returns the raw text string.
            return str(transcription).strip()
        except Exception as exc:
            logger.error("Groq STT failed: %s", exc)
            return ""

    async def _transcribe_raw(self, audio_bytes: bytes) -> str:
        """Fallback to sending raw bytes with detected extension."""
        filename = "audio.webm"
        if len(audio_bytes) > 4:
            if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
                filename = "audio.webm"
            elif audio_bytes[:4] == b'OggS':
                filename = "audio.ogg"
            elif b'ftyp' in audio_bytes[4:12]:
                filename = "audio.mp4"
            elif audio_bytes[:4] == b'fLaC':
                filename = "audio.flac"
            elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
                filename = "audio.mp3"
            elif audio_bytes[:4] == b'RIFF':
                filename = "audio.wav"

        try:
            transcription = await self.client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model=self.model,
                response_format="text",
                language="en",
                temperature=0.0
            )
            return str(transcription).strip()
        except Exception as exc:
            logger.error("Groq STT fallback failed: %s", exc)
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
                
                audio_base64 = data.get("audio")
                if audio_base64:
                    return audio_base64
                    
                return None
        except Exception as exc:
            logger.error("Sarvam TTS failed: %s", exc)
            return None
