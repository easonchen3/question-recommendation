# Qwen + DeepSeek Failure Case Analysis

## Summary

- Evaluation report: [qwen35_deepseek_eval_report.json](/D:/Code/questio_recommendation/reports/qwen35_deepseek_eval_report.json)
- Failed cases: [qwen35_deepseek_failed_cases.jsonl](/D:/Code/questio_recommendation/reports/qwen35_deepseek_failed_cases.jsonl)
- Total cases: `120`
- Top3 Accuracy: `80.83%`
- Failed cases: `23`
- Single-intent accuracy: `81.90%`
- Multi-intent accuracy: `73.33%`

## Failure Distribution

- By difficulty:
  - `easy`: 3
  - `medium`: 14
  - `hard`: 6
- By intent:
  - `知识问答`: 2
  - `知识问答+故障诊断`: 1
  - `故障诊断`: 11
  - `故障诊断+智能问数`: 3
  - `智能问数`: 6
- By scenario:
  - `drop_rate_drilldown`: 6
  - `volte_call_drop`: 5
  - `5g_attach_failure`: 4
  - `nsa_sa_compare`: 2
  - `pon_mass_offline`: 2
  - `ip_backhaul_loss`: 2
  - `pon_optical_power`: 1
  - `sms_delay`: 1

## Main Findings

### 1. The largest error bucket is action-direction mismatch

Most failed cases are not obviously irrelevant. They are usually reasonable next-step questions, but they do not match the expected action family.

Typical pattern:

- Reference prefers: `聚合/分组/按站点小区确认/失败码时间对齐/跨域交叉验证`
- Model generates: `更细的技术验证` or `更具体的数据查询`

Representative cases:

- `NQ-001`, `NQ-004`: `nsa_sa_compare`
  - Model moved toward low-level implementation details such as MML commands or signal IEs.
  - Reference expected field-oriented troubleshooting guidance such as which side to check first and how to use KPI/alarms in现场排障.
- `NQ-097` to `NQ-102`: `drop_rate_drilldown`
  - Model asked for TopN stations and concrete values.
  - Reference expected analysis-strategy questions such as `先按时段拆分` or `先按阈值过滤`.

Interpretation:

- The current prompt still allows the model to optimize for “more specific” instead of “more aligned with the intended next action type”.
- The reference answers also encode a fairly narrow action style, especially in `智能问数`.

### 2. In fault diagnosis, the model tends to over-focus on one technical side

This appears mainly in `volte_call_drop` and `5g_attach_failure`.

Typical pattern:

- Model focuses on one domain, usually `无线侧细节验证` or `链路/设备细节`
- Reference prefers multi-domain next steps, such as:
  - `IMS + 媒体面 + 回传` cross-check
  - `失败码 Top 原因 + 时间对齐`
  - `站点/小区范围确认`
  - `厂家/版本聚合`

Representative cases:

- `NQ-045`, `NQ-046`, `NQ-049`, `NQ-051`, `NQ-052`: `volte_call_drop`
  - Model stayed in radio-side diagnosis.
  - Reference expected broader closure actions and cross-domain evidence gathering.
- `NQ-038`, `NQ-040`, `NQ-041`, `NQ-044`: `5g_attach_failure`
  - Model often switched to correlation-style questions or transport-side details.
  - Reference expected `失败码时间对齐`, `站点/扇区范围确认`, `厂家版本聚合`.

Interpretation:

- For `故障诊断`, the prompt needs a stronger priority order.
- Right now, “reasonable next technical check” is often enough for the generator, but the evaluation expects “best next isolation move”.

### 3. Multi-intent cases are noticeably harder

- Single-intent accuracy: `81.90%`
- Multi-intent accuracy: `73.33%`

The weakest bucket is `故障诊断 + 智能问数`.

Representative cases:

- `NQ-040`: model moved to transport/detail correlation, while reference wanted `聚合分析 + 失败码 Top + 站点范围确认`
- `NQ-056`: model asked for timestamp-level verification, while reference wanted `楼宇/片区聚合` and `局端/末端隔离`
- `NQ-072`: model asked for direct data pull, while reference wanted `高峰前后对比` and `容量瓶颈 vs 偶发抖动` judgment

Interpretation:

- Multi-intent samples require the model to choose the dominant execution path.
- The current prompt mentions multi-intent handling, but it does not yet provide a strong enough decision policy.

