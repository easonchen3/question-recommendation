# Optimization Summary

## What Changed

### 1. Prompt optimization

Updated [prompting.py](/D:/Code/questio_recommendation/src/next_question_reco/prompting.py) to strengthen next-step priority rules:

- `故障诊断`:
  - first confirm impact scope
  - then align failure code / alarm / fault start time
  - then do cross-domain verification
  - only then go into deeper technical detail
- `智能问数`:
  - first ask about analysis strategy
  - then choose split dimensions / time windows / thresholds
  - only then ask for TopN or detailed values
- `多意图`:
  - prefer a question that best pushes the current execution state forward
  - for `故障诊断 + 智能问数`, prefer drill-down that helps isolation instead of pure detail lookup

### 2. Evaluation-set cleanup

Updated [generate_eval_set.py](/D:/Code/questio_recommendation/evals/generate_eval_set.py) to use scenario-specific slot pools:

- mobile scenarios now only sample mobile entities
- fixed-broadband scenarios now only sample fixed-network entities
- transport/core scenarios use their own network elements
- removed cross-domain contamination such as `5g_attach_failure` mixed with `OLT/ONU`

## Results

### Baseline

- Report: [qwen35_deepseek_eval_report.json](/D:/Code/questio_recommendation/reports/qwen35_deepseek_eval_report.json)
- Dataset: `next_step_eval_v1.jsonl`
- Top3 Accuracy: `80.83%`
- Single-intent: `81.90%`
- Multi-intent: `73.33%`

### Prompt optimized on old dataset

- Report: [qwen35_deepseek_eval_report_v1_prompt_optimized.json](/D:/Code/questio_recommendation/reports/qwen35_deepseek_eval_report_v1_prompt_optimized.json)
- Dataset: `next_step_eval_v1.jsonl`
- Top3 Accuracy: `81.67%`
- Single-intent: `84.76%`
- Multi-intent: `60.00%`

Interpretation:

- Prompt optimization brought a small overall gain on the old dataset: `+0.84%`
- Single-intent improved clearly
- Multi-intent regressed, which means the current multi-intent rule is still not strong enough

### Prompt optimized on cleaned dataset

- Report: [qwen35_deepseek_eval_report_v2.json](/D:/Code/questio_recommendation/reports/qwen35_deepseek_eval_report_v2.json)
- Dataset: [next_step_eval_v2.jsonl](/D:/Code/questio_recommendation/evals/next_step_eval_v2.jsonl)
- Top3 Accuracy: `78.33%`
- Single-intent: `79.05%`
- Multi-intent: `73.33%`

Interpretation:

- The cleaned dataset is more natural and has less synthetic noise
- But it is not directly comparable to the old dataset as a pure “improvement percentage”
- This result is better viewed as a more realistic post-cleanup baseline

## Key Conclusion

- Prompt optimization works, but the gain is modest and concentrated in single-intent cases
- Dataset cleanup was necessary and successfully removed telecom cross-domain noise
- The next bottleneck is still multi-intent recommendation quality, especially `故障诊断 + 智能问数`

## Recommended Next Step

The next high-value iteration should focus on multi-intent decision policy:

1. Explicitly infer a dominant action family before generating questions
2. Add an intermediate label such as:
   - `范围确认`
   - `失败码时间对齐`
   - `跨域验证`
   - `时段拆分`
   - `阈值过滤`
   - `TopN 明细`
3. Force the model to prefer higher-priority action labels when multiple labels are plausible
