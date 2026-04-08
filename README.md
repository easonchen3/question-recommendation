# 下一步问题推荐评测框架

这个仓库用于评测通信领域 Agent 的“下一步问题推荐”能力，当前已经统一为 Excel 评测集和 Markdown Prompt 归档方案。

当前约定：
- 评测集文件使用 [评测集.xlsx](/D:/Code/questio_recommendation/evals/评测集.xlsx)
- 生成模型配置从 [config.example.json](/D:/Code/questio_recommendation/evals/config.example.json) 的 `evaluate.generation_model` 读取
- 裁判模型配置从 [config.example.json](/D:/Code/questio_recommendation/evals/config.example.json) 的 `evaluate.judge_model` 读取
- 所有运行时 Prompt 都从 Markdown 归档文件加载，不再保留 `.txt` Prompt 文件

## 目录结构

```text
prompts/
  generation_prompt_archive.md
  evaluation_prompt_archive.md
src/
  next_question_reco/
    __init__.py
    prompting.py
evals/
  config.example.json
  generate_eval_set.py
  run_eval.py
  analyze_failures.py
  评测集.xlsx
requirements.txt
```

## Prompt 归档

- [generation_prompt_archive.md](/D:/Code/questio_recommendation/prompts/generation_prompt_archive.md)
- [evaluation_prompt_archive.md](/D:/Code/questio_recommendation/prompts/evaluation_prompt_archive.md)

[prompting.py](/D:/Code/questio_recommendation/src/next_question_reco/prompting.py) 会直接从这两个 Markdown 文件里提取运行时需要的代码块。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置模型

先编辑 [config.example.json](/D:/Code/questio_recommendation/evals/config.example.json)。

`run_eval.py` 不再从命令行读取生成模型和裁判模型参数，下面这些配置都从 `config` 读取：
- `evaluate.generation_model.model`
- `evaluate.generation_model.base_url`
- `evaluate.generation_model.api_key_env` 或 `evaluate.generation_model.api_key`
- `evaluate.generation_model.temperature`
- `evaluate.judge_model.model`
- `evaluate.judge_model.base_url`
- `evaluate.judge_model.api_key_env` 或 `evaluate.judge_model.api_key`
- `evaluate.judge_model.temperature`

环境变量示例：

```bash
set OPENAI_API_KEY=your_generation_api_key
set JUDGE_API_KEY=your_judge_api_key
```

## 脚本操作

### 1. 只生成评测集

```bash
python evals/run_eval.py --config evals/config.example.json --mode generate
```

### 2. 只评测已有 Excel 评测集

```bash
python evals/run_eval.py --config evals/config.example.json --mode evaluate
```

### 3. 先生成再立即评测

```bash
python evals/run_eval.py --config evals/config.example.json --mode generate_and_evaluate
```

### 4. 本地 dry-run 校验

```bash
python evals/run_eval.py --config evals/config.example.json --mode evaluate --dry-run
```

### 5. 覆盖部分非模型参数

```bash
python evals/run_eval.py ^
  --config evals/config.example.json ^
  --mode evaluate ^
  --dataset evals/评测集.xlsx ^
  --output reports/eval_report.json ^
  --concurrency 12 ^
  --max-cases 20
```

## 失败样本分析

```bash
python evals/analyze_failures.py ^
  --report reports/eval_report.json ^
  --markdown-output reports/failure_case_analysis.md ^
  --excel-output reports/failure_cases.xlsx
```
