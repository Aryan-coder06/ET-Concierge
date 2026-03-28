import io
import logging
import os
import re
import tempfile
from typing import Any


VOICE_MAX_CHARACTERS = 420
logger = logging.getLogger(__name__)


def _clean_spacing(text: str) -> str:
    cleaned = text.replace("\n", " ").replace("ETMasterclass", "ET Masterclass")
    cleaned = cleaned.replace("Next Move:", "Next,")
    cleaned = cleaned.replace("Recommendation:", "Recommendation")
    cleaned = cleaned.replace("|", " ")
    cleaned = re.sub(r"[*_`#]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def format_text_for_voice(answer: str) -> str:
    cleaned = _clean_spacing(answer)
    if len(cleaned) <= VOICE_MAX_CHARACTERS:
        return cleaned

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    spoken_parts: list[str] = []
    total = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        projected = total + len(sentence) + (1 if spoken_parts else 0)
        if projected > VOICE_MAX_CHARACTERS:
            break
        spoken_parts.append(sentence)
        total = projected

    if spoken_parts:
        return " ".join(spoken_parts).strip()

    truncated = cleaned[:VOICE_MAX_CHARACTERS].rsplit(" ", 1)[0].strip()
    return f"{truncated}."


def voice_used_rag(chat_payload: dict[str, Any]) -> bool:
    return bool(
        chat_payload.get("source_citations")
        or chat_payload.get("recommended_products")
        or chat_payload.get("response_type") == "product_query"
    )


def normalize_audio_for_stt(
    audio_bytes: bytes,
    *,
    original_filename: str | None = None,
) -> tuple[bytes, str, str]:
    if not audio_bytes:
        return audio_bytes, original_filename or "audio.wav", "audio/wav"

    try:
        from pydub import AudioSegment
    except Exception as exc:
        logger.warning("pydub is unavailable, sending raw audio to STT: %s", exc)
        return audio_bytes, original_filename or "audio.webm", "audio/webm"

    temp_suffix = ".webm"
    if original_filename and "." in original_filename:
        temp_suffix = f".{original_filename.rsplit('.', 1)[1]}"

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=temp_suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        audio_segment = AudioSegment.from_file(temp_path)
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        return wav_buffer.getvalue(), "recording.wav", "audio/wav"
    except Exception as exc:
        logger.warning("Audio normalization failed, sending raw audio to STT: %s", exc)
        return audio_bytes, original_filename or "audio.webm", "audio/webm"
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
