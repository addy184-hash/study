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


def decompose_skill(goal: str, base: str, hours: float, deadline: str) -> dict:
    """技能拆解：生成两套方案，含先修知识、难度分级"""
    system = """你是课程拆解专家，为学习目标生成两套学习方案（速成版/扎实版），每套含阶段化技能树。
每个知识点标注：name名称、difficulty难度(入门/进阶/高阶)、prerequisites先修知识数组、hours预计学时。
输出严格JSON：
{"plans":[{"plan_name":"速成版","description":"适合时间紧张快速入门","stages":[{"stage_name":"阶段名","knowledge_points":[{"name":"知识点","difficulty":"入门","prerequisites":["前置"],"hours":2}],"expected_ability":"达成能力","suggested_days":7}]},{"plan_name":"扎实版","description":"适合稳扎稳打","stages":[...]}]}
只返回JSON。"""
    user = f"目标：{goal}\n基础：{base}\n每日：{hours}小时\n截止：{deadline}"
    return call_llm(system, user)


def recommend_resources(skill_tree: dict) -> dict:
    """资源推荐：为每个知识点匹配资源，区分类型"""
    system = """你是学习资源推荐专家，为每个知识点匹配资源。
资源类型标注type：视频/文档/书籍/实战/刷题。
输出严格JSON：
{"resources":[{"knowledge_point":"知识点","beginner":[{"name":"资源名","type":"视频"}],"advanced":[{"name":"资源名","type":"文档"}],"practice":[{"name":"练习名","type":"实战"}]}]}
只返回JSON。"""
    user = f"为以下技能树匹配资源：\n{json.dumps(skill_tree, ensure_ascii=False)}"
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
