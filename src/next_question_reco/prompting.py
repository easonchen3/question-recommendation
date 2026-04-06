from __future__ import annotations

import json
from typing import Any, Mapping


RECOMMENDATION_SYSTEM_PROMPT = """你是一个“下一步问题推荐器”。

你的任务是：基于当前上下文，推荐最能推动任务继续前进的 Top3 个“下一步问题”。

核心要求：
1. 输出的是“下一步问题”，不是泛泛的相关问题。
2. 每个问题都必须承接当前问题、当前计划或当前执行结果，能够推动下一轮继续澄清、确认、下钻、验证、比较、定位或决策。
3. 问题必须与当前上下文强相关，不能跳出当前任务语境。
4. 历史高频问题仅用于去重参考，禁止复述或输出语义几乎相同的问题。
5. 如果用户特征缺失，不要编造；如果某个特征能帮助问题更贴合，就自然吸收。
6. 问题要具体、可执行、单轮可回答，避免空泛表达。

你不能依赖某个固定意图名或固定 skill 规则来工作。你必须只根据当前输入的上下文，自行判断“当前最值得推进的动作类型”。

你会收到一组通用动作标签及其优先级。你必须遵守：
- 优先选择高优先级动作标签对应的问题。
- Top3 尽量覆盖不同的高优先级动作标签，不要 3 个问题都落在同一类细节动作上。
- 如果高优先级动作还没有做，不要过早进入低优先级的细节查询。
- 如果已经存在明确可执行的下一步动作，不要优先输出“该先 A 还是先 B”这类二选一决策题。
- 优先输出“可直接执行的推进问题”，而不是“解释性问题”或“方法论发散问题”。

通用动作标签说明：
- clarify_boundary: 澄清定义、边界、口径、前提、判断标准
- narrow_scope: 缩小范围、确认对象、锁定影响面、明确聚焦对象
- align_key_signals: 对齐关键线索、时间窗口、异常信号、结果变化
- choose_dimension: 决定下一步要按什么维度、分组、对象或视角继续分析
- compare_or_filter: 做对比、切片、阈值过滤、异常筛选
- validate_evidence: 补证据链、做交叉验证、验证假设、消除歧义
- choose_next_path: 在多个可行方向中决定下一步优先路径
- detail_lookup: 索取过细明细、底层字段、底层实现、TopN 明细

通用优先原则：
1. 先补关键不确定性
2. 先缩小范围或明确对象
3. 先对齐关键线索、结果、时间窗口或异常信号
4. 先决定下一步分析路径、对比维度或判断标准
5. 再做证据补强和交叉验证
6. 最后才进入过细的底层实现、明细值或细节查询

推荐的问题形态：
- 是否继续按某个对象、维度、范围确认当前异常是否集中
- 要不要把某个关键线索、结果、告警、时间窗口继续对齐
- 是否继续按某个分组、切片、阈值、条件做下钻或筛选
- 是否继续补某类关键证据来验证当前判断

尽量避免的问题形态：
- 该先 A 还是先 B
- 能否证明某个复杂假设是否成立
- 请直接给我底层明细、底层字段、TopN 明细
- 过于抽象的方法论优化题

如果输入里包含多个意图或多个 skill，不要平均分配注意力；优先选择最能推动“当前执行状态继续前进”的问题。

不要输出解释，不要输出思考过程，不要输出额外文本。

输出格式必须是严格 JSON：
{
  "next_questions": [
    "问题1",
    "问题2",
    "问题3"
  ]
}
"""


ACTION_LABELS = {
    "clarify_boundary": "澄清定义、边界、口径、前提、判断标准",
    "narrow_scope": "缩小范围、确认对象、锁定影响面、明确聚焦对象",
    "align_key_signals": "对齐关键线索、时间窗口、异常信号、结果变化",
    "choose_dimension": "决定下一步要按什么维度、分组、对象或视角继续分析",
    "compare_or_filter": "做对比、切片、阈值过滤、异常筛选",
    "validate_evidence": "补证据链、做交叉验证、验证假设、消除歧义",
    "choose_next_path": "在多个可行方向中决定下一步优先路径",
    "detail_lookup": "索取过细明细、底层字段、底层实现、TopN 明细",
}


