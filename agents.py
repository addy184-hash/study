"""智能学习伴侣 - 多智能体核心模块"""
import json
from openai import OpenAI
import config


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


def decompose_skill(goal: str, base: str, hours: float, deadline: str, preference: list = None) -> dict:
    """技能拆解：生成两套方案，含先修知识、难度分级，考虑学习偏好"""
    pref_text = "、".join(preference) if preference else "无特殊偏好"
    system = f"""你是课程拆解专家，为学习目标生成两套学习方案（速成版/扎实版），每套含阶段化技能树。
用户学习偏好：{pref_text}，请在拆解时适当侧重偏好的学习方式。
每个知识点标注：name名称、difficulty难度(入门/进阶/高阶)、prerequisites先修知识数组、hours预计学时。
输出严格JSON：
{{"plans":[{{"plan_name":"速成版","description":"适合时间紧张快速入门","stages":[{{"stage_name":"阶段名","knowledge_points":[{{"name":"知识点","difficulty":"入门","prerequisites":["前置"],"hours":2}}],"expected_ability":"达成能力","suggested_days":7}}]}},{{"plan_name":"扎实版","description":"适合稳扎稳打","stages":[...]}}]}}
只返回JSON。"""
    user = f"目标：{goal}\n基础：{base}\n每日：{hours}小时\n截止：{deadline}\n偏好：{pref_text}"
    return call_llm(system, user)


def recommend_resources(skill_tree: dict, preference: list = None) -> dict:
    """资源推荐：为每个知识点匹配资源，考虑用户偏好"""
    pref_text = "、".join(preference) if preference else "无特殊偏好"
    system = f"""你是学习资源推荐专家，为每个知识点匹配资源。
用户偏好：{pref_text}，请优先推荐符合偏好的资源类型。
资源类型标注type：视频/文档/书籍/实战/刷题。
输出严格JSON：
{{"resources":[{{"knowledge_point":"知识点","beginner":[{{"name":"资源名","type":"视频"}}],"advanced":[{{"name":"资源名","type":"文档"}}],"practice":[{{"name":"练习名","type":"实战"}}]}}]}}
只返回JSON。"""
    user = f"为以下技能树匹配资源：\n{json.dumps(skill_tree, ensure_ascii=False)}\n用户偏好：{pref_text}"
    return call_llm(system, user)


def generate_plan(skill_tree: dict, hours: float) -> dict:
    """计划生成：含艾宾浩斯复习节点"""
    system = """你是学习计划排程专家，根据技能树生成周计划，并按艾宾浩斯遗忘曲线插入复习节点。
学习日类型：理论/实操/复习。复习节点在学习后第1、3、7天安排。
输出严格JSON：
{"weekly_plan":[{"week":1,"theme":"主题","days":[{"day":"周一","task":"内容","hours":1.5,"type":"理论"}]}],"review_nodes":[{"after_day":1,"content":"复习内容","related_stage":"阶段名"}]}
只返回JSON。"""
    user = f"技能树：{json.dumps(skill_tree, ensure_ascii=False)}\n每日：{hours}小时"
    return call_llm(system, user)


def adjust_plan(plan: dict, feedback: str) -> dict:
    """动态调优：根据反馈调整计划"""
    system = """你是学习计划调优专家，根据用户反馈调整路线。已掌握的跳过，薄弱点加强，保持原JSON格式。
只返回JSON。"""
    user = f"当前计划：{json.dumps(plan, ensure_ascii=False)}\n反馈：{feedback}"
    return call_llm(system, user)


def generate_quiz(stage: dict) -> dict:
    """生成阶段测试题"""
    system = """你是出题专家，为学习阶段生成5道测试题（3选择2简答），含答案。
输出严格JSON：
{"questions":[{"type":"选择","question":"题目","options":["A","B","C","D"],"answer":"A","explanation":"解析"},{"type":"简答","question":"题目","answer":"参考答案"}]}
只返回JSON。"""
    user = f"为以下阶段出题：\n{json.dumps(stage, ensure_ascii=False)}"
    return call_llm(system, user)


# ========== 对话式Agent ==========
def extract_info(message: str) -> dict:
    """从用户消息中提取学情信息"""
    system = """你是信息提取助手，从用户消息中提取学习相关信息。
输出严格JSON：{"goal":"学习目标(没有则空字符串)","base":"基础描述(没有则空字符串)","hours":每日学习小时数(数字，没有则0),"deadline":"截止时间(没有则空字符串)","preference":["偏好列表，没有则空数组"]}
只返回JSON。"""
    result = call_llm(system, message)
    return result if "error" not in result else {"goal": "", "base": "", "hours": 0, "deadline": "", "preference": []}