### 4. There is dataset noise from cross-domain variable mixing

At least 4 failed cases contain obvious cross-domain contamination inside mobile scenarios, for example `5g attach` or `drop rate` cases mixed with `OLT/ONU` concepts:

- `NQ-040`
- `NQ-041`
- `NQ-044`
- `NQ-098`

This is likely caused by the current synthetic case generator using a shared slot pool across scenarios.

Impact:

- These cases are still machine-readable, but less natural for telecom experts.
- They also increase evaluation volatility because both generated answers and references can drift toward awkward mixed-domain reasoning.

Interpretation:

- Part of the current failure count is not purely a model capability problem.
- Some failures are amplified by synthetic data quality issues.

## Representative Failure Cases

### Case A: Knowledge QA becomes too low-level

- ID: `NQ-001`
- Scenario: `nsa_sa_compare`
- Failure mode:
  - Generated question asked for MML commands and specific signaling fields.
  - Reference expected “what should the engineer check first in current-field troubleshooting”.
- Diagnosis:
  - Model optimized for technical depth, not for operational next-step framing.

### Case B: Fault diagnosis lacks cross-domain closure

- ID: `NQ-045`
- Scenario: `volte_call_drop`
- Failure mode:
  - Generated question stayed on handover failure cause breakdown.
  - Reference expected broader closure actions including terminal grouping, IMS/media verification, and radio/backhaul ordering.
- Diagnosis:
  - Model is too willing to continue in one subsystem instead of asking the best next isolation question.

### Case C: Analytics asks for raw TopN too early

- ID: `NQ-097`
- Scenario: `drop_rate_drilldown`
- Failure mode:
  - Generated question directly requested Top10 stations and values.
  - Reference expected strategy-level next steps: split by peak/non-peak, align accompanying indicators, apply threshold filtering.
- Diagnosis:
  - Model confuses “继续取数” with “最优下一步分析动作”.

### Case D: Multi-intent case lacks dominant intent selection

- ID: `NQ-040`
- Scenario: `5g_attach_failure`
- Intent: `故障诊断 + 智能问数`
- Failure mode:
  - Generated question leaned into detailed correlation checks.
  - Reference expected a diagnosis-first action sequence with aggregation and failure-code alignment.
- Diagnosis:
  - Model did not select a clear primary execution path.

### Case E: Data generator created unnatural context

- ID: `NQ-041`
- Scenario: `5g_attach_failure`
- Failure mode:
  - Mobile attach failure case contains `OLT` in the expected reference direction.
- Diagnosis:
  - This is a dataset-generation artifact, not just a model generation issue.

## Recommended Next Actions

### Prompt Improvements

- Add an explicit priority ladder for `故障诊断`:
  - `先确认影响范围`
  - `再对齐失败码/关键告警与故障开始时刻`
  - `再做跨域交叉验证`
  - `最后才做更细的网元/信令深挖`
- Add an explicit priority ladder for `智能问数`:
  - `先决定分析策略`
  - `再决定分组维度/时间窗口/阈值`
  - `最后才请求具体 TopN 或明细数据`
- Add a hard constraint:
  - If one candidate is “strategy-confirming next step” and another is “data-detail request”, prefer the former.

### Evaluation Set Improvements

- Split slot dictionaries by scenario family instead of using one shared pool.
- For mobile scenarios, ban fixed-network entities such as `OLT/ONU/PON`.
- For fixed-network scenarios, ban mobile-core entities unless the sample explicitly models cross-domain dependency.

### Reference Answer Improvements

- Expand each sample from 3 reference questions to:
  - `3 canonical references`
  - `3-5 acceptable paraphrase or same-action variants`
- Or replace pure reference-text matching with an intermediate `action label`, such as:
  - `范围确认`
  - `失败码时间对齐`
  - `厂家/版本聚合`
  - `终端/业务分群`
  - `时段拆分`
  - `阈值过滤`

This would reduce false negatives where the model asks a valid next-step question but in a different wording or slightly different granularity.

## Priority Recommendation

The highest-value next step is:

1. Clean the synthetic generator to remove cross-domain contamination.
2. Strengthen the diagnosis and analytics priority rules in the prompt.
3. Re-run the same evaluation and compare:
   - overall Top3 Accuracy
   - multi-intent Top3 Accuracy
   - `drop_rate_drilldown` and `volte_call_drop` scenario accuracy
