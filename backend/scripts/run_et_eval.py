import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.chatbot.registry import load_eval_prompts, official_product_names
from app.chatbot.service import concierge_service


EVAL_OUTPUT_DIR = BACKEND_ROOT / "eval_results"


def _normalize_text(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else " " for character in value)
    return " ".join(normalized.split())





def _citation_matches(required: str, citations: list[dict]) -> bool:
    required_lower = required.lower()
    if "multiple" in required_lower:
        return len(citations) >= 4
    if "relevant source" in required_lower:
        return bool(citations)
    if "portfolio pages" in required_lower:
        return any("portfolio" in str(citation.get("label", "")).lower() for citation in citations)
    if "events portals" in required_lower:
        return (
            sum(
                1
                for citation in citations
                if any(
                    keyword in str(citation.get("label", "")).lower()
                    for keyword in ["events", "portal", "summit"]
                )
            )
            >= 3
        )

    required_cleaned = required.replace("if available", "")
    for generic_term in [" page", " pages", " portal", " portals"]:
        required_cleaned = required_cleaned.replace(generic_term, "")

    required_normalized = _normalize_text(required_cleaned)
    variants = [required_normalized]
    for splitter in [" or ", "/"]:
        if splitter in required_normalized:
            variants = [
                part.strip()
                for part in required_normalized.split(splitter)
                if part.strip()
            ]
            break

    citation_text = " ".join(
        _normalize_text(
            " ".join(
                [
                    str(citation.get("label", "")),
                    str(citation.get("source_id", "")),
                    str(citation.get("page_type", "")),
                ]
            )
        )
        for citation in citations
    )

    for variant in variants:
        if not variant:
            continue
        tokens = [token for token in variant.split() if len(token) > 2]
        if variant in citation_text:
            return True
        if tokens:
            hits = sum(1 for token in tokens if token in citation_text)
            if hits / len(tokens) >= 0.66:
                return True

    return False


def _expected_products(prompt: dict) -> list[str]:
    expected_behavior = prompt.get("expected_behavior", "")
    return [
        product_name
        for product_name in official_product_names()
        if product_name.lower() in expected_behavior.lower()
    ]


def _score_prompt(prompt: dict, result: dict) -> dict:
    citations = result.get("source_citations", [])
    answer = result.get("answer", "")
    recommended_products = result.get("recommended_products", [])
    verification_notes = result.get("verification_notes", [])

    expected_products = _expected_products(prompt)
    citation_checks = {
        required: _citation_matches(required, citations)
        for required in prompt.get("must_cite", [])
    }
    routing_ok = not expected_products or any(
        product_name in recommended_products or product_name in answer
        for product_name in expected_products
    )
    conflict_expected = any(flag in {"conflict", "trial"} for flag in prompt.get("flags", []))
    conflict_ok = True
    if conflict_expected:
        lower_answer = answer.lower()
        conflict_ok = (
            any(
                phrase in lower_answer
                for phrase in [
                    "mixed signals",
                    "verify the latest",
                    "verify the current",
                    "public et pages",
                ]
            )
            or bool(verification_notes)
        )

    hallucination_ok = all(
        product_name in official_product_names() for product_name in recommended_products
    )
    total_checks = len(citation_checks) + 3
    passed_checks = sum(citation_checks.values()) + int(routing_ok) + int(conflict_ok) + int(
        hallucination_ok
    )

    return {
        "id": prompt["id"],
        "question": prompt["question"],
        "expected_behavior": prompt["expected_behavior"],
        "answer": answer,
        "recommended_products": recommended_products,
        "source_citations": citations,
        "verification_notes": verification_notes,
        "citation_checks": citation_checks,
        "routing_ok": routing_ok,
        "conflict_ok": conflict_ok,
        "hallucination_ok": hallucination_ok,
        "score": round(passed_checks / total_checks, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ET concierge evaluation prompt pack."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on the number of evaluation prompts to run.",
    )
    parser.add_argument(
        "--fresh-run",
        action="store_true",
        help="Use a unique session prefix for this evaluation run instead of reusing eval::<id> sessions.",
    )
    args = parser.parse_args()

    prompts = load_eval_prompts()
    if args.limit is not None:
        prompts = prompts[: args.limit]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    session_prefix = f"eval::{run_id}" if args.fresh_run else "eval"

    evaluations: list[dict] = []
    for index, prompt in enumerate(prompts, start=1):
        session_id = f"{session_prefix}::{prompt['id']}"
        try:
            response = concierge_service.chat(
                session_id=session_id,
                query=prompt["question"],
            )
            result = _score_prompt(prompt, response)
        except Exception as exc:
            result = {
                "id": prompt["id"],
                "question": prompt["question"],
                "expected_behavior": prompt.get("expected_behavior", ""),
                "answer": f"EVAL ERROR: {type(exc).__name__}: {exc}",
                "recommended_products": [],
                "source_citations": [],
                "verification_notes": [],
                "citation_checks": {
                    required: False for required in prompt.get("must_cite", [])
                },
                "routing_ok": False,
                "conflict_ok": False,
                "hallucination_ok": True,
                "score": 0.0,
            }
        evaluations.append(result)
        print(
            f"[{index}/{len(prompts)}] {prompt['id']} score={result['score']}",
            flush=True,
        )

    average_score = round(
        sum(item["score"] for item in evaluations) / len(evaluations),
        3,
    ) if evaluations else 0.0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_prefix": session_prefix,
        "prompt_count": len(evaluations),
        "average_score": average_score,
        "results": evaluations,
    }

    EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVAL_OUTPUT_DIR / "latest_et_eval_results.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
