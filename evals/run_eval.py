from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from generate_eval_set import DEFAULT_DATASET_PATH, generate_dataset, load_dataset, print_summary
from next_question_reco import JUDGE_SYSTEM_PROMPT, RECOMMENDATION_SYSTEM_PROMPT, build_recommendation_user_prompt


@dataclass
class ModelConfig:
    model: str
    api_key: str
    base_url: str
    temperature: float
    timeout: float


def load_config_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def nested_get(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def intent_key(intent_value: Any) -> str:
    if isinstance(intent_value, list):
        return "+".join(intent_value)
    return str(intent_value)


def safe_json_loads(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def extract_numeric_field(text: str, field: str) -> float:
    patterns = [
        rf'"{re.escape(field)}"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        rf"{re.escape(field)}\s*:\s*([0-9]+(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return 0.0


def extract_judge_payload_fallback(text: str) -> dict[str, Any]:
    return {
        "dimension_scores": {
            "relevance": extract_numeric_field(text, "relevance"),
            "next_step": extract_numeric_field(text, "next_step"),
            "skill_alignment": extract_numeric_field(text, "skill_alignment"),
            "telecom_fit": extract_numeric_field(text, "telecom_fit"),
            "non_redundancy": extract_numeric_field(text, "non_redundancy"),
        },
        "top3_hit": int(extract_numeric_field(text, "top3_hit")),
        "matched_questions": [],
        "overall_score": extract_numeric_field(text, "overall_score"),
        "strengths": [],
        "issues": [],
    }


def parse_questions(raw_text: str) -> list[str]:
    payload = safe_json_loads(raw_text)
    candidates = payload.get("next_questions") or payload.get("questions") or payload.get("top3") or []
    parsed: list[str] = []

    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, str):
                value = item.strip()
            elif isinstance(item, dict):
                value = str(item.get("question", "")).strip()
            else:
                value = str(item).strip()
            if value:
                parsed.append(value)
    if parsed:
        return parsed[:3]

    lines = [line.strip("-* 1234567890. \t") for line in raw_text.splitlines()]
    return [line for line in lines if line.endswith(("?", "？"))][:3]


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a, b=b).ratio()


def normalize_text(text: str) -> str:
    table = str.maketrans("", "", " \t\r\n，。；：、,.!?？！()（）[]【】\"'")
    return text.translate(table).lower()


def exact_top3_hit(predictions: list[str], references: list[str]) -> tuple[int, list[dict[str, str]]]:
    normalized_refs = {normalize_text(ref): ref for ref in references}
    matched: list[dict[str, str]] = []
    for prediction in predictions:
        key = normalize_text(prediction)
        if key in normalized_refs:
            matched.append({"generated": prediction, "reference": normalized_refs[key]})
    return (1 if matched else 0, matched)


def score_format(questions: list[str]) -> float:
    if len(questions) != 3:
        return 0.0
    punctuation = sum(q.endswith(("?", "？")) for q in questions) / 3
    length_ok = sum(8 <= len(q) <= 80 for q in questions) / 3
    return round(((punctuation + length_ok) / 2) * 10, 2)


def score_diversity(questions: list[str]) -> float:
    if len(questions) < 2:
        return 0.0
    values = []
    for idx in range(len(questions)):
        for jdx in range(idx + 1, len(questions)):
            values.append(1 - similarity(questions[idx], questions[jdx]))
    return round(max(0.0, mean(values)) * 10, 2)


def score_history_dedup(questions: list[str], history: list[str]) -> float:
    if not questions:
        return 0.0
    if not history:
        return 10.0
    overlaps = []
    for question in questions:
        overlaps.append(max(similarity(question, item) for item in history))
    return round(max(0.0, (1 - mean(overlaps))) * 10, 2)


def blend_score(rule_scores: dict[str, float], judge_score: float) -> float:
    rules = (
        rule_scores["format"] * 0.30
        + rule_scores["diversity"] * 0.35
        + rule_scores["history_dedup"] * 0.35
    )
    return round(rules * 0.30 + judge_score * 0.70, 2)


class OpenAICompatibleClient:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }
        fallback = {
            "model": self.config.model,
            "messages": payload["messages"],
            "temperature": self.config.temperature,
        }

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.client.post(url, json=payload)
                if response.status_code >= 400:
                    response = await self.client.post(url, json=fallback)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected chat_json failure")


