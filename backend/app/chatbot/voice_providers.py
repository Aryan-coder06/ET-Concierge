import logging
from typing import Optional

import httpx

from .config import get_settings


logger = logging.getLogger(__name__)


def _guess_audio_metadata(
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[str, str]:
    if filename and content_type and content_type.startswith("audio/"):
        return filename, content_type

    resolved_filename = filename or "audio.wav"
    resolved_content_type = content_type or "audio/wav"

    if len(audio_bytes) > 12:
        if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
            return resolved_filename.rsplit(".", 1)[0] + ".webm", "audio/webm"
        if audio_bytes[:4] == b"OggS":
            return resolved_filename.rsplit(".", 1)[0] + ".ogg", "audio/ogg"
        if b"ftyp" in audio_bytes[4:12]:
            return resolved_filename.rsplit(".", 1)[0] + ".mp4", "audio/mp4"
        if audio_bytes[:4] == b"fLaC":
            return resolved_filename.rsplit(".", 1)[0] + ".flac", "audio/flac"
        if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
            return resolved_filename.rsplit(".", 1)[0] + ".mp3", "audio/mpeg"
        if audio_bytes[:4] == b"RIFF":
            return resolved_filename.rsplit(".", 1)[0] + ".wav", "audio/wav"

    return resolved_filename, resolved_content_type


class SarvamSTTProvider:
    def __init__(self) -> None:
        self.url = "https://api.sarvam.ai/speech-to-text"

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:
        if not audio_bytes:
            return ""

        settings = get_settings()
        if not settings.sarvam_api_key:
            logger.warning("SARVAM_API_KEY is missing. Voice transcription is unavailable.")
            return ""

        upload_name, upload_type = _guess_audio_metadata(
            audio_bytes,
            filename=filename,
            content_type=content_type,
        )

        headers = {"api-subscription-key": settings.sarvam_api_key}
        files = {"file": (upload_name, audio_bytes, upload_type)}
        data = {"model": "saaras:v3", "mode": "transcribe"}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    self.url,
                    headers=headers,
                    data=data,
                    files=files,
                )
                if response.status_code >= 400:
                    logger.error(
                        "Sarvam STT rejected audio (%s): %s",
                        response.status_code,
                        response.text,
                    )
                response.raise_for_status()
                result = response.json()
                return str(result.get("transcript", "")).strip()
        except httpx.HTTPStatusError as exc:
            logger.error("Sarvam STT failed with HTTP error: %s", exc)
            return ""
        except Exception as exc:
            logger.error("Sarvam STT failed: %s", exc)
            return ""


class SarvamTTSProvider:
    def __init__(self) -> None:
        self.url = "https://api.sarvam.ai/text-to-speech"

    async def synthesize_speech(self, text: str, speaker: str = "shubh") -> Optional[str]:
        clean_text = text.strip()
        if not clean_text:
            return None

        settings = get_settings()
        if not settings.sarvam_api_key:
            logger.warning("SARVAM_API_KEY is missing. Voice synthesis is unavailable.")
            return None

        headers = {
            "api-subscription-key": settings.sarvam_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": clean_text,
            "target_language_code": "en-IN",
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": 1.0,
            "enable_preprocessing": True,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, headers=headers, json=payload)
                if response.status_code >= 400:
                    logger.error(
                        "Sarvam TTS rejected request (%s): %s",
                        response.status_code,
                        response.text,
                    )
                response.raise_for_status()
                result = response.json()
                audios = result.get("audios", [])
                if isinstance(audios, list) and audios:
                    return str(audios[0])
                return None
        except httpx.HTTPStatusError as exc:
            logger.error("Sarvam TTS failed with HTTP error: %s", exc)
            return None
        except Exception as exc:
            logger.error("Sarvam TTS failed: %s", exc)
            return None