def generate_plan_reply(conv: dict) -> str:
    """生成学习计划并返回友好的文字回复"""
    goal = conv.get("goal", "")
    base = conv.get("base", "零基础")
    hours = conv.get("hours", 2)
    deadline = conv.get("deadline", "1个月")
    preference = conv.get("preference", [])

    skill_tree = decompose_skill(goal, base, hours, deadline, preference)
    if "error" in skill_tree:
        return f"生成计划时出错：{skill_tree['error']}"
    resources = recommend_resources(skill_tree, preference)
    plan = generate_plan(skill_tree, hours)

    conv["skill_tree"] = skill_tree
    conv["resources"] = resources
    conv["plan"] = plan
    conv["stage"] = "learning"

    # 生成文字摘要
    plans = skill_tree.get("plans", [])
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
        reply += "\n你可以随时告诉我学习进度，我会帮你调整计划。也可以点击下方按钮查看详细技能树和资源推荐。"
        return reply
    return "计划生成失败，请重试。"


def process_chat_message(conv: dict, user_message: str) -> str:
    """
    处理对话消息，返回AI回复文本，同时更新conv状态。
    conv是对话字典，包含goal/base/hours/deadline/preference/skill_tree/plan/stage等
    """
    stage = conv.get("stage", "collecting")

    # 阶段1：收集学情
    if stage == "collecting":
        info = extract_info(user_message)
        # 更新已有信息
        if info.get("goal"):
            conv["goal"] = info["goal"]
        if info.get("base"):
            conv["base"] = info["base"]
        if info.get("hours", 0) > 0:
            conv["hours"] = info["hours"]
        if info.get("deadline"):
            conv["deadline"] = info["deadline"]
        if info.get("preference"):
            conv["preference"] = info["preference"]

        # 检查是否信息齐全
        missing = []
        if not conv.get("goal"):
            missing.append("学习目标")
        if not conv.get("base"):
            missing.append("现有基础")
        if conv.get("hours", 0) == 0:
            missing.append("每日学习时长")

        if missing:
            return f"好的！我还需要了解一些信息：\n\n还缺少：{'、'.join(missing)}\n\n请告诉我这些信息，或者直接说'用默认设置'，我会按零基础、每天2小时、1个月来生成计划。"
        else:
            # 信息齐全，生成计划
            return generate_plan_reply(conv)

    # 阶段2：学习中，处理进度反馈或问题
    elif stage == "learning":
        # 判断是要调整计划还是普通提问
        system = """你是学习助手，判断用户消息是在汇报学习进度/反馈，还是普通提问。
如果是进度反馈，输出{"action":"adjust","summary":"反馈摘要"}
如果是查看计划/资源/进度，输出{"action":"show","target":"plan/resources/progress"}
如果是普通问题，输出{"action":"answer","question":"问题"}
只返回JSON。"""
        intent = call_llm(system, user_message)

        if intent.get("action") == "adjust":
            plan = conv.get("plan", {})
            if plan:
                new_plan = adjust_plan(plan, user_message)
                if "error" not in new_plan:
                    conv["plan"] = new_plan
                    return f"已根据你的反馈调整了学习计划！\n\n反馈：{intent.get('summary','')}\n\n你可以在下方查看更新后的周计划。薄弱环节我已经加强了练习，已掌握的内容做了精简。"
                else:
                    return f"调整计划时出错：{new_plan['error']}"
            else:
                return "还没有生成学习计划，请先告诉我你的学习目标。"

        elif intent.get("action") == "show":
            target = intent.get("target", "plan")
            if target == "progress":
                completed = len(conv.get("completed_kps", []))
                skill_tree = conv.get("skill_tree", {})
                plans = skill_tree.get("plans", [])
                total = 0
                if plans:
                    total = sum(len(s.get("knowledge_points", [])) for s in plans[0].get("stages", []))
                pct = int(completed / total * 100) if total > 0 else 0
                return f"当前学习进度：{completed}/{total} 知识点（{pct}%）\n\n已掌握：{', '.join(conv.get('completed_kps', [])) if completed > 0 else '暂无'}\n\n继续加油！有任何问题随时问我。"
            elif target == "resources":
                return "好的，你可以在下方「资源推荐」区域查看为每个知识点匹配的学习资源，每个资源都带B站和百度搜索链接。"
            else:
                return "好的，你可以在下方查看当前的周计划和艾宾浩斯复习节点。"

        else:
            # 普通问答，用LLM直接回答
            system2 = f"""你是学习助手，用户正在学习{conv.get('goal','')}。请用简洁友好的语气回答用户的问题。"""
            try:
                resp = _client().chat.completions.create(
                    model=config.DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": system2},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.5
                )
                return resp.choices[0].message.content
            except Exception as e:
                return f"回答时出错：{str(e)}"

    return "我在听，请告诉我你的学习目标或进度。"
