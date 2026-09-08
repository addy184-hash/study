"""智能学习伴侣 - 多智能体核心模块"""
import json
from openai import OpenAI
import config


def _client():
    """延迟初始化OpenAI客户端"""
    return OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict:
    """统一调用大模型，返回解析后的JSON"""
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
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


# ===== 智能体1：技能拆解 =====
def decompose_skill(goal: str, base: str, hours: float, deadline: str) -> dict:
    system = """你是课程拆解专家，将学习目标拆解为分层技能树，输出严格JSON。
格式：{"stages":[{"stage_name":"阶段名","knowledge_points":["知识点"],"expected_ability":"达成能力","suggested_days":7}],"total_weeks":4}
只返回JSON。"""
    user = f"目标：{goal}\n基础：{base}\n每日：{hours}小时\n截止：{deadline}"
    return call_llm(system, user)


# ===== 智能体2：资源推荐 =====
def recommend_resources(skill_tree: dict) -> dict:
    system = """你是学习资源推荐专家，为每个知识点匹配资源，输出严格JSON。
格式：{"resources":[{"knowledge_point":"知识点","beginner":["入门资源"],"advanced":["进阶资源"],"practice":["实战练习"]}]}
只返回JSON。"""
    user = f"为以下技能树匹配资源：\n{json.dumps(skill_tree, ensure_ascii=False)}"
    return call_llm(system, user)


# ===== 智能体3：计划生成 =====
def generate_plan(skill_tree: dict, hours: float) -> dict:
    system = """你是学习计划排程专家，根据技能树和每日时间生成周计划，输出严格JSON。
格式：{"weekly_plan":[{"week":1,"theme":"主题","days":[{"day":"周一","task":"内容","hours":1.5,"type":"理论/实操"}]}]}
只返回JSON。"""
    user = f"技能树：{json.dumps(skill_tree, ensure_ascii=False)}\n每日：{hours}小时"
    return call_llm(system, user)


# ===== 智能体4：动态调优 =====
def adjust_plan(plan: dict, feedback: str) -> dict:
    system = """你是学习计划调优专家，根据反馈调整路线，已掌握的跳过，薄弱点加强，输出严格JSON。
格式与原计划一致，只返回JSON。"""
    user = f"当前计划：{json.dumps(plan, ensure_ascii=False)}\n反馈：{feedback}"
    return call_llm(system, user)
