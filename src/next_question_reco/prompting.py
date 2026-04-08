from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
GENERATION_PROMPT_ARCHIVE_PATH = PROMPTS_DIR / "generation_prompt_archive.md"
EVALUATION_PROMPT_ARCHIVE_PATH = PROMPTS_DIR / "evaluation_prompt_archive.md"


def _extract_markdown_code_block(markdown: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\s+```[a-zA-Z0-9_-]*\n(.*?)\n```"
    match = re.search(pattern, markdown, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Cannot find prompt section '{heading}' in markdown archive.")
    return match.group(1).strip()


GENERATION_PROMPT_ARCHIVE = GENERATION_PROMPT_ARCHIVE_PATH.read_text(encoding="utf-8")
EVALUATION_PROMPT_ARCHIVE = EVALUATION_PROMPT_ARCHIVE_PATH.read_text(encoding="utf-8")

RECOMMENDATION_SYSTEM_PROMPT = _extract_markdown_code_block(GENERATION_PROMPT_ARCHIVE, "System Prompt")
USER_PROMPT_TEMPLATE = _extract_markdown_code_block(GENERATION_PROMPT_ARCHIVE, "User Prompt Template")
JUDGE_SYSTEM_PROMPT = _extract_markdown_code_block(EVALUATION_PROMPT_ARCHIVE, "Judge System Prompt")


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
