from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOTAL_CASES = 120

REGIONS = ["泰国北区", "泰国南区", "泰国东区", "泰国西区", "曼谷核心区", "东北片区"]
ROLES = ["网络运维工程师", "无线优化工程师", "核心网工程师", "家宽运维工程师", "NOC 值班工程师", "数据分析工程师"]
THRESHOLDS = ["10%", "12%", "15%"]
TIME_WINDOWS = ["昨晚 20:00-22:00", "今天 08:00-10:00", "近 24 小时", "近 3 天", "本周高峰时段", "凌晨 01:00-03:00"]
VENDORS = ["华为", "中兴", "爱立信", "诺基亚"]
SITES = ["CNX-5G-001", "BKK-LTE-118", "HKT-OLT-023", "KBI-MW-009", "AYT-IMS-017", "NRT-UPF-032"]
NODES = ["AMF", "SMF", "UPF", "IMS", "MME", "OLT", "BRAS", "gNodeB", "短信中心", "传输设备"]
METRICS = ["注册失败率", "掉话率", "上行丢包率", "ONU 离线数", "PRB 利用率", "投诉量", "附着成功率", "切换失败率"]
ALARMS = ["链路抖动告警", "光功率低告警", "SCTP 重传告警", "高干扰告警", "PON 口拥塞告警", "CPU 高负载告警"]
CODES = ["15", "11", "13", "98", "111", "384"]
SERVICES = ["5G 注册", "VoLTE 语音", "家宽上网", "短信下发", "国际漫游", "数据业务"]

MOBILE_SITES = ["CNX-5G-001", "BKK-LTE-118", "AYT-NR-021", "HKT-NR-054", "KBI-LTE-203", "NRT-NR-032"]
CORE_SITES = ["AYT-IMS-017", "NRT-UPF-032", "BKK-AMF-011", "CNX-SMF-008", "HKT-UPF-022", "NRT-IMS-105"]
FIXED_SITES = ["HKT-OLT-023", "CNX-OLT-014", "BKK-OLT-009", "NST-PON-017", "KBI-OLT-031", "SKA-OLT-006"]
TRANSPORT_SITES = ["KBI-MW-009", "CNX-MW-013", "BKK-IPRAN-022", "HKT-PTN-004", "AYT-MW-016", "NRT-PTN-018"]

MOBILE_METRICS = ["注册失败率", "附着成功率", "掉话率", "切换失败率", "PRB 利用率", "投诉量"]
FIXED_METRICS = ["ONU 离线数", "家宽投诉量", "上行丢包率", "光功率波动", "PON 口利用率", "宽带成功率"]
TRANSPORT_METRICS = ["上行丢包率", "时延", "抖动", "接口错误包", "链路利用率", "业务受影响数"]
ROAMING_METRICS = ["漫游失败率", "注册失败率", "投诉量", "信令时延", "失败码占比", "附着成功率"]

MOBILE_ALARMS = ["SCTP 重传告警", "高干扰告警", "小区退服告警", "链路抖动告警", "时钟异常告警", "CPU 高负载告警"]
FIXED_ALARMS = ["光功率低告警", "LOS 告警", "LOF 告警", "PON 口拥塞告警", "OLT 板卡告警", "CPU 高负载告警"]
TRANSPORT_ALARMS = ["链路抖动告警", "误码告警", "光模块异常告警", "CPU 高负载告警", "端口拥塞告警", "保护倒换告警"]
CORE_ALARMS = ["SCTP 重传告警", "信令拥塞告警", "会话建立异常告警", "CPU 高负载告警", "接口超时告警", "链路抖动告警"]

MOBILE_CODES = ["15", "11", "13", "111", "384", "27"]
FIXED_CODES = ["101", "102", "201", "301", "401", "501"]
CORE_CODES = ["15", "11", "13", "98", "111", "384"]

