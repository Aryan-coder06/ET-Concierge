import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.chatbot.registry import (
    canonical_product_name,
    load_eval_prompts,
    load_nonprime_eval_prompts,
    official_product_names,
)
from app.chatbot.service import concierge_service
from app.chatbot.stage2 import load_stage2_eval_suite


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


def _flatten_stage2_prompts() -> list[dict]:
    suite = load_stage2_eval_suite()
    prompts: list[dict] = []
    for group_name, questions in suite.get("prompt_sets", {}).items():
        for index, question in enumerate(questions, start=1):
            prompts.append(
                {
                    "id": f"{group_name}_{index}",
                    "group": group_name,
                    "question": question,
                }
            )
    return prompts


def _infer_expected_products_from_group(group_name: str) -> list[str]:
    normalized_group = _normalize_text(group_name)
    expected: list[str] = []
    for product_name in official_product_names():
        normalized_product = _normalize_text(product_name)
        product_tokens = [token for token in normalized_product.split() if len(token) > 2]
        group_tokens = [token for token in normalized_group.split() if len(token) > 2]
        if normalized_product in normalized_group or all(token in normalized_group for token in product_tokens[:2]):
            expected.append(product_name)
            continue
        if group_tokens and any(token in normalized_product for token in group_tokens):
            expected.append(product_name)
    deduped: list[str] = []
    for product_name in expected:
        canonical_name = canonical_product_name(product_name) or product_name
        if canonical_name not in deduped:
            deduped.append(canonical_name)
    return deduped


def _flatten_nonprime_prompts() -> list[dict]:
    suite = load_nonprime_eval_prompts()
    prompts: list[dict] = []
    for group_name, questions in suite.get("prompt_sets", {}).items():
        expected_products = _infer_expected_products_from_group(group_name)
        for index, question in enumerate(questions, start=1):
            prompts.append(
                {
                    "id": f"{group_name}_{index}",
                    "group": group_name,
                    "question": question,
                    "expected_products": expected_products,
                }
            )
    return prompts


def _score_stage2_prompt(prompt: dict, result: dict) -> dict:
    question = prompt["question"].lower()
    answer = str(result.get("answer", ""))
    answer_lower = answer.lower()
    recommended_products = result.get("recommended_products", [])
    decision = result.get("decision") or {}
    primary = (decision.get("primary_recommendation") or {}).get("product")
    comparison_rows = result.get("comparison_rows", [])
    bullet_groups = result.get("bullet_groups", [])
    roadmap = result.get("roadmap") or {}
    presentation = result.get("presentation") or {}
    verification_notes = result.get("verification_notes", [])
    visual_hint = result.get("visual_hint")
    navigator_summary = result.get("navigator_summary") or {}
    ui_modules = result.get("ui_modules", [])
    source_citations = result.get("source_citations", [])

    wants_table = any(keyword in question for keyword in ["table", "compare", "comparison", " vs "])
    wants_bullets = any(keyword in question for keyword in ["bullet", "bullets", "three bullets"])
    wants_roadmap = any(keyword in question for keyword in ["roadmap", "7-day", "5-day", "journey", "plan"])
    wants_short = "short answer" in question or "under 150 words" in question
    markets_query = any(keyword in question for keyword in ["sensex", "nifty", "markets", "trading"])
    learning_query = any(keyword in question for keyword in ["learn", "learning", "student", "guided learning", "masterclass"])
    trust_query = any(keyword in question for keyword in ["free trial", "for sure", "confirmation", "execute trades", "broker", "confidence-aware"])

    accuracy = 4 if answer and not answer.startswith("EVAL ERROR") else 1
    groundedness = 5 if source_citations else 2

    format_hits = 0
    format_targets = 0
    if wants_table:
        format_targets += 1
        format_hits += int(bool(comparison_rows))
    if wants_bullets:
        format_targets += 1
        format_hits += int(bool(bullet_groups))
    if wants_roadmap:
        format_targets += 1
        format_hits += int(bool(roadmap.get("steps")))
    if wants_short:
        format_targets += 1
        format_hits += int(len(answer.split()) <= 170)
    if format_targets == 0:
        format_targets = 1
        format_hits = 1
    format_obedience = max(1, min(5, round((format_hits / format_targets) * 5)))

    robotic_phrases = [
        "i'm delighted to assist",
        "i have enough context to guide you now",
        "please verify your fastapi server",
    ]
    tone_quality = 5 if answer and not any(phrase in answer_lower for phrase in robotic_phrases) else 2

    recommendation_consistency = 5
    if primary and primary != "Mixed Path":
        recommendation_consistency = 5 if primary in recommended_products else 2
    if markets_query and visual_hint not in {"markets_tools", "portfolio_view", None}:
        recommendation_consistency = min(recommendation_consistency, 2)
    if learning_query and visual_hint == "markets_tools":
        recommendation_consistency = 1

    realism_of_reasoning = 3
    if "because" in answer_lower or "best fit" in answer_lower or navigator_summary:
        realism_of_reasoning = 4
    if ui_modules and decision.get("next_best_action"):
        realism_of_reasoning = 5

    concierge_feel = 3
    if decision.get("next_best_action") or navigator_summary:
        concierge_feel = 4
    if ui_modules and presentation:
        concierge_feel = 5

    if trust_query and (verification_notes or "verify" in answer_lower or "mixed signals" in answer_lower):
        groundedness = min(5, groundedness + 1)
        accuracy = min(5, accuracy + 1)

    return {
        "id": prompt["id"],
        "group": prompt.get("group"),
        "question": prompt["question"],
        "answer": answer,
        "recommended_products": recommended_products,
        "decision": decision,
        "comparison_rows": comparison_rows,
        "bullet_groups": bullet_groups,
        "visual_hint": visual_hint,
        "ui_modules": ui_modules,
        "rubric_scores": {
            "accuracy": accuracy,
            "groundedness": groundedness,
            "format_obedience": format_obedience,
            "tone_quality": tone_quality,
            "recommendation_consistency": recommendation_consistency,
            "realism_of_reasoning": realism_of_reasoning,
            "concierge_feel": concierge_feel,
        },
        "score": round(
            (
                accuracy
                + groundedness
                + format_obedience
                + tone_quality
                + recommendation_consistency
                + realism_of_reasoning
                + concierge_feel
            )
            / 35,
            3,
        ),
    }