def _compact_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _flatten_text(case_input: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in ("original_question", "rewritten_question", "execution_result"):
        value = case_input.get(key)
        if value:
            parts.append(str(value))
    for key in ("current_plan", "history_high_freq_questions", "user_profile"):
        value = case_input.get(key) or []
        parts.extend(str(item) for item in value)
    intent_value = case_input.get("intent")
    if isinstance(intent_value, list):
        parts.extend(str(item) for item in intent_value)
    elif intent_value:
        parts.append(str(intent_value))
    return " ".join(parts)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _add_score(scores: dict[str, int], label: str, value: int) -> None:
    scores[label] = scores.get(label, 0) + value


def derive_generic_action_bias(case_input: Mapping[str, Any]) -> dict[str, Any]:
    text = _flatten_text(case_input)
    original_question = str(case_input.get("original_question") or "")
    rewritten_question = str(case_input.get("rewritten_question") or "")
    execution_result = str(case_input.get("execution_result") or "")
    current_plan = case_input.get("current_plan") or []
    history = case_input.get("history_high_freq_questions") or []

    scores = {label: 0 for label in ACTION_LABELS}
    reasons: dict[str, list[str]] = {label: [] for label in ACTION_LABELS}

    if _contains_any(original_question + rewritten_question, ["什么", "区别", "定义", "口径", "边界", "怎么理解", "判别", "判断"]):
        _add_score(scores, "clarify_boundary", 4)
        reasons["clarify_boundary"].append("问题本身包含定义/边界/判别诉求")

    if _contains_any(text, ["范围", "影响", "哪些", "哪批", "区域", "站点", "小区", "用户", "对象", "集中", "分布", "聚合"]):
        _add_score(scores, "narrow_scope", 4)
        reasons["narrow_scope"].append("上下文出现对象范围或影响范围信号")

    if _contains_any(text, ["时间", "时段", "窗口", "前后", "开始时刻", "高峰", "昨晚", "今天", "近 3 天", "近 24 小时", "趋势", "对齐"]):
        _add_score(scores, "align_key_signals", 4)
        reasons["align_key_signals"].append("上下文包含时间窗口或时序对齐信号")

    if _contains_any(text, ["维度", "分组", "按", "下钻", "视角", "类型", "对象", "终端", "运营商", "厂家", "版本", "业务类型"]):
        _add_score(scores, "choose_dimension", 3)
        reasons["choose_dimension"].append("上下文包含继续按维度或对象拆分的信号")

    if _contains_any(text, ["对比", "比较", "阈值", "%", "过滤", "筛选", "波动", "突增", "突变", "高于", "低于"]):
        _add_score(scores, "compare_or_filter", 3)
        reasons["compare_or_filter"].append("上下文包含对比、阈值或过滤信号")

    if _contains_any(text, ["验证", "交叉", "关联", "相关", "证据", "闭环", "确认是否", "主因", "根因", "原因", "假设"]):
        _add_score(scores, "validate_evidence", 3)
        reasons["validate_evidence"].append("上下文包含验证、归因或证据链信号")

    if _contains_any(text, ["下一步", "优先", "先看", "先做", "判断", "是否继续", "怎么继续"]):
        _add_score(scores, "choose_next_path", 3)
        reasons["choose_next_path"].append("上下文显式需要决定下一步路径")

    if _contains_any(text, ["TopN", "Top3", "Top5", "Top10", "明细", "具体数值", "字段", "命令", "日志详情", "MML", "IE"]):
        _add_score(scores, "detail_lookup", 3)
        reasons["detail_lookup"].append("上下文包含明细或底层实现信号")

    if len(current_plan) >= 3:
        _add_score(scores, "narrow_scope", 1)
        _add_score(scores, "choose_dimension", 1)
        reasons["narrow_scope"].append("已经存在计划，优先承接未完成的具体步骤而不是空泛发散")
        reasons["choose_dimension"].append("计划可作为下一步动作锚点")

    if execution_result:
        if _contains_any(execution_result, ["但", "不过", "尚未", "还未", "不明确", "不清楚", "缺", "需要继续"]):
            _add_score(scores, "validate_evidence", 4)
            _add_score(scores, "narrow_scope", 1)
            reasons["validate_evidence"].append("执行结果明确表明当前仍缺证据或结论")
            reasons["narrow_scope"].append("执行结果表明需要继续把问题收敛到更明确对象")
        if _contains_any(execution_result, ["集中", "主要在", "分布在", "局部", "少数"]):
            _add_score(scores, "narrow_scope", 2)
            reasons["narrow_scope"].append("执行结果已经给出部分范围信息，适合继续收敛对象")
        if _contains_any(execution_result, ["升高", "下降", "波动", "告警", "失败码"]):
            _add_score(scores, "align_key_signals", 2)
            reasons["align_key_signals"].append("执行结果包含可继续对齐的关键异常信号")

    if isinstance(case_input.get("intent"), list):
        _add_score(scores, "choose_next_path", 1)
        _add_score(scores, "validate_evidence", 1)
        reasons["choose_next_path"].append("存在多个意图或 skill，需要保证问题仍然推动主执行方向")
        reasons["validate_evidence"].append("多意图下更需要补能帮助主线推进的证据")

    if history:
        _add_score(scores, "compare_or_filter", 1)
        reasons["compare_or_filter"].append("存在历史高频问题，需要注意去重和差异化")

    # 明细查询默认降级，除非它在计划和结果中已经明显成为当前阶段的主要需求。
    scores["detail_lookup"] -= 2
    scores["choose_next_path"] -= 1

    sorted_labels = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ranked_labels = [label for label, score in sorted_labels if score > 0][:5]
    if not ranked_labels:
        ranked_labels = ["choose_next_path", "narrow_scope", "validate_evidence"]

    high_priority = [label for label in ranked_labels if label != "detail_lookup"][:3]
    if len(high_priority) < 3:
        for label in ranked_labels:
            if label not in high_priority:
                high_priority.append(label)
            if len(high_priority) == 3:
                break

    return {
        "ranked_action_labels": ranked_labels,
        "high_priority_action_labels": high_priority,
        "action_label_definitions": ACTION_LABELS,
        "label_reasons": {label: reasons[label] for label in ranked_labels},
        "plan_anchor_steps": current_plan[:4],
        "result_anchor": execution_result,
        "diversity_rule": "Top3 尽量覆盖不同的高优先级动作标签，不要 3 个问题都落在同一类细节动作上",
        "avoid_patterns": [
            "不要输出平行发散的相关问题",
            "不要直接复述历史高频问题",
            "在高优先级动作未完成前，避免过早进入 detail_lookup",
            "如果可以问范围确认或路径决策，就不要优先问底层细节",
            "如果可以输出明确动作题，就不要优先输出二选一决策题",
            "不要把 3 个问题都写成假设验证题",
        ],
        "preferred_question_shapes": [
            "是否继续按某个对象或维度确认当前异常是否集中",
            "要不要把某个关键线索与时间窗口或结果变化继续对齐",
            "是否继续按某个分组、阈值、条件或切片方式下钻",
            "是否继续补某类关键证据来验证当前判断",
        ],
    }


def build_recommendation_user_prompt(case_input: Mapping[str, Any]) -> str:
    intent_value = case_input.get("intent")
    if isinstance(intent_value, (list, tuple)):
        intent_payload: Any = list(intent_value)
    else:
        intent_payload = intent_value

    generic_bias = derive_generic_action_bias(case_input)
    normalized_payload = {
        "original_question": case_input.get("original_question"),
        "rewritten_question": case_input.get("rewritten_question"),
        "intent": intent_payload,
        "user_profile": case_input.get("user_profile") or [],
        "current_plan": case_input.get("current_plan") or [],
        "execution_result": case_input.get("execution_result"),
        "history_high_freq_questions": case_input.get("history_high_freq_questions") or [],
    }

    return f"""请基于以下上下文，为当前任务推荐 Top3 个“下一步问题”。

要求：
- 输出必须是“下一步问题”，不是相关问题
- 必须承接当前计划或当前执行结果
- 不能重复历史高频问题
- 优先推荐能推进当前任务状态的问题，而不是过细的实现细节
- Top3 尽量覆盖不同的高优先级动作标签
- 必须严格输出 JSON

通用动作优先级分析：
{_compact_json(generic_bias)}

上下文如下：
{_compact_json(normalized_payload)}
"""
