import re
from typing import Any


VOICE_MAX_CHARACTERS = 420


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