def _score_nonprime_prompt(prompt: dict, result: dict) -> dict:
    stage2_like = _score_stage2_prompt(prompt, result)
    answer = str(result.get("answer", ""))
    answer_lower = answer.lower()
    recommended_products = result.get("recommended_products", [])
    decision = result.get("decision") or {}
    primary = canonical_product_name((decision.get("primary_recommendation") or {}).get("product"))
    expected_products = [
        canonical_product_name(product_name) or product_name
        for product_name in prompt.get("expected_products", [])
    ]
    expected_products = [product for product in expected_products if product]

    explicit_fit = any(
        product_name in recommended_products or product_name == primary or product_name.lower() in answer_lower
        for product_name in expected_products
    )
    overbiased_to_prime = (
        "ET Prime" in recommended_products or primary == "ET Prime"
    ) and expected_products and all(product_name != "ET Prime" for product_name in expected_products)

    stage2_like["expected_products"] = expected_products
    stage2_like["explicit_fit"] = explicit_fit
    stage2_like["overbiased_to_prime"] = overbiased_to_prime

    recommendation_score = 5 if explicit_fit else 2
    if overbiased_to_prime:
        recommendation_score = 1

    stage2_like["rubric_scores"]["recommendation_consistency"] = recommendation_score
    stage2_like["score"] = round(
        (
            stage2_like["rubric_scores"]["accuracy"]
            + stage2_like["rubric_scores"]["groundedness"]
            + stage2_like["rubric_scores"]["format_obedience"]
            + stage2_like["rubric_scores"]["tone_quality"]
            + stage2_like["rubric_scores"]["recommendation_consistency"]
            + stage2_like["rubric_scores"]["realism_of_reasoning"]
            + stage2_like["rubric_scores"]["concierge_feel"]
        )
        / 35,
        3,
    )
    return stage2_like


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
    parser.add_argument(
        "--suite",
        choices=["stage1", "stage2", "nonprime"],
        default="stage1",
        help="Which evaluation suite to run.",
    )
    args = parser.parse_args()

    if args.suite == "stage1":
        prompts = load_eval_prompts()
    elif args.suite == "stage2":
        prompts = _flatten_stage2_prompts()
    else:
        prompts = _flatten_nonprime_prompts()
    if args.limit is not None:
        prompts = prompts[: args.limit]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    session_prefix_root = {
        "stage1": "eval",
        "stage2": "stage2-eval",
        "nonprime": "nonprime-eval",
    }[args.suite]
    session_prefix = f"{session_prefix_root}::{run_id}" if args.fresh_run else session_prefix_root

    evaluations: list[dict] = []
    for index, prompt in enumerate(prompts, start=1):
        session_id = f"{session_prefix}::{prompt['id']}"
        try:
            response = concierge_service.chat(
                session_id=session_id,
                query=prompt["question"],
            )
            if args.suite == "stage1":
                result = _score_prompt(prompt, response)
            elif args.suite == "stage2":
                result = _score_stage2_prompt(prompt, response)
            else:
                result = _score_nonprime_prompt(prompt, response)
        except Exception as exc:
            result = {
                "id": prompt["id"],
                "question": prompt["question"],
                "answer": f"EVAL ERROR: {type(exc).__name__}: {exc}",
                "recommended_products": [],
                "source_citations": [],
                "verification_notes": [],
                "score": 0.0,
            }
            if args.suite == "stage1":
                result.update(
                    {
                        "expected_behavior": prompt.get("expected_behavior", ""),
                        "citation_checks": {
                            required: False for required in prompt.get("must_cite", [])
                        },
                        "routing_ok": False,
                        "conflict_ok": False,
                        "hallucination_ok": True,
                    }
                )
            elif args.suite == "stage2":
                result["rubric_scores"] = {
                    "accuracy": 1,
                    "groundedness": 1,
                    "format_obedience": 1,
                    "tone_quality": 1,
                    "recommendation_consistency": 1,
                    "realism_of_reasoning": 1,
                    "concierge_feel": 1,
                }
            else:
                result["rubric_scores"] = {
                    "accuracy": 1,
                    "groundedness": 1,
                    "format_obedience": 1,
                    "tone_quality": 1,
                    "recommendation_consistency": 1,
                    "realism_of_reasoning": 1,
                    "concierge_feel": 1,
                }
                result["expected_products"] = prompt.get("expected_products", [])
                result["explicit_fit"] = False
                result["overbiased_to_prime"] = False
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
        "suite": args.suite,
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
