import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

def call_llm(system_prompt, user_prompt, temperature=0.3):
    """统一调用大模型"""
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except:
        return {"raw": content}


# ===== 智能体1：技能拆解 =====
def decompose_skill(goal, base, hours_per_day, deadline):
    system = """你是课程拆解专家，将用户学习目标拆解为分层技能树，输出严格JSON。
输出格式：
{
  "stages": [
    {
      "stage_name": "阶段名称",
      "knowledge_points": ["知识点1", "知识点2"],
      "expected_ability": "阶段达成能力",
      "suggested_days": 7
    }
  ],
  "total_weeks": 4
}
只返回JSON，不要多余解释。"""
    user = f"""用户目标：{goal}
现有基础：{base}
每日可投入：{hours_per_day}小时
截止时间：{deadline}
请根据时间合理分配每个阶段的天数。"""
    return call_llm(system, user)


# ===== 智能体2：资源推荐 =====
def recommend_resources(skill_tree):
    system = """你是学习资源推荐专家，为每个知识点匹配学习资源。
输出严格JSON格式：
{
  "resources": [
    {
      "knowledge_point": "知识点名称",
      "beginner": ["入门资源1", "入门资源2"],
      "advanced": ["进阶资源1"],
      "practice": ["实战练习建议"]
    }
  ]
}
资源类型包括：网课、书籍、文档、实战项目。只返回JSON。"""
    user = f"请为以下技能树的每个知识点推荐学习资源：\n{json.dumps(skill_tree, ensure_ascii=False)}"
    return call_llm(system, user)


# ===== 智能体3：计划生成 =====
def generate_plan(skill_tree, hours_per_day):
    system = """你是学习计划排程专家，根据技能树和每日时间生成周计划。
输出严格JSON：
{
  "weekly_plan": [
    {
      "week": 1,
      "theme": "本周主题",
      "days": [
        {"day": "周一", "task": "学习内容", "hours": 1.5, "type": "理论/实操"}
      ]
    }
  ]
}
合理分配理论学习和实操练习，只返回JSON。"""
    user = f"技能树：{json.dumps(skill_tree, ensure_ascii=False)}\n每日可用时间：{hours_per_day}小时"
    return call_llm(system, user)


# ===== 智能体4：动态调优 =====
def adjust_plan(current_plan, feedback):
    system = """你是学习计划调优专家，根据用户反馈调整学习路线。
用户反馈中已掌握的知识点要跳过或压缩，薄弱点要增加练习。
输出严格JSON，格式与原计划一致。只返回JSON。"""
    user = f"当前计划：{json.dumps(current_plan, ensure_ascii=False)}\n用户反馈：{feedback}"
    return call_llm(system, user)
