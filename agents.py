"""智能学习伴侣 - LangGraph多智能体核心模块"""
import json
from typing import TypedDict, List, Dict, Any
from openai import OpenAI
from langgraph.graph import StateGraph, END
import config


# ========== LLM 基础调用 ==========
def _client():
    return OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict:
    try:
        resp = _client().chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}


def call_llm_text(system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
    """非JSON格式的LLM调用，用于普通问答"""
    try:
        resp = _client().chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"回答时出错：{str(e)}"


# ========== 多智能体共享状态 ==========
class LearningState(TypedDict):
    """三智能体共享的全局状态"""
    goal: str
    base: str
    hours: float
    deadline: str
    preference: List[str]
    skill_tree: Dict[str, Any]       # 任务拆分智能体输出
    resources: Dict[str, Any]        # 资源推荐智能体输出
    plan: Dict[str, Any]             # 计划调优智能体输出
    completed_kps: List[str]
    feedback: str                    # 用户反馈，供调优智能体使用
    error: str


# ========== 智能体1：任务拆分智能体 (Planner Agent) ==========
def planner_agent(state: LearningState) -> Dict[str, Any]:
    """
    角色：课程拆解专家
    职责：将学习目标拆解为层级化技能树，输出两套方案
    读取：goal, base, hours, deadline, preference
    写入：skill_tree
    """
    pref_text = "、".join(state.get("preference", [])) or "无特殊偏好"
    system = f"""你是【课程拆解专家】，为学习目标生成两套学习方案（速成版/扎实版），每套含阶段化技能树。
用户学习偏好：{pref_text}，请在拆解时适当侧重偏好的学习方式。
每个知识点标注：name名称、difficulty难度(入门/进阶/高阶)、prerequisites先修知识数组、hours预计学时。
输出严格JSON：
{{"plans":[{{"plan_name":"速成版","description":"适合时间紧张快速入门","stages":[{{"stage_name":"阶段名","knowledge_points":[{{"name":"知识点","difficulty":"入门","prerequisites":["前置"],"hours":2}}],"expected_ability":"达成能力","suggested_days":7}}]}},{{"plan_name":"扎实版","description":"适合稳扎稳打","stages":[...]}}]}}
只返回JSON。"""
    user = f"目标：{state['goal']}\n基础：{state['base']}\n每日：{state['hours']}小时\n截止：{state['deadline']}\n偏好：{pref_text}"

    result = call_llm(system, user)
    if "error" in result:
        return {"error": f"任务拆分智能体出错：{result['error']}"}
    return {"skill_tree": result}


# ========== 智能体2：资源推荐智能体 (Researcher Agent) ==========
def researcher_agent(state: LearningState) -> Dict[str, Any]:
    """
    角色：学习资源研究员
    职责：根据技能树为每个知识点匹配学习资源
    读取：skill_tree, preference
    写入：resources
    """
    pref_text = "、".join(state.get("preference", [])) or "无特殊偏好"
    skill_tree = state.get("skill_tree", {})
    system = f"""你是【学习资源研究员】，为每个知识点匹配资源。
用户偏好：{pref_text}，请优先推荐符合偏好的资源类型。
资源类型标注type：视频/文档/书籍/实战/刷题。
输出严格JSON：
{{"resources":[{{"knowledge_point":"知识点","beginner":[{{"name":"资源名","type":"视频"}}],"advanced":[{{"name":"资源名","type":"文档"}}],"practice":[{{"name":"练习名","type":"实战"}}]}}]}}
只返回JSON。"""
    user = f"为以下技能树匹配资源：\n{json.dumps(skill_tree, ensure_ascii=False)}\n用户偏好：{pref_text}"

    result = call_llm(system, user)
    if "error" in result:
        return {"error": f"资源推荐智能体出错：{result['error']}"}
    return {"resources": result}


# ========== 智能体3：计划调优智能体 (Coach Agent) ==========
def coach_agent(state: LearningState) -> Dict[str, Any]:
    """
    角色：学习教练
    职责：生成周计划（含艾宾浩斯复习），或根据用户反馈动态调整计划
    读取：skill_tree, hours, plan, feedback, completed_kps
    写入：plan
    """
    if state.get("feedback"):
        # 调优模式：根据反馈调整现有计划
        plan = state.get("plan", {})
        system = """你是【学习教练】，根据用户反馈调整学习路线。
已掌握的知识点跳过，薄弱点加强练习，保持原JSON格式。
输出严格JSON，只返回调整后的plan。"""
        user = f"当前计划：{json.dumps(plan, ensure_ascii=False)}\n已掌握：{json.dumps(state.get('completed_kps', []), ensure_ascii=False)}\n用户反馈：{state['feedback']}"
        result = call_llm(system, user)
        if "error" in result:
            return {"error": f"计划调优智能体出错：{result['error']}"}
        return {"plan": result, "feedback": ""}
    else:
        # 生成模式：从技能树生成全新计划
        skill_tree = state.get("skill_tree", {})
        system = """你是【学习教练】，根据技能树生成周计划，并按艾宾浩斯遗忘曲线插入复习节点。
学习日类型：理论/实操/复习。复习节点在学习后第1、3、7天安排。
输出严格JSON：
{"weekly_plan":[{"week":1,"theme":"主题","days":[{"day":"周一","task":"内容","hours":1.5,"type":"理论"}]}],"review_nodes":[{"after_day":1,"content":"复习内容","related_stage":"阶段名"}]}
只返回JSON。"""
        user = f"技能树：{json.dumps(skill_tree, ensure_ascii=False)}\n每日：{state['hours']}小时"
        result = call_llm(system, user)
        if "error" in result:
            return {"error": f"计划调优智能体出错：{result['error']}"}
        return {"plan": result}


# ========== 条件路由 ==========
def route_after_planner(state: LearningState) -> str:
    """任务拆分后 → 资源推荐"""
    if state.get("error"):
        return END
    return "researcher"


def route_after_researcher(state: LearningState) -> str:
    """资源推荐后 → 计划调优"""
    if state.get("error"):
        return END
    return "coach"


def route_after_coach(state: LearningState) -> str:
    """计划调优后 → 结束"""
    return END


# ========== 构建 LangGraph 图 ==========
def build_graph():
    """构建三智能体工作流图"""
    graph = StateGraph(LearningState)

    # 添加三个智能体节点
    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("coach", coach_agent)

    # 入口：任务拆分
    graph.set_entry_point("planner")

    # 边：planner → researcher → coach → END
    graph.add_conditional_edges("planner", route_after_planner, {
        "researcher": "researcher",
        END: END
    })
    graph.add_conditional_edges("researcher", route_after_researcher, {
        "coach": "coach",
        END: END
    })
    graph.add_conditional_edges("coach", route_after_coach, {
        END: END
    })

    return graph.compile()


# 全局图实例
_learning_graph = None

def get_graph():
    global _learning_graph
    if _learning_graph is None:
        _learning_graph = build_graph()
    return _learning_graph


# ========== 对外接口 ==========
def generate_learning_plan(goal: str, base: str, hours: float, deadline: str, preference: list = None) -> dict:
    """完整流程：任务拆分 → 资源推荐 → 计划生成"""
    state: LearningState = {
        "goal": goal,
        "base": base,
        "hours": hours,
        "deadline": deadline,
        "preference": preference or [],
        "skill_tree": {},
        "resources": {},
        "plan": {},
        "completed_kps": [],
        "feedback": "",
        "error": ""
    }
    result = get_graph().invoke(state)
    return result


def adjust_learning_plan(state: LearningState, feedback: str) -> dict:
    """仅调优：调用教练智能体调整计划"""
    state["feedback"] = feedback
    # 只跑coach节点，从中间开始
    graph = StateGraph(LearningState)
    graph.add_node("coach", coach_agent)
    graph.set_entry_point("coach")
    graph.add_edge("coach", END)
    coach_only = graph.compile()
    result = coach_only.invoke(state)
    return result


def extract_info(message: str) -> dict:
    """从用户消息中提取学情信息"""
    system = """你是信息提取助手，从用户消息中提取学习相关信息。
输出严格JSON：{"goal":"学习目标(没有则空字符串)","base":"基础描述(没有则空字符串)","hours":每日学习小时数(数字，没有则0),"deadline":"截止时间(没有则空字符串)","preference":["偏好列表，没有则空数组"]}
只返回JSON。"""
    result = call_llm(system, message)
    return result if "error" not in result else {"goal": "", "base": "", "hours": 0, "deadline": "", "preference": []}


def generate_plan_reply(conv: dict) -> str:
    """调用三智能体生成计划，返回友好文字回复"""
    goal = conv.get("goal", "")
    base = conv.get("base", "零基础")
    hours = conv.get("hours", 2)
    deadline = conv.get("deadline", "1个月")
    preference = conv.get("preference", [])

    result = generate_learning_plan(goal, base, hours, deadline, preference)

    if result.get("error"):
        return f"生成计划时出错：{result['error']}"

    conv["skill_tree"] = result.get("skill_tree", {})
    conv["resources"] = result.get("resources", {})
    conv["plan"] = result.get("plan", {})
    conv["stage"] = "learning"

    plans = conv["skill_tree"].get("plans", [])
    if plans:
        p = plans[0]
        stages = p.get("stages", [])
        total_kps = sum(len(s.get("knowledge_points", [])) for s in stages)
        reply = f"已为你生成「{goal}」的学习计划！\n\n"
        reply += f"方案：{p.get('plan_name','')}（{p.get('description','')}）\n"
        reply += f"共 {len(stages)} 个阶段，{total_kps} 个知识点\n\n"
        reply += "阶段概览：\n"
        for i, s in enumerate(stages, 1):
            reply += f"{i}. {s.get('stage_name','')}（约{s.get('suggested_days','?')}天）\n"
        reply += "\n你可以随时告诉我学习进度，我会帮你调整计划。下方可查看详细技能树、资源推荐和周计划。"
        return reply
    return "计划生成失败，请重试。"


# ========== 智能意图识别 ==========
def detect_intent(message: str, stage: str, conv: dict) -> dict:
    """
    细粒度意图识别，返回 {"action": "...", "target": "...", "summary": "..."}
    """
    # 规则匹配（快速通道，不用调LLM）
    msg = message.strip()

    # 打招呼
    if msg in ["你好", "hi", "hello", "在吗", "在么", "嗨"]:
        return {"action": "greeting"}

    # 用默认设置
    if "默认" in msg and ("设置" in msg or "就行" in msg or "开始" in msg):
        return {"action": "use_default"}

    # 查看进度
    if any(k in msg for k in ["进度", "完成了多少", "学到哪", "学了多少", "掌握了多少"]):
        return {"action": "show", "target": "progress"}

    # 查看计划
    if any(k in msg for k in ["计划", "周计划", "学习安排", "接下来学什么", "下一步", "今天学什么"]):
        if "下一步" in msg or "接下来" in msg or "今天学什么" in msg:
            return {"action": "next_step"}
        return {"action": "show", "target": "plan"}

    # 查看资源
    if any(k in msg for k in ["资源", "资料", "推荐", "看什么", "学什么材料"]):
        return {"action": "show", "target": "resources"}

    # 测试题
    if any(k in msg for k in ["测试", "出题", "考考我", "练习", "做题", "测验"]):
        return {"action": "quiz"}

    # 情绪/鼓励
    if any(k in msg for k in ["太难了", "学不会", "想放弃", "好累", "焦虑", "压力大", "没信心", "学不下去"]):
        return {"action": "motivation"}

    # 感谢/结束
    if any(k in msg for k in ["谢谢", "感谢", "辛苦了", "拜拜", "再见"]):
        return {"action": "thanks"}

    # LLM深度判断
    system = """你是对话意图识别专家，判断用户消息的意图。
可选意图：
- adjust: 用户汇报学习进度、说某个知识点掌握了/没掌握、遇到困难、要求调整计划
- answer: 用户问知识性问题、概念解释、学习方法
- clarify: 用户在回答之前的问题、补充信息
- motivation: 用户表达消极情绪、需要鼓励
只返回JSON：{"action":"adjust/answer/clarify/motivation","summary":"一句话摘要"}"""
    result = call_llm(system, f"对话阶段：{stage}\n用户消息：{msg}")
    if "error" not in result:
        return result
    return {"action": "answer", "summary": ""}


def get_next_step(conv: dict) -> str:
    """根据当前进度，建议下一步学什么"""
    skill_tree = conv.get("skill_tree", {})
    completed = set(conv.get("completed_kps", []))
    plans = skill_tree.get("plans", [])
    if not plans:
        return "还没有生成学习计划，请先告诉我你的学习目标。"

    stages = plans[0].get("stages", [])
    for stage in stages:
        for kp in stage.get("knowledge_points", []):
            kp_name = kp.get("name", "") if isinstance(kp, dict) else str(kp)
            if kp_name not in completed:
                # 检查先修是否完成
                prereq = kp.get("prerequisites", []) if isinstance(kp, dict) else []
                unmet = [p for p in prereq if p not in completed]
                if unmet:
                    return f"建议先学习「{unmet[0]}」，它是「{kp_name}」的先修知识。\n\n打好基础后再学「{kp_name}」会更顺利。"
                diff = kp.get("difficulty", "") if isinstance(kp, dict) else ""
                hours = kp.get("hours", "") if isinstance(kp, dict) else ""
                return f"下一步建议学习：「{kp_name}」\n\n难度：{diff} | 预计：{hours}小时\n\n学完后告诉我，我帮你记录进度并调整后续计划。"
    return "太棒了！所有知识点都已掌握，你可以进入综合实战阶段了。需要我推荐一些项目练习吗？"


def generate_motivation(conv: dict) -> str:
    """根据学习情况生成鼓励话语"""
    completed = len(conv.get("completed_kps", []))
    goal = conv.get("goal", "这个目标")
    if completed == 0:
        return f"刚开始学{goal}遇到困难很正常，每个人都是从零开始的。\n\n建议你：\n1. 把大目标拆成小任务，每天只专注一个知识点\n2. 遇到不懂的先跳过，回头再看会豁然开朗\n3. 学完一个知识点就来告诉我，我帮你记录进度\n\n你已经迈出了最难的第一步，继续加油！"
    else:
        return f"你已经掌握了{completed}个知识点，这说明你完全有能力学会{goal}！\n\n学习曲线本来就是先慢后快，现在正是爬坡期。\n\n建议：\n1. 回顾一下已掌握的内容，你会发现自己进步很大\n2. 把当前困难的知识点告诉我，我可以调整计划，增加基础练习\n3. 适当休息，劳逸结合效率更高\n\n有任何问题随时问我，我一直在这里陪你学习。"


# ========== 对话处理（智能版） ==========
def process_chat_message(conv: dict, user_message: str) -> str:
    """处理对话消息，更新conv状态，返回AI回复"""
    stage = conv.get("stage", "collecting")

    # 统一意图识别
    intent = detect_intent(user_message, stage, conv)
    action = intent.get("action", "answer")

    # ===== 通用意图（两个阶段都适用） =====
    if action == "greeting":
        if stage == "collecting":
            return "你好！我是你的智能学习伴侣。请告诉我你想学什么，比如「我想在1个月内学会Python数据分析」，我会为你生成个性化的学习计划。"
        else:
            return f"你好！继续学习「{conv.get('goal','')}」吗？你可以告诉我学习进度，或者问我任何问题。"

    if action == "thanks":
        return "不客气！学习是一场马拉松，坚持就是胜利。有任何问题随时来找我。"

    if action == "motivation":
        return generate_motivation(conv)

    # ===== 收集学情阶段 =====
    if stage == "collecting":
        if action == "use_default":
            if not conv.get("goal"):
                conv["goal"] = "通用学习"
            conv["base"] = conv.get("base") or "零基础"
            conv["hours"] = conv.get("hours") or 2
            conv["deadline"] = conv.get("deadline") or "1个月"
            return generate_plan_reply(conv)

        if action == "clarify" or action == "answer":
            # 用户在补充信息
            info = extract_info(user_message)
            updated = []
            if info.get("goal") and not conv.get("goal"):
                conv["goal"] = info["goal"]
                updated.append(f"学习目标：{info['goal']}")
            if info.get("base") and not conv.get("base"):
                conv["base"] = info["base"]
                updated.append(f"现有基础：{info['base']}")
            if info.get("hours", 0) > 0 and conv.get("hours", 0) == 0:
                conv["hours"] = info["hours"]
                updated.append(f"每日时长：{info['hours']}小时")
            if info.get("deadline") and not conv.get("deadline"):
                conv["deadline"] = info["deadline"]
                updated.append(f"截止时间：{info['deadline']}")
            if info.get("preference"):
                conv["preference"] = info["preference"]

            missing = []
            if not conv.get("goal"):
                missing.append("学习目标")
            if not conv.get("base"):
                missing.append("现有基础")
            if conv.get("hours", 0) == 0:
                missing.append("每日学习时长")

            if missing:
                prefix = f"已记录：{'、'.join(updated)}\n\n" if updated else ""
                return f"{prefix}还需要了解：{'、'.join(missing)}\n\n请告诉我这些信息，或者说「用默认设置」直接开始。"
            else:
                return generate_plan_reply(conv)

        # adjust在收集阶段当作补充信息处理
        if action == "adjust":
            info = extract_info(user_message)
            if info.get("goal"):
                conv["goal"] = info["goal"]
            if info.get("base"):
                conv["base"] = info["base"]
            if info.get("hours", 0) > 0:
                conv["hours"] = info["hours"]
            if info.get("deadline"):
                conv["deadline"] = info["deadline"]

            missing = []
            if not conv.get("goal"):
                missing.append("学习目标")
            if not conv.get("base"):
                missing.append("现有基础")
            if conv.get("hours", 0) == 0:
                missing.append("每日学习时长")

            if missing:
                return f"还缺少：{'、'.join(missing)}\n\n请补充这些信息，或者说「用默认设置」直接开始。"
            else:
                return generate_plan_reply(conv)

    # ===== 学习中阶段 =====
    elif stage == "learning":
        if action == "show":
            target = intent.get("target", "plan")
            if target == "progress":
                completed = len(conv.get("completed_kps", []))
                plans = conv.get("skill_tree", {}).get("plans", [])
                total = sum(len(s.get("knowledge_points", [])) for s in plans[0].get("stages", [])) if plans else 0
                pct = int(completed / total * 100) if total > 0 else 0
                return f"当前学习进度：{completed}/{total} 知识点（{pct}%）\n\n已掌握：{', '.join(conv.get('completed_kps', [])) if completed > 0 else '暂无'}\n\n继续加油！可以在下方「学习进度」标签页勾选已掌握的知识点。"
            elif target == "resources":
                return "好的，你可以在下方「资源推荐」标签页查看为每个知识点匹配的学习资源，每个资源都带B站和百度搜索链接。"
            else:
                return "好的，你可以在下方「学习计划」标签页查看当前的周计划和艾宾浩斯复习节点。"

        if action == "next_step":
            return get_next_step(conv)

        if action == "quiz":
            # 生成当前阶段的测试题
            skill_tree = conv.get("skill_tree", {})
            plans = skill_tree.get("plans", [])
            if plans:
                stages = plans[0].get("stages", [])
                # 找第一个未完全掌握的阶段
                for stage in stages:
                    kps = stage.get("knowledge_points", [])
                    stage_kps = [kp.get("name","") if isinstance(kp,dict) else str(kp) for kp in kps]
                    if not all(k in conv.get("completed_kps", []) for k in stage_kps):
                        quiz = generate_quiz(stage)
                        if "error" not in quiz:
                            questions = quiz.get("questions", [])
                            reply = f"为你准备了「{stage.get('stage_name','')}」阶段的测试题：\n\n"
                            for i, q in enumerate(questions, 1):
                                reply += f"{i}. [{q.get('type','')}] {q.get('question','')}\n"
                                if q.get("options"):
                                    for opt in q["options"]:
                                        reply += f"   {opt}\n"
                            reply += "\n做完后告诉我你的答案，我帮你批改！"
                            return reply
            return "还没有可测试的阶段，先去学习吧。"

        if action == "adjust":
            # 先检查是否是在说某个知识点掌握了
            completed = conv.get("completed_kps", [])
            skill_tree = conv.get("skill_tree", {})
            all_kps = []
            plans = skill_tree.get("plans", [])
            if plans:
                for s in plans[0].get("stages", []):
                    for kp in s.get("knowledge_points", []):
                        all_kps.append(kp.get("name","") if isinstance(kp,dict) else str(kp))

            newly_completed = [kp for kp in all_kps if kp in user_message and kp not in completed]
            if newly_completed:
                for kp in newly_completed:
                    completed.append(kp)
                conv["completed_kps"] = completed

            # 调用教练智能体调整计划
            state: LearningState = {
                "goal": conv.get("goal", ""),
                "base": conv.get("base", ""),
                "hours": conv.get("hours", 2),
                "deadline": conv.get("deadline", ""),
                "preference": conv.get("preference", []),
                "skill_tree": conv.get("skill_tree", {}),
                "resources": conv.get("resources", {}),
                "plan": conv.get("plan", {}),
                "completed_kps": completed,
                "feedback": user_message,
                "error": ""
            }
            result = adjust_learning_plan(state, user_message)
            if result.get("error"):
                return f"调整计划时出错：{result['error']}"
            conv["plan"] = result.get("plan", conv["plan"])

            prefix = ""
            if newly_completed:
                prefix = f"已记录你掌握了：{'、'.join(newly_completed)}\n\n"
            return f"{prefix}已根据你的反馈调整了学习计划！\n\n薄弱环节我已经加强了练习，已掌握的内容做了精简。下方可查看更新后的周计划。"

        if action == "answer":
            # 普通问答，结合学习上下文
            system2 = f"""你是学习助手，用户正在学习「{conv.get('goal','')}」。
用户当前基础：{conv.get('base','')}，已掌握：{', '.join(conv.get('completed_kps', [])) or '暂无'}。
请用简洁友好的语气回答，结合用户的学习进度给出针对性建议。"""
            return call_llm_text(system2, user_message)

    return "我在听，请告诉我你的学习目标或进度。"