SCENARIO_SLOT_POOLS = {
    "nsa_sa_compare": {
        "sites": MOBILE_SITES,
        "nodes": ["AMF", "SMF", "UPF", "gNodeB", "MME"],
        "metrics": ["注册失败率", "附着成功率", "驻留成功率", "切换失败率", "PRB 利用率", "投诉量"],
        "alarms": MOBILE_ALARMS,
        "codes": MOBILE_CODES,
        "services": ["5G 注册", "VoLTE 语音", "数据业务", "驻留异常"],
    },
    "volte_kpi_definition": {
        "sites": MOBILE_SITES,
        "nodes": ["IMS", "MME", "eNodeB", "SBC", "PCRF", "gNodeB"],
        "metrics": ["掉话率", "接通率", "语音时延", "抖动", "投诉量", "切换失败率"],
        "alarms": CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["VoLTE 语音", "语音投诉", "语音接通", "语音保持"],
    },
    "pon_optical_power": {
        "sites": FIXED_SITES,
        "nodes": ["OLT", "ONU", "PON 口", "分光器", "BRAS"],
        "metrics": FIXED_METRICS,
        "alarms": FIXED_ALARMS,
        "codes": FIXED_CODES,
        "services": ["家宽上网", "家宽离线", "宽带接入", "家宽投诉"],
    },
    "amf_smf_roles": {
        "sites": CORE_SITES,
        "nodes": ["AMF", "SMF", "UPF", "gNodeB", "MME"],
        "metrics": ["注册失败率", "会话建立成功率", "附着成功率", "时延", "投诉量", "数据业务成功率"],
        "alarms": CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["5G 注册", "数据业务", "会话建立", "VoLTE 语音"],
    },
    "5g_attach_failure": {
        "sites": MOBILE_SITES,
        "nodes": ["AMF", "SMF", "UPF", "MME", "gNodeB", "传输设备"],
        "metrics": ["注册失败率", "附着成功率", "切换失败率", "PRB 利用率", "投诉量", "上行丢包率"],
        "alarms": MOBILE_ALARMS + ["传输链路异常告警"],
        "codes": MOBILE_CODES,
        "services": ["5G 注册", "短信下发", "VoLTE 语音", "数据业务"],
    },
    "volte_call_drop": {
        "sites": MOBILE_SITES + CORE_SITES,
        "nodes": ["IMS", "MME", "eNodeB", "gNodeB", "SBC", "传输设备"],
        "metrics": ["掉话率", "切换失败率", "语音时延", "抖动", "投诉量", "弱覆盖比例"],
        "alarms": MOBILE_ALARMS + CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["VoLTE 语音", "语音投诉", "语音保持"],
    },
    "pon_mass_offline": {
        "sites": FIXED_SITES,
        "nodes": ["OLT", "ONU", "PON 口", "分光器", "光路"],
        "metrics": FIXED_METRICS,
        "alarms": FIXED_ALARMS,
        "codes": FIXED_CODES,
        "services": ["家宽上网", "家宽离线", "宽带接入"],
    },
    "ip_backhaul_loss": {
        "sites": TRANSPORT_SITES,
        "nodes": ["传输设备", "BRAS", "IPRAN", "PTN", "微波链路", "上联路由器"],
        "metrics": TRANSPORT_METRICS,
        "alarms": TRANSPORT_ALARMS,
        "codes": CORE_CODES,
        "services": ["数据业务", "VoLTE 语音", "5G 注册", "回传承载"],
    },
    "sms_delay": {
        "sites": CORE_SITES,
        "nodes": ["短信中心", "信令网关", "IMS", "MME", "SMSC", "传输设备"],
        "metrics": ["下发时延", "重传次数", "投诉量", "提交成功率", "信令时延", "队列长度"],
        "alarms": CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["短信下发", "短信到达", "国际短信"],
    },
    "high_interference_cell": {
        "sites": MOBILE_SITES,
        "nodes": ["gNodeB", "eNodeB", "天馈系统", "邻区站点", "传输设备"],
        "metrics": ["PRB 利用率", "上行干扰值", "掉话率", "切换失败率", "投诉量", "上行质量"],
        "alarms": MOBILE_ALARMS,
        "codes": MOBILE_CODES,
        "services": ["数据业务", "VoLTE 语音", "5G 注册"],
    },
    "traffic_spike_analysis": {
        "sites": MOBILE_SITES,
        "nodes": ["gNodeB", "UPF", "AMF", "传输设备", "汇聚节点"],
        "metrics": ["流量", "PRB 利用率", "投诉量", "上行丢包率", "带宽利用率", "数据业务成功率"],
        "alarms": MOBILE_ALARMS + TRANSPORT_ALARMS,
        "codes": MOBILE_CODES,
        "services": ["数据业务", "视频业务", "游戏业务", "5G 注册"],
    },
    "complaint_kpi_correlation": {
        "sites": MOBILE_SITES,
        "nodes": ["gNodeB", "IMS", "UPF", "传输设备", "核心网节点"],
        "metrics": ["投诉量", "掉话率", "注册失败率", "上行丢包率", "切换失败率", "时延"],
        "alarms": MOBILE_ALARMS + CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["VoLTE 语音", "数据业务", "5G 注册", "短信下发"],
    },
    "drop_rate_drilldown": {
        "sites": MOBILE_SITES,
        "nodes": ["gNodeB", "UPF", "传输设备", "核心网节点", "邻区站点"],
        "metrics": ["掉线率", "切换失败率", "弱覆盖比例", "上行丢包率", "PRB 利用率", "投诉量"],
        "alarms": MOBILE_ALARMS + TRANSPORT_ALARMS,
        "codes": MOBILE_CODES,
        "services": ["数据业务", "VoLTE 语音", "5G 注册"],
    },
    "home_broadband_offline_topn": {
        "sites": FIXED_SITES,
        "nodes": ["OLT", "PON 口", "ONU", "分光器", "光路"],
        "metrics": FIXED_METRICS,
        "alarms": FIXED_ALARMS,
        "codes": FIXED_CODES,
        "services": ["家宽离线", "家宽上网", "宽带接入"],
    },
    "roaming_failure_heatmap": {
        "sites": CORE_SITES,
        "nodes": ["AMF", "MME", "信令网关", "漫游平台", "归属网接口"],
        "metrics": ROAMING_METRICS,
        "alarms": CORE_ALARMS,
        "codes": CORE_CODES,
        "services": ["国际漫游", "漫游注册", "漫游数据业务"],
    },
    "power_alarm_impact_analysis": {
        "sites": MOBILE_SITES + FIXED_SITES,
        "nodes": ["站点电源", "OLT", "gNodeB", "传输设备", "机房配电"],
        "metrics": ["投诉量", "掉话率", "注册失败率", "ONU 离线数", "上行丢包率", "业务成功率"],
        "alarms": ["电源告警", "蓄电池告警", "整流模块告警", "CPU 高负载告警", "链路抖动告警", "光功率低告警"],
        "codes": CORE_CODES,
        "services": ["VoLTE 语音", "数据业务", "家宽上网", "5G 注册"],
    },
}

DIFFICULTIES = (["easy"] * 30) + (["medium"] * 66) + (["hard"] * 24)


@dataclass(frozen=True)
class Blueprint:
    key: str
    intent: str
    repeats: int
    question_templates: list[str]
    rewritten_template: str
    plan_steps: list[str]
    result_templates: list[str]
    next_question_templates: list[str]
    history_templates: list[str]
    evaluation_focus: list[str]


def scenario_pool(key: str) -> dict[str, list[str]]:
    fallback = {
        "sites": SITES,
        "nodes": NODES,
        "metrics": METRICS,
        "alarms": ALARMS,
        "codes": CODES,
        "services": SERVICES,
    }
    return SCENARIO_SLOT_POOLS.get(key, fallback)


def pick(seq: list[str], idx: int) -> str:
    return seq[idx % len(seq)]


def slice_plan(steps: list[str], difficulty: str) -> list[str]:
    if difficulty == "easy":
        return steps[:3]
    if difficulty == "medium":
        return steps[:4]
    return steps[:5]


def build_user_profile(idx: int, difficulty: str, region: str, vendor: str, threshold: str) -> list[str]:
    profile: list[str] = []
    if idx % 5 != 0:
        profile.append(pick(ROLES, idx))
    if idx % 4 != 0:
        profile.append(f"地区偏好：{region}")
    if difficulty != "hard" or idx % 3 == 0:
        profile.append(f"波动阈值偏好：{threshold}")
    if idx % 2 == 0:
        profile.append(f"设备厂家偏好：{vendor}")
    return profile


def build_history(templates: list[str], slots: dict[str, str], idx: int) -> list[str]:
    if idx % 6 == 0:
        return []
    size = 3 + (idx % 2)
    items = []
    for offset in range(size):
        items.append(pick(templates, idx + offset).format(**slots))
    return items


def build_next_top3(templates: list[str], slots: dict[str, str], idx: int) -> list[str]:
    items: list[str] = []
    for offset in range(len(templates)):
        candidate = pick(templates, idx + offset).format(**slots)
        if candidate not in items:
            items.append(candidate)
        if len(items) == 3:
            return items
    raise ValueError("Each blueprint must provide at least 3 distinct next-question templates.")


def build_result(template: str, slots: dict[str, str], difficulty: str) -> str:
    base = template.format(**slots)
    suffix = {
        "easy": "当前线索比较集中，适合顺着主线继续推进。",
        "medium": "目前已经缩小了一部分范围，但还缺关键证据闭环。",
        "hard": "当前同时存在两到三个可疑方向，需要进一步缩小范围再判断。",
    }[difficulty]
    return f"{base} {suffix}"


def build_intent_value(primary_intent: str, case_id: int) -> str | list[str]:
    if case_id % 8 != 0:
        return primary_intent
    multi_mapping = {
        "知识问答": ["知识问答", "故障诊断"],
        "故障诊断": ["故障诊断", "智能问数"],
        "智能问数": ["智能问数", "故障诊断"],
    }
    return multi_mapping[primary_intent]


def render_case(case_id: int, blueprint: Blueprint, variant: int, difficulty: str) -> dict:
    pool = scenario_pool(blueprint.key)
    region = pick(REGIONS, case_id + variant)
    vendor = pick(VENDORS, case_id + variant)
    threshold = pick(THRESHOLDS, case_id + variant)
    slots = {
        "region": region,
        "vendor": vendor,
        "threshold": threshold,
        "site": pick(pool["sites"], case_id + variant),
        "time_window": pick(TIME_WINDOWS, case_id + variant),
        "node": pick(pool["nodes"], case_id + variant),
        "metric": pick(pool["metrics"], case_id + variant),
        "alarm": pick(pool["alarms"], case_id + variant),
        "code": pick(pool["codes"], case_id + variant),
        "service": pick(pool["services"], case_id + variant),
    }

    question = pick(blueprint.question_templates, variant).format(**slots)
    rewritten = blueprint.rewritten_template.format(**slots)
    intent_value = build_intent_value(blueprint.intent, case_id)
    profile = build_user_profile(case_id + variant, difficulty, region, vendor, threshold)
    current_plan = slice_plan(blueprint.plan_steps, difficulty)
    result = build_result(pick(blueprint.result_templates, variant), slots, difficulty)
    history = build_history(blueprint.history_templates, slots, case_id + variant)
    top3 = build_next_top3(blueprint.next_question_templates, slots, case_id + variant)

    return {
        "id": f"NQ-{case_id:03d}",
        "intent": intent_value,
        "difficulty": difficulty,
        "input": {
            "original_question": question,
            "rewritten_question": rewritten,
            "intent": intent_value,
            "user_profile": profile,
            "current_plan": current_plan,
            "execution_result": result,
            "history_high_freq_questions": history,
        },
        "expected": {
            "top3": top3,
            "evaluation_focus": blueprint.evaluation_focus,
        },
        "meta": {
            "scenario_family": blueprint.key,
            "region": region,
            "vendor": vendor,
            "intent_mode": "multi" if isinstance(intent_value, list) else "single",
            "profile_density": "rich" if len(profile) >= 3 else ("medium" if profile else "sparse"),
        },
    }


KNOWLEDGE_BLUEPRINTS = [
    Blueprint(
        key="nsa_sa_compare",
        intent="知识问答",
        repeats=9,
        question_templates=[
            "{region} 现网里怎么快速区分 NSA 和 SA，最好能用于排障。",
            "如果我要在 {region} 判断某站点是 NSA 还是 SA，下一步该看哪些网元和信令？",
            "{service} 场景下 NSA 和 SA 的判断口径分别是什么？",
        ],
        rewritten_template="结合通信现网场景，澄清 NSA 与 SA 的判别方式，并给出 {region} 可落地的判断路径",
        plan_steps=["澄清定义边界", "对齐接入与核心网差异", "补充现网观察点", "补充故障定位中的用法", "给出落地判断步骤"],
        result_templates=[
            "已说明 NSA 依赖 EPC、SA 依赖 5GC，但还没有落到 {region} 现网核查动作。",
            "当前回答覆盖了架构差异，但对 {site} 如何现场判断仍不够具体。",
            "当前结果提到了核心网差异，但缺少针对 {service} 场景的现网落地方法。",
        ],
        next_question_templates=[
            "要不要继续补充在 {region} 现网里判断 NSA/SA 时应该优先查看哪些网元和信令？",
            "是否继续把 NSA 和 SA 的差异落到 {service} 排障步骤里，说明各自先看什么指标？",
            "要不要进一步说明在 {site} 现场如果只有 KPI 和告警，怎样快速判断当前是 NSA 还是 SA？",
            "是否继续补充当用户驻留异常时，NSA 和 SA 分别应该从接入侧还是核心网侧先入手？",
        ],
        history_templates=["NSA 和 SA 有什么区别？", "{region} 现网怎么判断 NSA/SA？", "5G SA 和 NSA 的网元差异是什么？", "排障时怎么识别 NSA 还是 SA？"],
        evaluation_focus=["next_step", "knowledge_grounding", "telecom_fit"],
    ),
    Blueprint(
        key="volte_kpi_definition",
        intent="知识问答",
        repeats=9,
        question_templates=[
            "VoLTE 掉话率和接通率的口径总记不清，能不能按现网运维场景讲清楚？",
            "{region} 做 VoLTE 运维时，接通率、掉话率、时延这几个指标怎么一起看？",
            "想搞清楚 VoLTE 相关 KPI 在故障定位里的用法，不要只给定义。",
        ],
        rewritten_template="澄清 VoLTE 关键 KPI 口径，并结合 {region} 现网运维给出使用方式",
        plan_steps=["梳理 KPI 定义", "说明统计口径", "对齐故障场景用法", "补充指标联动", "给出运维分析顺序"],
        result_templates=[
            "当前结果已经给出 VoLTE 接通率、掉话率和时延的定义，但还没说明遇到投诉时应该先看哪个指标。",
            "现有回答偏概念解释，对 {region} 运维值班场景的指标联动顺序还不够清晰。",
            "当前内容提到了 KPI 口径，但缺少把指标和 IMS、无线侧、回传侧联系起来的分析思路。",
        ],
        next_question_templates=[
            "要不要继续说明在 {region} 出现 VoLTE 投诉时，这几个 KPI 的排查顺序应该怎么排？",
            "是否继续把接通率、掉话率和时延分别映射到 IMS、无线侧和回传侧的常见问题？",
            "要不要补充当 {threshold} 以上波动才算异常时，VoLTE KPI 应该怎样设告警阈值？",
            "是否继续举一个现网故障案例，说明这些 KPI 应该怎么联动判断？",
        ],
        history_templates=["VoLTE 掉话率是什么意思？", "VoLTE 接通率怎么定义？", "VoLTE KPI 有哪些？", "IMS 故障看哪些 KPI？"],
        evaluation_focus=["next_step", "knowledge_to_action", "telecom_fit"],
    ),
    Blueprint(
        key="pon_optical_power",
        intent="知识问答",
        repeats=9,
        question_templates=[
            "PON 光功率阈值到底怎么定，别只说标准值，最好结合运维经验。",
            "{region} 家宽场景下，ONU 光功率高低阈值通常怎么用来判断故障？",
            "PON 口光功率告警很多时，阈值和现网判断方法想系统梳理一下。",
        ],
        rewritten_template="澄清 PON/ONU 光功率阈值的使用方式，并结合 {region} 家宽运维场景给出判断方法",
        plan_steps=["说明标准阈值和工程阈值差异", "补充 OLT/ONU 双侧口径", "说明常见故障映射", "补充告警联动关系", "给出运维建议"],
        result_templates=[
            "当前只给出了一般光功率范围，对 OLT 与 ONU 双侧如何联合判断还不够完整。",
            "回答已经覆盖了部分阈值，但没有说明 {alarm} 出现时阈值应如何配合使用。",
            "现有结果偏静态阈值，缺少在 {region} 家宽运维里判断弱光、断纤和分光异常的方法。",
        ],
        next_question_templates=[
            "要不要继续补充 OLT 和 ONU 两侧光功率一起看时，怎样区分弱光、断纤和分光异常？",
            "是否继续说明出现 {alarm} 时，光功率阈值和 LOS/LOF 告警该怎么联合判断？",
            "要不要进一步给出 {region} 家宽大面积离线场景里，先看 PON 口还是先看 ONU 光功率的步骤？",
            "是否继续补充按 {vendor} 设备口径看，阈值差异会不会影响告警判断？",
        ],
        history_templates=["ONU 光功率正常范围是多少？", "PON 光功率阈值怎么设？", "OLT 光功率低怎么处理？", "家宽弱光怎么判断？"],
        evaluation_focus=["next_step", "knowledge_grounding", "telecom_fit"],
    ),
    Blueprint(
        key="amf_smf_roles",
        intent="知识问答",
        repeats=9,
        question_templates=[
            "AMF 和 SMF 在 5GC 里分别管什么，想听排障视角的解释。",
            "5G 核心网里 AMF、SMF 的职责怎么区分，最好能联系注册和会话问题。",
            "{service} 出问题时，AMF 和 SMF 分别应该怎么看？",
        ],
        rewritten_template="从通信运维和排障视角澄清 AMF 与 SMF 的职责差异，并给出 {service} 场景的使用方法",
        plan_steps=["梳理职责边界", "说明注册与会话分工", "映射常见故障现象", "补充关键接口与指标", "给出排障观察顺序"],
        result_templates=[
            "当前已经说明 AMF 偏控制面接入管理、SMF 偏会话管理，但对排障时先看哪个网元还没有明确结论。",
            "现有结果解释了基本职责，不过缺少把注册失败和数据业务异常映射到 AMF/SMF 的方法。",
            "当前回答偏概念，对 {service} 现网告警和接口定位的指导性仍然不够。",
        ],
        next_question_templates=[
            "要不要继续说明在注册失败场景里，为什么通常先看 AMF，再看 SMF？",
            "是否继续把 {service} 异常拆成注册问题和会话问题，分别对应 AMF 和 SMF 的核查点？",
            "要不要补充 N1、N2、N4 等关键接口在 AMF、SMF 排障里的观察意义？",
            "是否继续给一个 {region} 现网案例，说明 AMF 和 SMF 的告警与 KPI 应该怎么联动看？",
        ],
        history_templates=["AMF 和 SMF 区别是什么？", "5GC 里 AMF 负责什么？", "SMF 负责哪些功能？", "注册失败和 SMF 有关系吗？"],
        evaluation_focus=["next_step", "knowledge_to_action", "telecom_fit"],
    ),
]


DIAGNOSIS_BLUEPRINTS = [
    Blueprint(
        key="5g_attach_failure",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} {time_window} 5G 注册失败突然升高，已经查到 {site} 这批站点比较严重，下一步怎么追？",
            "{region} 从 {time_window} 开始 {service} 失败变多，怀疑和 {node} 有关，下一步要怎么定位？",
            "昨晚开始 {region} 一批站点注册失败明显上升，当前排查做到一半了，下一步问题应该怎么问？",
        ],
        rewritten_template="定位 {region} {service} 失败升高的主因，并判断问题更接近无线侧、回传侧还是核心网侧",
        plan_steps=["确认影响范围", "检查站点退服和告警", "核查核心网侧失败码", "对齐回传链路时延与丢包", "按站点和小区继续下钻"],
        result_templates=[
            "目前已确认 {site} 未退服，但 {node} 侧失败码 {code} 在 {time_window} 后快速升高，且伴随 {metric} 波动。",
            "当前排查发现区域主告警不是退服而是 {alarm}，同时 {metric} 从基线抬升明显。",
            "执行结果显示异常主要集中在同厂家站点，{vendor} 设备占比最高，但是否和核心网信令相关还不明确。",
        ],
        next_question_templates=[
            "要继续按站点和小区维度确认是否所有扇区都出现 {service} 失败吗？",
            "要不要把 {node} 侧失败码 Top 原因按 {time_window} 前后拉出来，对齐故障开始时刻？",
            "是否继续检查这批站点的回传时延和丢包，确认是否引发控制面重传？",
            "要不要把异常站点按 {vendor} 厂家和版本聚合，排除版本或配置共性问题？",
        ],
        history_templates=["5G 注册失败怎么排查？", "{service} 失败升高看什么？", "{node} 失败码 {code} 是什么意思？", "{region} 注册失败异常站点有哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "history_dedup"],
    ),
    Blueprint(
        key="volte_call_drop",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} {time_window} VoLTE 掉话率突然升高，已经看到投诉增加，下一步该怎么问？",
            "{service} 掉话从昨天开始变多，当前已经看过基础 KPI，想继续定位。",
            "{region} 用户投诉 VoLTE 通话中断，现在线索不够集中，下一步问题怎么设计？",
        ],
        rewritten_template="定位 {region} VoLTE 掉话率升高的主因，并继续缩小到无线侧、IMS 侧或回传侧",
        plan_steps=["确认掉话影响范围", "核查无线侧覆盖和切换 KPI", "检查 IMS 信令与媒体面质量", "核查回传时延丢包", "按投诉用户和站点继续下钻"],
        result_templates=[
            "目前已确认掉话高峰出现在 {time_window}，无线侧切换失败率同步升高，但 IMS 未见明显退服。",
            "当前结果显示投诉用户集中在 {region} 城区，媒体面时延轻微抬升，同时部分站点出现 {alarm}。",
            "执行结果发现掉话更集中在高铁沿线站点，切换相关 KPI 异常明显，但是否与回传质量叠加有关还不清楚。",
        ],
        next_question_templates=[
            "要不要继续按站点和小区维度下钻，确认掉话是否集中在切换链路相同的区域？",
            "是否继续把掉话用户按终端型号和移动场景聚合，排除终端兼容性因素？",
            "要不要拉取 IMS 信令失败和媒体面时延丢包，对齐 {time_window} 掉话高峰做交叉验证？",
            "是否继续核查高投诉站点的切换失败率、弱覆盖和回传抖动，判断主因先后顺序？",
        ],
        history_templates=["VoLTE 掉话怎么排查？", "IMS 掉话看哪些指标？", "切换失败会引起掉话吗？", "{region} VoLTE 掉话高的站点有哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "telecom_fit"],
    ),
    Blueprint(
        key="pon_mass_offline",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} {time_window} 开始一批 ONU 大面积离线，PON 口上已经有告警了，下一步怎么查？",
            "家宽离线投诉突然增多，目前怀疑和 {site} 所在 OLT 有关，下一步问题怎么设计？",
            "{region} 大面积 ONU 离线，当前排查到光功率和告警都有异常，下一步问什么更有效？",
        ],
        rewritten_template="定位 {region} 大面积 ONU 离线的主因，并继续区分断纤、弱光、分光异常还是设备问题",
        plan_steps=["确认离线范围和 PON 口分布", "检查 OLT/PON 口告警", "核查光功率和 LOS/LOF", "确认是否涉及割接或外线施工", "按分光器和光路继续下钻"],
        result_templates=[
            "目前已确认离线 ONU 集中在 {site} 下挂的两个 PON 口，伴随 {alarm}，且部分光功率明显偏低。",
            "当前排查发现故障开始于 {time_window}，离线用户呈树状分布，但是否为外线施工导致还未确认。",
            "执行结果显示 OLT 本身负载正常，不过离线 ONU 主要集中在同一光路，疑似存在分光或弱光问题。",
        ],
        next_question_templates=[
            "要不要继续按 PON 口和分光器维度确认离线 ONU 是否集中在同一条光路？",
            "是否继续对比 OLT 和 ONU 两侧光功率，区分是弱光、断纤还是分光异常？",
            "要不要核查 {time_window} 是否有施工、割接或外线变更，与离线开始时刻对齐？",
            "是否继续把离线用户按楼宇或片区聚合，判断问题是在局端还是末端？",
        ],
        history_templates=["ONU 大面积离线怎么排查？", "PON 口告警导致离线怎么办？", "光功率低会造成 ONU 离线吗？", "{region} 家宽离线用户 TopN 是哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "telecom_fit"],
    ),
    Blueprint(
        key="ip_backhaul_loss",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} 回传链路从 {time_window} 开始丢包明显升高，业务体验也变差，下一步怎么继续？",
            "{site} 对应的回传网络上行丢包率升高，已经排到链路层面了，下一步问什么？",
            "当前怀疑是回传拥塞或链路抖动导致业务异常，想设计下一步问题继续定位。",
        ],
        rewritten_template="定位 {region} 回传链路丢包升高的主要原因，并继续区分拥塞、链路抖动还是设备异常",
        plan_steps=["确认异常链路和影响业务", "检查接口错误包和链路状态", "核查时延抖动趋势", "核查设备资源和流量峰值", "对齐变更和施工记录"],
        result_templates=[
            "目前已确认 {time_window} 丢包率升高主要发生在 {site} 上联链路，时延和抖动也同步抬升。",
            "当前结果显示接口未 down，但错误包增加，同时设备 CPU 在高峰期上升明显。",
            "执行结果发现异常更集中在 {vendor} 设备链路，且与业务高峰重合，不过是否为拥塞仍需确认。",
        ],
        next_question_templates=[
            "要不要继续按链路和接口维度核查错误包、CRC 和双工状态，确认是否存在物理层问题？",
            "是否继续把时延、抖动和流量峰值对齐到 {time_window}，判断更像拥塞还是链路抖动？",
            "要不要继续查看设备 CPU、队列丢弃和流量整形配置，确认是否是设备侧瓶颈？",
            "是否继续核查最近变更、割接或施工记录，排除外部操作引发的链路异常？",
        ],
        history_templates=["回传丢包怎么排查？", "链路抖动和拥塞怎么区分？", "接口错误包升高说明什么？", "{region} 回传异常链路有哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "telecom_fit"],
    ),
    Blueprint(
        key="sms_delay",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} 短信下发延迟从 {time_window} 开始升高，当前业务方在催，下一步怎么问更有效？",
            "短信发送成功但到达慢，已经拿到部分网元线索，下一步问题怎么设计？",
            "{service} 时延变差，目前怀疑短信中心或信令链路，下一步该怎么追问？",
        ],
        rewritten_template="定位 {region} 短信下发时延升高的主因，并继续区分短信中心、信令链路或下游网元问题",
        plan_steps=["确认影响范围和时间窗口", "检查短信中心队列和处理时延", "核查信令链路质量", "确认下游网元响应情况", "对齐业务高峰和重传情况"],
        result_templates=[
            "目前已确认短信提交成功率正常，但从 {time_window} 开始下发时延明显抬升，短信中心队列长度波动较大。",
            "当前结果显示短信中心未退服，但信令链路出现短时 {alarm}，同时重传次数增加。",
            "执行结果发现下发慢问题主要出现在 {region}，并且与业务高峰高度重合。",
        ],
        next_question_templates=[
            "要不要继续拉取短信中心队列长度和处理时延，确认瓶颈是在接收侧还是下发侧？",
            "是否继续核查信令链路重传和时延，对齐 {time_window} 的短信慢时刻？",
            "要不要把慢短信按区域和运营商互联方向拆开，确认是否集中在特定下游链路？",
            "是否继续对比业务高峰前后负载，判断是容量瓶颈还是偶发链路抖动？",
        ],
        history_templates=["短信延迟怎么排查？", "短信中心队列高怎么办？", "短信下发慢看什么指标？", "{region} 短信异常区域有哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "telecom_fit"],
    ),
    Blueprint(
        key="high_interference_cell",
        intent="故障诊断",
        repeats=8,
        question_templates=[
            "{region} 某片区高干扰告警持续升高，业务 KPI 也变差，下一步问题怎么问？",
            "无线侧怀疑同频干扰，目前看到 PRB 和上行质量都有异常，下一步该怎么继续？",
            "{service} 体验变差，排到无线侧像是干扰问题，想设计下一步问题。",
        ],
        rewritten_template="定位 {region} 无线高干扰问题的主因，并继续判断是同频干扰、外部干扰还是参数配置问题",
        plan_steps=["确认受影响小区和时间窗口", "核查干扰相关 KPI", "检查邻区关系和参数", "对比频点和负载变化", "按站点和扇区继续下钻"],
        result_templates=[
            "目前已确认高干扰主要集中在 {time_window}，同时 {metric} 和上行质量同步恶化。",
            "当前结果显示告警集中在同频站点群，且部分小区 PRB 利用率在高峰期明显升高。",
            "执行结果发现问题更偏向城区热点区域，但是否为外部干扰源仍未确认。",
        ],
        next_question_templates=[
            "要不要继续按站点、扇区和频点维度下钻，确认高干扰是否集中在同频邻区？",
            "是否继续核查邻区关系和功率参数，判断是否存在参数配置引发的干扰？",
            "要不要把干扰 KPI 和 PRB 利用率按 {time_window} 对齐，确认是否由高负载诱发？",
            "是否继续结合路测或频谱信息，排除外部干扰源导致的异常？",
        ],
        history_templates=["高干扰怎么排查？", "同频干扰怎么看？", "PRB 高会导致干扰吗？", "{region} 干扰严重小区有哪些？"],
        evaluation_focus=["next_step", "fault_isolation", "telecom_fit"],
    ),
]


ANALYTICS_BLUEPRINTS = [
    Blueprint(
        key="traffic_spike_analysis",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} {time_window} 流量突然升高，我已经拿到初步结果，下一步应该推荐什么问题？",
            "智能问数结果显示区域流量突增，但还没下钻完，下一步问题怎么设计？",
            "{service} 在 {time_window} 波动明显，想继续做数据下钻，下一步问什么更合理？",
        ],
        rewritten_template="针对 {region} 流量突增结果继续下钻，定位主要贡献维度与异常来源",
        plan_steps=["确认异常时间窗口", "对比历史基线和阈值", "按区域和站点拆分贡献度", "按业务类型继续下钻", "结合告警和资源指标交叉验证"],
        result_templates=[
            "当前结果显示 {time_window} 流量较基线上升超过 {threshold}，主要贡献来自少数站点，但还未拆到小区层。",
            "已确认 {region} 流量突增不是全网普涨，而是局部热点拉动，且部分站点伴随 {metric} 波动。",
            "执行结果发现异常集中在 {vendor} 设备站点群，不过是否为活动流量还是网络异常暂时不明确。",
        ],
        next_question_templates=[
            "要不要继续按站点和小区维度下钻，确认哪几个对象对流量突增贡献最大？",
            "是否继续把流量结果按业务类型拆分，判断是视频、游戏还是通用数据业务拉动？",
            "要不要结合 {threshold} 波动阈值过滤噪声，只保留真正突变的站点再分析？",
            "是否继续把异常站点的告警、PRB 利用率和回传带宽一起对齐，判断是自然热点还是网络异常？",
        ],
        history_templates=["区域流量突增怎么分析？", "流量异常需要看哪些维度？", "站点流量 TopN 怎么查？", "{region} 流量高峰站点有哪些？"],
        evaluation_focus=["next_step", "drill_down", "threshold_usage"],
    ),
    Blueprint(
        key="complaint_kpi_correlation",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} 投诉量这两天上升，我已经拿到初步问数结果，下一步想继续关联 KPI。",
            "智能问数显示投诉和网络指标可能相关，但还不够明确，下一步问题怎么问？",
            "用户投诉突然增多，想在问数链路里继续下钻，什么问题最像下一步？",
        ],
        rewritten_template="针对 {region} 投诉上升结果继续下钻，定位与投诉最相关的网络 KPI 和对象",
        plan_steps=["确认投诉时间和区域分布", "对齐网络 KPI 变化", "按站点与业务类型关联", "按用户群体与终端维度继续下钻", "输出最可能关联因子"],
        result_templates=[
            "当前结果显示投诉高峰与 {metric} 波动时间接近，但还未确认主要集中在哪些站点和业务类型。",
            "已发现投诉主要来自 {region}，且与部分站点的质量指标恶化同向，不过关联对象仍较粗。",
            "执行结果表明高投诉区域与 {alarm} 有时序重叠，但是否存在用户侧或终端侧因素还未拆解。",
        ],
        next_question_templates=[
            "要不要继续按站点和小区维度下钻，确认哪些对象同时出现投诉上升和 KPI 恶化？",
            "是否继续把投诉按业务类型和终端型号拆分，判断问题更偏语音、数据还是特定终端？",
            "要不要继续对齐投诉高峰前后 1 小时的关键 KPI，验证时序上是否存在明显先后关系？",
            "是否继续筛出超过 {threshold} 波动的 KPI，只保留与投诉变化更相关的异常因子？",
        ],
        history_templates=["投诉和 KPI 怎么做关联分析？", "投诉上升看哪些指标？", "高投诉站点 TopN 怎么查？", "{region} 投诉集中在哪些业务？"],
        evaluation_focus=["next_step", "drill_down", "correlation_reasoning"],
    ),
    Blueprint(
        key="drop_rate_drilldown",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} 掉线率比基线高了不少，现在已经查到区域层，下一步问什么更合理？",
            "问数结果显示掉线率异常，但还没定位到站点或时段，下一步想继续下钻。",
            "{service} 掉线率在 {time_window} 明显升高，如何设计下一步问题？",
        ],
        rewritten_template="针对 {region} 掉线率异常结果继续下钻，定位关键站点、时间和伴随指标",
        plan_steps=["确认时间窗口和基线", "按区域到站点拆分", "按业务和场景继续拆分", "补充伴随 KPI 对比", "定位最主要异常来源"],
        result_templates=[
            "当前结果显示 {time_window} 掉线率较基线上升超过 {threshold}，但异常站点和业务场景还未完全展开。",
            "已确认异常主要发生在 {region}，同时 {metric} 也有联动，但目前只看到区域级汇总。",
            "执行结果表明掉线率上升更集中在高负载时段，不过是否是单站点拉高还不确定。",
        ],
        next_question_templates=[
            "要不要继续按站点和小区维度下钻，确认掉线率异常是否由少数对象集中贡献？",
            "是否继续把结果按时段拆成高峰与非高峰，判断异常是否只出现在特定窗口？",
            "要不要继续对齐切换失败率、弱覆盖和回传丢包，找出和掉线率最同步的指标？",
            "是否继续按照 {threshold} 波动门槛筛选异常对象，避免把轻微波动也纳入分析？",
        ],
        history_templates=["掉线率异常怎么下钻？", "站点掉线率 TopN 怎么查？", "掉线率和切换失败率怎么关联？", "{region} 掉线率高的时段是什么？"],
        evaluation_focus=["next_step", "drill_down", "telecom_fit"],
    ),
    Blueprint(
        key="home_broadband_offline_topn",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} 家宽离线用户数变多，问数结果已经给到区域汇总，下一步该问什么？",
            "智能问数查到家宽离线增加，但还需要继续下钻，下一步问题怎么设计？",
            "{time_window} 家宽离线数异常，想继续从数据里找主因，下一步问什么更合适？",
        ],
        rewritten_template="针对 {region} 家宽离线数异常继续下钻，定位主要 PON 口、片区和时间特征",
        plan_steps=["确认离线时间窗口", "按区域和局站拆分", "按 OLT/PON 口下钻", "对齐告警和光功率结果", "识别主贡献对象"],
        result_templates=[
            "当前结果显示 {time_window} 家宽离线数较平时明显升高，但目前只定位到区域层。",
            "已发现离线增加主要集中在 {region}，并伴随部分 OLT 的 {alarm}，但还没拆到 PON 口。",
            "执行结果表明异常更偏向少数片区和局站，不过是否由同一光路引起暂不清楚。",
        ],
        next_question_templates=[
            "要不要继续按 OLT 和 PON 口维度下钻，确认哪些对象贡献了最多离线用户？",
            "是否继续把离线用户按片区和楼宇聚合，判断异常是否集中在同一条光路或分光器？",
            "要不要继续对齐光功率、LOS/LOF 告警和离线开始时刻，验证是否存在同源问题？",
            "是否继续筛选超过 {threshold} 波动的 OLT/PON 口，优先关注真正异常的对象？",
        ],
        history_templates=["家宽离线数怎么下钻？", "PON 口离线用户 TopN 怎么看？", "OLT 告警和离线怎么关联？", "{region} 家宽异常片区有哪些？"],
        evaluation_focus=["next_step", "drill_down", "telecom_fit"],
    ),
    Blueprint(
        key="roaming_failure_heatmap",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} 漫游失败率这周有点高，问数只看到大盘结果，下一步问题怎么设计？",
            "智能问数显示国际漫游失败增加，但还没拆到方向和运营商，下一步怎么问？",
            "我想继续下钻漫游失败热力分布，当前结果还不够细。",
        ],
        rewritten_template="针对 {region} 漫游失败率异常继续下钻，定位方向、运营商和时间窗口上的贡献差异",
        plan_steps=["确认异常时间范围", "按国家和运营商方向拆分", "按入境与出境业务拆分", "对齐失败码和信令方向", "定位最关键异常对象"],
        result_templates=[
            "当前结果显示本周漫游失败率高于基线，但目前只看到整体趋势，尚未拆到方向和运营商。",
            "已确认异常主要发生在 {region}，且部分国家方向失败率更高，不过还未对齐失败码。",
            "执行结果显示入境与出境业务表现不一致，但还没继续下钻到运营商层。",
        ],
        next_question_templates=[
            "要不要继续按国家和归属运营商维度下钻，确认哪些方向贡献了最多失败？",
            "是否继续把入境和出境漫游拆开分析，判断异常是否只集中在单一业务方向？",
            "要不要继续对齐失败码和时间窗口，确认是否存在特定码值驱动的失败高峰？",
            "是否继续按 {threshold} 波动门槛筛出显著异常方向，避免被轻微波动干扰？",
        ],
        history_templates=["漫游失败率异常怎么下钻？", "国家方向失败率怎么查？", "漫游失败和失败码怎么关联？", "{region} 漫游失败高的运营商有哪些？"],
        evaluation_focus=["next_step", "drill_down", "telecom_fit"],
    ),
    Blueprint(
        key="power_alarm_impact_analysis",
        intent="智能问数",
        repeats=6,
        question_templates=[
            "{region} 电源告警增多后，想看它对业务 KPI 的影响，当前结果还比较粗，下一步怎么问？",
            "智能问数显示电源告警和业务波动可能有关，但还没量化，下一步问题怎么设计？",
            "我想从问数结果继续判断电源告警影响了哪些站点和 KPI，下一步问什么？",
        ],
        rewritten_template="针对 {region} 电源告警影响分析结果继续下钻，定位受影响站点、时间和业务 KPI",
        plan_steps=["确认电源告警时间窗口", "对齐业务 KPI 波动", "按站点维度拆分影响", "按业务类型和影响程度排序", "识别主要受影响对象"],
        result_templates=[
            "当前结果显示电源告警与 {metric} 波动存在时序重叠，但还未明确是哪批站点贡献了主要影响。",
            "已确认 {region} 部分站点电源告警增多后业务 KPI 有抬升，不过还没有拆到时间和站点层。",
            "执行结果表明电源告警影响并非全区域一致，疑似集中在少数站点和时段。",
        ],
        next_question_templates=[
            "要不要继续按站点和时间窗口下钻，确认哪些对象在电源告警后 KPI 恶化最明显？",
            "是否继续把业务 KPI 按语音、数据和接入类拆分，判断电源告警对哪类业务影响最大？",
            "要不要继续对齐告警发生前后 1 小时的关键 KPI，验证是否存在明显的先后关系？",
            "是否继续筛选超过 {threshold} 波动的站点，只保留受影响显著的对象做归因？",
        ],
        history_templates=["电源告警影响怎么分析？", "告警和 KPI 如何做时序对齐？", "受电源告警影响的站点怎么查？", "{region} 电源告警多的站点有哪些？"],
        evaluation_focus=["next_step", "drill_down", "correlation_reasoning"],
    ),
]


ALL_BLUEPRINTS = KNOWLEDGE_BLUEPRINTS + DIAGNOSIS_BLUEPRINTS + ANALYTICS_BLUEPRINTS


def build_cases() -> Iterable[dict]:
    case_id = 1
    difficulty_iter = iter(DIFFICULTIES)
    for blueprint in ALL_BLUEPRINTS:
        for variant in range(blueprint.repeats):
            yield render_case(case_id, blueprint, variant, next(difficulty_iter))
            case_id += 1


def write_jsonl(cases: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in cases:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def summarize(cases: list[dict]) -> None:
    multi_intent_count = sum(isinstance(case["intent"], list) for case in cases)
    print(f"Generated {len(cases)} cases")
    print(f"Intent distribution: {dict(Counter('+'.join(case['intent']) if isinstance(case['intent'], list) else case['intent'] for case in cases))}")
    print(f"Difficulty distribution: {dict(Counter(case['difficulty'] for case in cases))}")
    print(f"Multi-intent cases: {multi_intent_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate telecom next-step-question evaluation set.")
    parser.add_argument("--output", default="evals/next_step_eval_v1.jsonl")
    args = parser.parse_args()

    cases = list(build_cases())
    if len(cases) != TOTAL_CASES:
        raise ValueError(f"Expected {TOTAL_CASES} cases, got {len(cases)}")
    write_jsonl(cases, Path(args.output))
    summarize(cases)


if __name__ == "__main__":
    main()