async def judge_case(client: OpenAICompatibleClient, case: dict[str, Any], generated_questions: list[str]) -> dict[str, Any]:
    payload = {
        "input": case["input"],
        "generated_next_questions": generated_questions,
        "reference_top3": case["expected"]["top3"],
        "evaluation_focus": case["expected"]["evaluation_focus"],
    }
    response_text = await client.chat_json(JUDGE_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False, indent=2))
    parsed = safe_json_loads(response_text)
    if not parsed:
        parsed = extract_judge_payload_fallback(response_text)
    scores = parsed.get("dimension_scores") or {}
    return {
        "dimension_scores": {
            "relevance": float(scores.get("relevance", 0)),
            "next_step": float(scores.get("next_step", 0)),
            "skill_alignment": float(scores.get("skill_alignment", 0)),
            "telecom_fit": float(scores.get("telecom_fit", 0)),
            "non_redundancy": float(scores.get("non_redundancy", 0)),
        },
        "top3_hit": int(parsed.get("top3_hit", 0)),
        "matched_questions": parsed.get("matched_questions") or [],
        "overall_score": float(parsed.get("overall_score", 0)),
        "strengths": parsed.get("strengths") or [],
        "issues": parsed.get("issues") or [],
    }


async def evaluate_one(
    semaphore: asyncio.Semaphore,
    gen_client: OpenAICompatibleClient | None,
    judge_client: OpenAICompatibleClient | None,
    case: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    async with semaphore:
        prompt = build_recommendation_user_prompt(case["input"])
        if dry_run:
            generated_raw = json.dumps({"next_questions": case["expected"]["top3"]}, ensure_ascii=False)
        else:
            if gen_client is None:
                raise ValueError("Generation client is required when dry_run is False.")
            generated_raw = await gen_client.chat_json(RECOMMENDATION_SYSTEM_PROMPT, prompt)

        generated_questions = parse_questions(generated_raw)
        history = case["input"].get("history_high_freq_questions") or []
        exact_hit, exact_matches = exact_top3_hit(generated_questions, case["expected"]["top3"])
        rule_scores = {
            "format": score_format(generated_questions),
            "diversity": score_diversity(generated_questions),
            "history_dedup": score_history_dedup(generated_questions, history),
        }

        if dry_run:
            judge = {
                "dimension_scores": {
                    "relevance": 9.5,
                    "next_step": 9.5,
                    "skill_alignment": 9.5,
                    "telecom_fit": 9.5,
                    "non_redundancy": 9.0,
                },
                "top3_hit": 1,
                "matched_questions": exact_matches or [{"generated": case["expected"]["top3"][0], "reference": case["expected"]["top3"][0]}],
                "overall_score": 9.4,
                "strengths": ["dry-run 使用参考答案模拟输出"],
                "issues": [],
            }
        else:
            if judge_client is None:
                raise ValueError("Judge client is required when dry_run is False.")
            judge = await judge_case(judge_client, case, generated_questions)

        top3_hit = 1 if exact_hit == 1 or judge["top3_hit"] == 1 else 0
        final_score = blend_score(rule_scores, judge["overall_score"])
        return {
            "id": case["id"],
            "intent": case["intent"],
            "difficulty": case["difficulty"],
            "meta": case["meta"],
            "generated_raw": generated_raw,
            "generated_questions": generated_questions,
            "reference_top3": case["expected"]["top3"],
            "exact_top3_hit": exact_hit,
            "exact_matches": exact_matches,
            "top3_hit": top3_hit,
            "rule_scores": rule_scores,
            "judge": judge,
            "final_score": final_score,
        }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_intent: dict[str, list[float]] = {}
    by_difficulty: dict[str, list[float]] = {}
    by_scenario: dict[str, list[float]] = {}
    top3_by_intent: dict[str, list[int]] = {}
    top3_by_difficulty: dict[str, list[int]] = {}
    top3_by_mode: dict[str, list[int]] = {}
    for item in results:
        key = intent_key(item["intent"])
        by_intent.setdefault(key, []).append(item["final_score"])
        by_difficulty.setdefault(item["difficulty"], []).append(item["final_score"])
        by_scenario.setdefault(item["meta"]["scenario_family"], []).append(item["final_score"])
        top3_by_intent.setdefault(key, []).append(item["top3_hit"])
        top3_by_difficulty.setdefault(item["difficulty"], []).append(item["top3_hit"])
        top3_by_mode.setdefault(item["meta"].get("intent_mode", "single"), []).append(item["top3_hit"])

    return {
        "count": len(results),
        "top3_accuracy": round(mean(item["top3_hit"] for item in results), 4),
        "average_final_score": round(mean(item["final_score"] for item in results), 2),
        "average_rule_scores": {
            "format": round(mean(item["rule_scores"]["format"] for item in results), 2),
            "diversity": round(mean(item["rule_scores"]["diversity"] for item in results), 2),
            "history_dedup": round(mean(item["rule_scores"]["history_dedup"] for item in results), 2),
        },
        "average_judge_overall": round(mean(item["judge"]["overall_score"] for item in results), 2),
        "by_intent": {k: round(mean(v), 2) for k, v in by_intent.items()},
        "by_difficulty": {k: round(mean(v), 2) for k, v in by_difficulty.items()},
        "by_scenario": {k: round(mean(v), 2) for k, v in sorted(by_scenario.items())},
        "top3_accuracy_by_intent": {k: round(mean(v), 4) for k, v in top3_by_intent.items()},
        "top3_accuracy_by_difficulty": {k: round(mean(v), 4) for k, v in top3_by_difficulty.items()},
        "top3_accuracy_by_intent_mode": {k: round(mean(v), 4) for k, v in top3_by_mode.items()},
    }


def resolve_api_key(api_key: str | None, api_key_env: str | None) -> str:
    if api_key:
        return api_key
    if api_key_env:
        value = os.getenv(api_key_env, "")
        if value:
            return value
    raise ValueError(f"Missing API key. Checked api_key and environment variable: {api_key_env}")


def build_model_config(
    model: str,
    base_url: str,
    api_key_env: str | None,
    temperature: float,
    timeout: float,
    api_key: str | None = None,
) -> ModelConfig:
    api_key = resolve_api_key(api_key, api_key_env)
    if not api_key:
        raise ValueError(f"Missing API key in environment variable: {api_key_env}")
    return ModelConfig(model=model, api_key=api_key, base_url=base_url, temperature=temperature, timeout=timeout)


def resolve_model_settings(config: dict[str, Any], section: str, *, dry_run: bool) -> dict[str, Any]:
    settings = nested_get(config, "evaluate", section, default={}) or {}
    if dry_run:
        return settings
    if not settings:
        raise ValueError(f"Missing evaluate.{section} in config file.")
    required = ("model", "base_url", "temperature")
    missing = [key for key in required if settings.get(key) is None]
    if missing:
        raise ValueError(f"Missing fields in evaluate.{section}: {', '.join(missing)}")
    if settings.get("api_key") is None and settings.get("api_key_env") is None:
        raise ValueError(f"evaluate.{section} must provide api_key or api_key_env")
    return settings


def resolve_runtime_args(cli_args: argparse.Namespace) -> argparse.Namespace:
    config = load_config_file(cli_args.config)

    mode = coalesce(cli_args.mode, config.get("mode"), "evaluate")
    dataset = coalesce(cli_args.dataset, nested_get(config, "evaluate", "dataset"), DEFAULT_DATASET_PATH)
    generate_output = coalesce(cli_args.generate_output, nested_get(config, "generate", "output"), dataset)
    eval_output = coalesce(cli_args.output, nested_get(config, "evaluate", "output"), "reports/eval_report.json")
    concurrency = int(coalesce(cli_args.concurrency, nested_get(config, "evaluate", "concurrency"), 8))
    max_cases = int(coalesce(cli_args.max_cases, nested_get(config, "evaluate", "max_cases"), 0))
    timeout = float(coalesce(cli_args.timeout, nested_get(config, "evaluate", "timeout"), 120.0))
    dry_run = bool(cli_args.dry_run or bool(nested_get(config, "evaluate", "dry_run", default=False)))
    generation_model = resolve_model_settings(config, "generation_model", dry_run=dry_run)
    judge_model = resolve_model_settings(config, "judge_model", dry_run=dry_run)

    return argparse.Namespace(
        config=cli_args.config,
        mode=mode,
        dataset=dataset,
        generate_output=generate_output,
        output=eval_output,
        concurrency=concurrency,
        max_cases=max_cases,
        dry_run=dry_run,
        timeout=timeout,
        generation_model=generation_model,
        judge_model=judge_model,
    )


async def run_async(args: argparse.Namespace) -> dict[str, Any]:
    dataset = load_dataset(args.dataset)
    if args.max_cases:
        dataset = dataset[: args.max_cases]
    if not dataset:
        raise ValueError(f"Dataset is empty: {args.dataset}")

    gen_client: OpenAICompatibleClient | None = None
    judge_client: OpenAICompatibleClient | None = None
    if not args.dry_run:
        gen_client = OpenAICompatibleClient(
            build_model_config(
                args.generation_model["model"],
                args.generation_model["base_url"],
                args.generation_model.get("api_key_env"),
                float(args.generation_model["temperature"]),
                args.timeout,
                api_key=args.generation_model.get("api_key"),
            )
        )
        judge_client = OpenAICompatibleClient(
            build_model_config(
                args.judge_model["model"],
                args.judge_model["base_url"],
                args.judge_model.get("api_key_env"),
                float(args.judge_model["temperature"]),
                args.timeout,
                api_key=args.judge_model.get("api_key"),
            )
        )

    semaphore = asyncio.Semaphore(args.concurrency)
    try:
        tasks = [evaluate_one(semaphore, gen_client, judge_client, case, args.dry_run) for case in dataset]
        results = await asyncio.gather(*tasks)
    finally:
        if gen_client is not None:
            await gen_client.close()
        if judge_client is not None:
            await judge_client.close()

    return {
        "config": {
            "dataset": args.dataset,
            "dry_run": args.dry_run,
            "concurrency": args.concurrency,
            "gen_model": args.generation_model.get("model"),
            "judge_model": args.judge_model.get("model"),
        },
        "summary": aggregate(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run next-step-question dataset generation and evaluation.")
    parser.add_argument("--config")
    parser.add_argument("--mode", choices=["generate", "evaluate", "generate_and_evaluate"])
    parser.add_argument("--generate-output")
    parser.add_argument("--dataset")
    parser.add_argument("--output")
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float)

    cli_args = parser.parse_args()
    args = resolve_runtime_args(cli_args)

    if args.mode in {"generate", "generate_and_evaluate"}:
        generation_summary = generate_dataset(args.generate_output)
        print_summary(generation_summary)
        if args.mode == "generate":
            return
        args.dataset = args.generate_output

    report = asyncio.run(run_async(args))

    output_path = Path(args.output)
    ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Saved report to: {output_path}")


if __name__ == "__main__":
    main()
