from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "next_step_question_recommendation_system_prompt.txt"
USER_PROMPT_TEMPLATE_PATH = PROMPTS_DIR / "next_step_question_recommendation_user_prompt.txt"


RECOMMENDATION_SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
USER_PROMPT_TEMPLATE = USER_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def _serialize_prompt_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def build_recommendation_user_prompt(case_input: Mapping[str, Any]) -> str:
    replacements = {
        "{original_question}": _serialize_prompt_value(case_input.get("original_question")),
        "{rewritten_question}": _serialize_prompt_value(case_input.get("rewritten_question")),
        "{intent}": _serialize_prompt_value(case_input.get("intent")),
        "{user_profile}": _serialize_prompt_value(case_input.get("user_profile") or []),
        "{current_plan}": _serialize_prompt_value(case_input.get("current_plan") or []),
        "{execution_result}": _serialize_prompt_value(case_input.get("execution_result")),
        "{history_high_freq_questions}": _serialize_prompt_value(case_input.get("history_high_freq_questions") or []),
    }

    prompt = USER_PROMPT_TEMPLATE
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt
