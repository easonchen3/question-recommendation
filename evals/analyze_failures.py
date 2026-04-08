from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import Workbook


def load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def intent_key(intent_value: Any) -> str:
    if isinstance(intent_value, list):
        return "+".join(intent_value)
    return str(intent_value)


def classify_failure(result: dict[str, Any]) -> list[str]:
    text = " ".join(result.get("judge", {}).get("issues", [])).lower()
    tags: list[str] = []
    if "是否继续" in text or "确认式" in text:
        tags.append("confirmation_style")
    if "处理步骤" in text or "使用指导" in text or "可执行" in text or "优先查看" in text:
        tags.append("actionability_gap")
    if "知识问答" in text or "知识深化" in text or "知识转化" in text:
        tags.append("knowledge_alignment_gap")
    if "过于具体" in text or "区域" in text or "设备" in text:
        tags.append("over_specific")
    if "验证" in text and "偏向" in text:
        tags.append("over_verification")
    return tags or ["other"]


def build_summary(failed: list[dict[str, Any]]) -> dict[str, Any]:
    by_intent = Counter(intent_key(item["intent"]) for item in failed)
    by_scenario = Counter(item["meta"]["scenario_family"] for item in failed)
    by_difficulty = Counter(item["difficulty"] for item in failed)
    by_tag = Counter(tag for item in failed for tag in classify_failure(item))

    return {
        "failed_count": len(failed),
        "by_intent": dict(by_intent),
        "by_scenario": dict(by_scenario),
        "by_difficulty": dict(by_difficulty),
        "by_tag": dict(by_tag),
    }


def build_markdown(report_path: Path, summary: dict[str, Any], failed: list[dict[str, Any]]) -> str:
    lines = [
        "# Failure Case Analysis",
        "",
        f"- Source report: `{report_path}`",
        f"- Failed cases: `{summary['failed_count']}`",
        "",
        "## Summary",
        "",
        f"- By intent: `{summary['by_intent']}`",
        f"- By scenario: `{summary['by_scenario']}`",
        f"- By difficulty: `{summary['by_difficulty']}`",
        f"- By tag: `{summary['by_tag']}`",
        "",
        "## Key Findings",
        "",
        "- 失败样本如果高度集中在解释型场景，说明当前 Prompt 仍然偏向验证式下钻，而不是把解释转成操作指导。",
        "- 如果出现大量 `confirmation_style`，说明生成问题过多使用“是否继续……”句式，缺少更直接的推进式提问。",
        "- 如果出现大量 `actionability_gap`，说明模型没有把当前说明落到“先看什么、后看什么、步骤顺序、优先查看对象和信号”这类问题上。",
        "",
        "## Sample Failures",
        "",
    ]

    for item in failed[:10]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Intent: `{intent_key(item['intent'])}`",
                f"- Scenario: `{item['meta']['scenario_family']}`",
                f"- Tags: `{classify_failure(item)}`",
                f"- Generated: `{item['generated_questions']}`",
                f"- Reference: `{item['reference_top3']}`",
                f"- Judge issues: `{item.get('judge', {}).get('issues', [])}`",
                "",
            ]
        )
    return "\n".join(lines)


def write_failure_excel(path: Path, failed: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "失败样本"
    worksheet.append(
        [
            "id",
            "intent",
            "difficulty",
            "scenario_family",
            "failure_tags",
            "generated_questions",
            "reference_top3",
            "judge_issues",
            "judge_overall_score",
            "final_score",
        ]
    )
    for item in failed:
        worksheet.append(
            [
                item.get("id", ""),
                intent_key(item.get("intent")),
                item.get("difficulty", ""),
                item.get("meta", {}).get("scenario_family", ""),
                "\n".join(classify_failure(item)),
                "\n".join(item.get("generated_questions", [])),
                "\n".join(item.get("reference_top3", [])),
                "\n".join(item.get("judge", {}).get("issues", [])),
                item.get("judge", {}).get("overall_score", ""),
                item.get("final_score", ""),
            ]
        )
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze failed cases from an evaluation report.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--markdown-output", required=True)
    parser.add_argument("--excel-output", required=True)
    args = parser.parse_args()

    report_path = Path(args.report)
    report = load_report(report_path)
    failed = [item for item in report.get("results", []) if item.get("top3_hit") == 0]
    summary = build_summary(failed)

    markdown = build_markdown(report_path, summary, failed)
    markdown_path = Path(args.markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")

    excel_path = Path(args.excel_output)
    write_failure_excel(excel_path, failed)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved markdown to: {markdown_path}")
    print(f"Saved excel to: {excel_path}")


if __name__ == "__main__":
    main()
