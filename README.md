# 下一步问题推荐评测框架

这个目录提供一套面向通信领域 Agent 的“下一步问题推荐”方案，包含：

- 推荐 Prompt 设计
- 120 条评测集样本
- 支持生成模型与评测模型分别配置的并发评测脚本

## 目录结构

```text
prompts/
  next_step_question_recommendation_prompt.md
src/
  next_question_reco/
    __init__.py
    prompting.py
evals/
  generate_eval_set.py
  run_eval.py
  next_step_eval_v1.jsonl
requirements.txt
```

## 推荐 Prompt 设计要点

这套 Prompt 强制约束模型输出“下一步问题”，而不是泛泛的相关问题，核心原则有：

- 必须紧贴当前问题、当前意图、当前执行结果和当前计划
- 问题要能推动下一轮 Agent 真正继续分析、定位、确认、下钻或决策
- 必须与通信场景一致，不能跳出当前业务上下文
- 要避免与历史高频问题过于相似
- 只输出 Top3

Prompt 模板见 [prompts/next_step_question_recommendation_prompt.md](/D:/Code/questio_recommendation/prompts/next_step_question_recommendation_prompt.md)。

## 评测集设计

评测集共 120 条，覆盖三类意图：

- `知识问答`：36 条
- `故障诊断`：48 条
- `智能问数`：36 条

难度分布：

- `easy`：30 条
- `medium`：66 条
- `hard`：24 条

设计逻辑：

- 使用通信领域常见场景，如 5G 注册失败、VoLTE 掉话、PON 大面积离线、回传丢包、区域流量突增、投诉与 KPI 关联分析等
- 每条样本都包含原始问题、改写问题、意图、用户特征、当前计划、执行结果、历史高频问题
- 其中包含一部分多意图样本，用于模拟真实场景中 `故障诊断+智能问数`、`知识问答+故障诊断` 等复合意图输入
- Gold 参考答案为“合理的下一步问题 Top3”，不是唯一标准答案，评测时使用 LLM-as-a-Judge 做语义判断
- 保证部分样本缺省用户特征、缺省历史问题或计划信息，模拟真实线上输入质量

## 评测口径

主指标为 `Top3 Accuracy`：

- 每条样本生成 3 个下一步问题
- 只要生成的 3 个问题里，有 1 个与参考答案 Top3 中任意一个语义命中，这条样本就记为正确
- 全部样本中正确样本的占比，就是 `Top3 Accuracy`

脚本同时保留规则分和 LLM Judge 评分，用于辅助分析模型问题，但主指标以 `Top3 Accuracy` 为准。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 生成评测集

```bash
python evals/generate_eval_set.py --output evals/next_step_eval_v1.jsonl
```

## 运行评测

脚本支持生成模型和评测模型分别配置，均采用 OpenAI 兼容接口。

### 环境变量示例

```bash
set OPENAI_API_KEY=your_api_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set JUDGE_API_KEY=your_judge_api_key
set JUDGE_BASE_URL=https://api.openai.com/v1
```

### 命令示例

```bash
python evals/run_eval.py ^
  --dataset evals/next_step_eval_v1.jsonl ^
  --output reports/eval_report.json ^
  --gen-model gpt-4.1-mini ^
  --gen-api-key-env OPENAI_API_KEY ^
  --gen-base-url %OPENAI_BASE_URL% ^
  --judge-model gpt-4.1 ^
  --judge-api-key-env JUDGE_API_KEY ^
  --judge-base-url %JUDGE_BASE_URL% ^
  --concurrency 12
```

### 本地干跑校验

不调用模型，只验证数据集、Prompt 组装与流程完整性：

```bash
python evals/run_eval.py --dataset evals/next_step_eval_v1.jsonl --dry-run
```
