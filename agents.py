"""智能学习伴侣 - LangGraph多智能体核心模块"""
import json
import re
from datetime import datetime, timedelta
from typing import TypedDict, List, Dict, Any
from openai import OpenAI
from langgraph.graph import StateGraph, END
import config

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ========== LLM 基础调用 ==========
def _client():
    return OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict:
    try:
        if not config.DEEPSEEK_API_KEY:
            return {"error": "未配置DeepSeek API Key，请在左侧边栏填写，或在Render环境变量中设置DEEPSEEK_API_KEY"}
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
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return {"error": "API Key认证失败，请检查DeepSeek API Key是否正确"}
        elif "404" in error_msg:
            return {"error": "API地址或模型名称错误，请检查配置"}
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            return {"error": "API调用频率超限或余额不足，请稍后再试或检查账户余额"}
        return {"error": error_msg}


def call_llm_text(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """非JSON格式的LLM调用，使用推理模型(deepseek-reasoner)，回答质量更高"""
    try:
        if not config.DEEPSEEK_API_KEY:
            return "[警告] 未配置DeepSeek API Key，请在左侧边栏填写，或在Render环境变量中设置DEEPSEEK_API_KEY。"
        resp = _client().chat.completions.create(
            model=config.DEEPSEEK_REASONER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return "[警告] API Key认证失败，请检查DeepSeek API Key是否正确。"
        elif "404" in error_msg:
            return "[警告] API地址或模型名称错误，请检查配置。"
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            return "[警告] API调用频率超限或余额不足，请稍后再试或检查账户余额。"
        return f"回答时出错：{error_msg}"


# ========== 工具1：多源搜索工具（Researcher Agent使用） ==========
def search_bilibili(keyword: str, limit: int = 3) -> list:
    """调用B站搜索API，返回真实视频链接，不需要API Key"""
    if not HAS_REQUESTS:
        return []
    try:
        url = "https://api.bilibili.com/x/web-interface/search/type"
        params = {"search_type": "video", "keyword": keyword, "page": 1}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        data = resp.json()
        results = []
        for item in data.get("data", {}).get("result", [])[:limit]:
            title = re.sub(r'<[^>]+>', '', item.get("title", ""))
            bvid = item.get("bvid", "")
            results.append({
                "name": title,
                "type": "视频",
                "url": f"https://www.bilibili.com/video/{bvid}",
                "author": item.get("author", ""),
                "source": "B站"
            })
        return results
    except:
        return []


def search_zhihu(keyword: str, limit: int = 3) -> list:
    """知乎搜索 - 返回知乎搜索结果页链接（知乎API需认证，用站内搜索链接）"""
    encoded = requests.utils.quote(keyword) if HAS_REQUESTS else keyword
    return [{
        "name": f"知乎：{keyword} 相关回答",
        "type": "文章",
        "url": f"https://www.zhihu.com/search?type=content&q={encoded}",
        "author": "知乎社区",
        "source": "知乎"
    }]


def search_official_docs(keyword: str) -> list:
    """智能匹配官方文档 - 根据关键词判断技术栈，返回对应官方文档搜索链接"""
    kw = keyword.lower()
    doc_map = [
        (["python", "pandas", "numpy", "django", "flask", "scrapy", "requests"],
         "Python官方文档", f"https://docs.python.org/3/search.html?q={keyword}"),
        (["javascript", "js", "html", "css", "web", "前端", "dom", "ajax"],
         "MDN Web文档", f"https://developer.mozilla.org/zh-CN/search?q={keyword}"),
        (["react", "hooks", "redux", "nextjs"],
         "React官方文档", f"https://react.dev/search?q={keyword}"),
        (["vue", "vuex", "pinia", "nuxt"],
         "Vue官方文档", f"https://cn.vuejs.org/search/?q={keyword}"),
        (["java", "spring", "maven", "jvm"],
         "Java官方文档", f"https://docs.oracle.com/en/java/javase/17/docs/api/index.html"),
        (["mysql", "sql", "数据库", "redis", "mongodb"],
         "MySQL官方文档", f"https://dev.mysql.com/doc/search/?q={keyword}"),
        (["linux", "shell", "bash", "docker", "nginx"],
         "Linux/Docker文档", f"https://docs.docker.com/search/?q={keyword}"),
        (["算法", "数据结构", "leetcode", "刷题"],
         "LeetCode题解", f"https://leetcode.cn/search/?q={keyword}"),
        (["git", "github", "版本控制"],
         "Git官方文档", f"https://git-scm.com/search/results?search={keyword}"),
        (["机器学习", "深度学习", "pytorch", "tensorflow", "ai", "神经网络"],
         "PyTorch官方文档", f"https://pytorch.org/docs/stable/search.html?q={keyword}"),
    ]

    for keywords, doc_name, url in doc_map:
        if any(k in kw for k in keywords):
            return [{
                "name": f"{doc_name}：{keyword}",
                "type": "官方文档",
                "url": url,
                "author": doc_name,
                "source": "官方文档"
            }]
    # 通用：Google搜索官方文档
    encoded = requests.utils.quote(f"{keyword} 官方文档") if HAS_REQUESTS else keyword
    return [{
        "name": f"搜索官方文档：{keyword}",
        "type": "官方文档",
        "url": f"https://www.google.com/search?q={encoded}",
        "author": "Google",
        "source": "官方文档"
    }]


def search_github(keyword: str) -> list:
    """GitHub搜索 - 返回相关项目搜索链接"""
    encoded = requests.utils.quote(keyword) if HAS_REQUESTS else keyword
    return [{
        "name": f"GitHub：{keyword} 相关项目",
        "type": "开源项目",
        "url": f"https://github.com/search?q={keyword}&type=repositories",
        "author": "GitHub",
        "source": "GitHub"
    }]


def multi_source_search(kp_name: str, preference: list = None) -> dict:
    """多源搜索：整合B站+知乎+官方文档+GitHub，为知识点返回真实资源"""
    beginner = []
    advanced = []
    practice = []

    # B站：入门教程
    bv_beginner = search_bilibili(f"{kp_name} 教程 入门", 2)
    beginner.extend(bv_beginner)

    # B站：进阶实战
    bv_advanced = search_bilibili(f"{kp_name} 实战 进阶", 2)
    advanced.extend(bv_advanced)

    # 知乎：深度文章
    zhihu = search_zhihu(f"{kp_name} 原理 详解")
    advanced.extend(zhihu)

    # 官方文档
    docs = search_official_docs(kp_name)
    beginner.extend(docs)

    # GitHub：实战项目
    github = search_github(f"{kp_name} example")
    practice.extend(github)

    # B站：练习题
    bv_practice = search_bilibili(f"{kp_name} 练习题 面试题", 2)
    practice.extend(bv_practice)

    # 去重
    def dedup(lst):
        seen = set()
        result = []
        for item in lst:
            if item["url"] not in seen:
                seen.add(item["url"])
                result.append(item)
        return result

    return {
        "beginner": dedup(beginner)[:5],
        "advanced": dedup(advanced)[:5],
        "practice": dedup(practice)[:5]
    }


# ========== 工具2：ICS日历导出（Coach Agent使用） ==========
def generate_ics(plan: dict, goal: str, start_date: str = None) -> str:
    """从学习计划生成ICS日历文件，可导入手机/电脑日历"""
    if not start_date:
        start_date = datetime.now().strftime("%Y%m%d")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Study Planner//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    base_date = datetime.strptime(start_date, "%Y%m%d")

    for week in plan.get("weekly_plan", []):
        week_num = week.get("week", 1)
        for day in week.get("days", []):
            day_name = day.get("day", "")
            task = day.get("task", "")
            hours = float(day.get("hours", 1.5))
            task_type = day.get("type", "学习")

            # 计算日期
            weekday = day_map.get(day_name, 0)
            event_date = base_date + timedelta(weeks=week_num - 1, days=weekday)
            date_str = event_date.strftime("%Y%m%d")

            # 事件时间：默认上午9点开始
            start_hour = 9
            end_hour = start_hour + int(hours)
            dtstart = f"{date_str}T{start_hour:02d}0000"
            dtend = f"{date_str}T{end_hour:02d}0000"

            uid = f"study-{week_num}-{day_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}@studyplanner"

            ics_lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:[{task_type}] {goal} - {task}",
                f"DESCRIPTION:学习计划自动生成\\n目标：{goal}\\n类型：{task_type}\\n预计：{hours}小时",
                "BEGIN:VALARM",
                "TRIGGER:-PT30M",
                "ACTION:DISPLAY",
                "DESCRIPTION:该学习了！",
                "END:VALARM",
                "END:VEVENT",
            ])

    # 复习节点
    for node in plan.get("review_nodes", []):
        after_day = node.get("after_day", 1)
        content = node.get("content", "复习")
        review_date = base_date + timedelta(days=after_day)
        date_str = review_date.strftime("%Y%m%d")
        uid = f"review-{after_day}-{datetime.now().strftime('%Y%m%d%H%M%S')}@studyplanner"
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
            f"DTSTART:{date_str}T190000",
            f"DTEND:{date_str}T200000",
            f"SUMMARY:[复习] {content}",
            f"DESCRIPTION:艾宾浩斯复习节点\\n相关阶段：{node.get('related_stage','')}",
            "END:VEVENT",
        ])

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)


# ========== 工具3：测试题系统 ==========
def generate_quiz(stage: dict, num: int = 5) -> dict:
    """生成阶段测试题（3选择2简答），含答案和解析"""
    system = """你是出题专家，为学习阶段生成测试题，含答案和详细解析。
输出严格JSON：
{"questions":[{"type":"选择","question":"题目","options":["A选项","B选项","C选项","D选项"],"answer":"A","explanation":"解析"},{"type":"简答","question":"题目","answer":"参考答案","explanation":"评分要点"}]}
只返回JSON。"""
    user = f"为以下阶段出{num}道题（3选择2简答）：\n{json.dumps(stage, ensure_ascii=False)}"
    result = call_llm(system, user)
    return result if "error" not in result else {"questions": []}


def grade_quiz(questions: list, user_answers: list) -> dict:
    """批改测试题，返回得分、错题、详细反馈"""
    correct = 0
    wrong = []
    details = []

    for i, (q, ua) in enumerate(zip(questions, user_answers)):
        q_type = q.get("type", "")
        correct_answer = q.get("answer", "")
        if q_type == "选择":
            is_correct = (ua or "").strip().upper() == correct_answer.strip().upper()
        else:
            # 简答题：用LLM判断
            is_correct = _grade_short_answer(q.get("question", ""), ua, correct_answer)
        if is_correct:
            correct += 1
        else:
            wrong.append({
                "question": q.get("question", ""),
                "your_answer": ua or "未作答",
                "correct_answer": correct_answer,
                "explanation": q.get("explanation", "")
            })
        details.append({
            "question": q.get("question", ""),
            "your_answer": ua or "未作答",
            "correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": q.get("explanation", "")
        })

    score = int(correct / len(questions) * 100) if questions else 0
    return {
        "score": score,
        "correct": correct,
        "total": len(questions),
        "wrong": wrong,
        "details": details
    }


def _grade_short_answer(question: str, user_answer: str, reference: str) -> bool:
    """用LLM判断简答题是否正确"""
    if not user_answer or len(user_answer) < 5:
        return False
    system = """判断学生回答是否正确，只返回JSON：{"correct": true/false}"""
    user = f"题目：{question}\n参考答案：{reference}\n学生回答：{user_answer}"
    result = call_llm(system, user)
    return result.get("correct", False)


def _parse_quiz_answers(message: str, num: int) -> list:
    """解析用户的测试题答案，支持格式：1.A 2.回答 3.B 或 A B C 或 1A2B3C"""
    answers = [""] * num
    # 格式1：1.A 2.xxx 3.B
    matches = re.findall(r'(\d+)[\.\、\s]*([A-Da-d]|[^\s]+)', message)
    if matches:
        for m in matches:
            idx = int(m[0]) - 1
            if 0 <= idx < num:
                answers[idx] = m[1].strip()
    else:
        # 格式2：A B C D（纯字母）
        letters = re.findall(r'[A-Da-d]', message)
        for i, letter in enumerate(letters[:num]):
            answers[i] = letter.upper()
    return answers


def _plan_stats(plan: dict) -> dict:
    """提取计划的统计信息，用于对比新旧计划"""
    weekly = plan.get("weekly_plan", [])
    total_weeks = len(weekly)
    total_tasks = sum(len(w.get("days", [])) for w in weekly)
    total_hours = sum(d.get("hours", 0) for w in weekly for d in w.get("days", []))
    review_count = len(plan.get("review_nodes", []))
    return {
        "weeks": total_weeks,
        "tasks": total_tasks,
        "hours": round(total_hours, 1),
        "reviews": review_count
    }


def _compare_plans(old_plan: dict, new_plan: dict, feedback: str) -> str:
    """对比新旧计划，生成具体的变化说明"""
    old = _plan_stats(old_plan)
    new = _plan_stats(new_plan)

    changes = []

    # 周数变化
    if new["weeks"] != old["weeks"]:
        if new["weeks"] < old["weeks"]:
            changes.append(f"总周期从 {old['weeks']} 周压缩到 {new['weeks']} 周")
        else:
            changes.append(f"总周期从 {old['weeks']} 周延长到 {new['weeks']} 周")

    # 任务数变化
    if new["tasks"] != old["tasks"]:
        if new["tasks"] < old["tasks"]:
            changes.append(f"学习任务从 {old['tasks']} 个精简到 {new['tasks']} 个")
        else:
            changes.append(f"学习任务从 {old['tasks']} 个增加到 {new['tasks']} 个")

    # 学时变化
    if new["hours"] != old["hours"]:
        if new["hours"] < old["hours"]:
            changes.append(f"总学时从 {old['hours']} 小时减少到 {new['hours']} 小时")
        else:
            changes.append(f"总学时从 {old['hours']} 小时增加到 {new['hours']} 小时")

    # 复习节点变化
    if new["reviews"] != old["reviews"]:
        if new["reviews"] > old["reviews"]:
            changes.append(f"复习节点从 {old['reviews']} 个增加到 {new['reviews']} 个")
        else:
            changes.append(f"复习节点从 {old['reviews']} 个调整为 {new['reviews']} 个")

    if not changes:
        return "计划内容已根据你的反馈优化，任务安排更加合理。"

    # 根据反馈类型生成总结
    if any(k in feedback for k in ["缩短", "压缩", "快点", "加快", "速成"]):
        summary = "已压缩学习周期，知识点密度增加，建议每天多投入一些时间。"
    elif any(k in feedback for k in ["延长", "放慢", "轻松", "慢点"]):
        summary = "已延长学习周期，每个知识点的学习时间更充裕。"
    elif any(k in feedback for k in ["难", "不懂", "薄弱", "加强"]):
        summary = "已加强薄弱环节的练习和复习，建议多花时间在这些知识点上。"
    elif any(k in feedback for k in ["简单", "掌握", "学会", "跳过"]):
        summary = "已精简已掌握的内容，把时间留给更有挑战的知识点。"
    else:
        summary = "已根据你的反馈优化了学习安排。"

    return "具体变化：\n" + "\n".join(f"- {c}" for c in changes) + f"\n\n{summary}"


# ========== 工具4：用户记忆系统 ==========
def update_user_profile(profile: dict, conv: dict, quiz_result: dict = None) -> dict:
    """更新用户画像：薄弱点、学习习惯、平均成绩"""
    if not profile:
        profile = {
            "total_quizzes": 0,
            "avg_score": 0,
            "weak_points": [],
            "strong_points": [],
            "total_study_hours": 0,
            "completed_kps": [],
            "preference": []
        }

    # 更新已掌握知识点
    completed = conv.get("completed_kps", [])
    profile["completed_kps"] = list(set(profile.get("completed_kps", []) + completed))

    # 更新学习时长
    profile["total_study_hours"] = profile.get("total_study_hours", 0) + conv.get("hours", 0)

    # 更新测试成绩
    if quiz_result:
        profile["total_quizzes"] = profile.get("total_quizzes", 0) + 1
        old_avg = profile.get("avg_score", 0)
        n = profile["total_quizzes"]
        profile["avg_score"] = int((old_avg * (n - 1) + quiz_result["score"]) / n)

        # 错题加入薄弱点
        for w in quiz_result.get("wrong", []):
            # 从题目中提取知识点关键词
            kp = _extract_kp_from_question(w["question"])
            if kp and kp not in profile.get("weak_points", []):
                profile["weak_points"].append(kp)

        # 全对加入强项
        if quiz_result["score"] == 100:
            stage_name = conv.get("current_stage", "")
            if stage_name and stage_name not in profile.get("strong_points", []):
                profile["strong_points"].append(stage_name)

    return profile


def _extract_kp_from_question(question: str) -> str:
    """从题目中提取知识点关键词"""
    system = """从题目中提取核心知识点关键词，只返回JSON：{"keyword": "知识点"}"""
    result = call_llm(system, question)
    return result.get("keyword", "")


# ========== 多智能体共享状态 ==========
class LearningState(TypedDict):
    """三智能体共享的全局状态（ReAct模式）"""
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
    thought: str                     # Supervisor的思考过程
    next_action: str                 # Supervisor决定的下一步：planner/researcher/coach/finish
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
    职责：先用LLM生成资源框架，再调用B站搜索工具补全真实链接
    读取：skill_tree, preference
    写入：resources（含真实URL）
    """
    pref_text = "、".join(state.get("preference", [])) or "无特殊偏好"
    skill_tree = state.get("skill_tree", {})

    # 第一步：LLM生成资源框架（资源名称和类型）
    system = f"""你是【学习资源研究员】，为每个知识点匹配资源名称和类型。
用户偏好：{pref_text}，请优先推荐符合偏好的资源类型。
资源类型：视频/文档/书籍/实战/刷题。
输出严格JSON：
{{"resources":[{{"knowledge_point":"知识点","beginner":[{{"name":"资源名","type":"视频"}}],"advanced":[{{"name":"资源名","type":"文档"}}],"practice":[{{"name":"练习名","type":"实战"}}]}}]}}
只返回JSON。"""
    user = f"为以下技能树匹配资源：\n{json.dumps(skill_tree, ensure_ascii=False)}\n用户偏好：{pref_text}"
    framework = call_llm(system, user)

    if "error" in framework:
        return {"error": f"资源推荐智能体出错：{framework['error']}"}

    # 第二步：调用多源搜索工具，为每个知识点补全真实链接
    resources_list = framework.get("resources", [])
    for item in resources_list:
        kp_name = item.get("knowledge_point", "")
        # 多源搜索：B站+知乎+官方文档+GitHub
        search_results = multi_source_search(kp_name, state.get("preference", []))

        # 合并搜索结果到对应级别
        for level in ["beginner", "advanced", "practice"]:
            existing = item.get(level, [])
            for r in search_results.get(level, []):
                if not any(e.get("url") == r["url"] for e in existing if e.get("url")):
                    existing.append(r)
            item[level] = existing[:6]

    return {"resources": {"resources": resources_list}}


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


# ========== 智能体0：Supervisor调度智能体 (ReAct核心) ==========
def supervisor_agent(state: LearningState) -> Dict[str, Any]:
    """
    角色：学习规划总监
    职责：观察当前状态，自主决策下一步调用哪个Agent，或结束任务
    决策逻辑：
    - 没有skill_tree → 调用planner
    - 有skill_tree但没有resources → 调用researcher
    - 有skill_tree和resources但没有plan → 调用coach
    - 有feedback需要调优 → 调用coach
    - 全部完成 → finish
    """
    has_skill_tree = bool(state.get("skill_tree"))
    has_resources = bool(state.get("resources"))
    has_plan = bool(state.get("plan"))
    has_feedback = bool(state.get("feedback"))

    # ReAct思考过程
    thought = f"当前状态：技能树={'有' if has_skill_tree else '无'}，资源={'有' if has_resources else '无'}，计划={'有' if has_plan else '无'}，反馈={'有' if has_feedback else '无'}"

    if has_feedback:
        thought += " → 用户有反馈，需要调优计划"
        next_action = "coach"
    elif not has_skill_tree:
        thought += " → 需要先拆解技能树"
        next_action = "planner"
    elif not has_resources:
        thought += " → 技能树已有，需要匹配资源"
        next_action = "researcher"
    elif not has_plan:
        thought += " → 资源已有，需要生成计划"
        next_action = "coach"
    else:
        thought += " → 全部完成，结束任务"
        next_action = "finish"

    return {"thought": thought, "next_action": next_action}


def route_supervisor(state: LearningState) -> str:
    """根据Supervisor的决策路由"""
    action = state.get("next_action", "finish")
    if action == "planner":
        return "planner"
    elif action == "researcher":
        return "researcher"
    elif action == "coach":
        return "coach"
    else:
        return END


# ========== 构建 LangGraph 图（ReAct自主决策模式） ==========
def build_graph():
    """
    构建ReAct模式的多智能体工作流图
    Supervisor → Planner/Researcher/Coach → Supervisor → ... → END
    Supervisor每次观察状态，自主决定下一步，实现自主决策循环
    """
    graph = StateGraph(LearningState)

    # 添加四个节点：Supervisor + 三个工作Agent
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("coach", coach_agent)

    # 入口：Supervisor
    graph.set_entry_point("supervisor")

    # Supervisor决策路由
    graph.add_conditional_edges("supervisor", route_supervisor, {
        "planner": "planner",
        "researcher": "researcher",
        "coach": "coach",
        END: END
    })

    # 工作Agent执行完回到Supervisor，继续决策
    graph.add_edge("planner", "supervisor")
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("coach", "supervisor")

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
    """完整流程：Supervisor自主调度 Planner → Researcher → Coach"""
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
        "thought": "",
        "next_action": "",
        "error": ""
    }
    result = get_graph().invoke(state)
    return result


def adjust_learning_plan(state: LearningState, feedback: str) -> dict:
    """仅调优：Supervisor检测到feedback后自动调用Coach"""
    state["feedback"] = feedback
    state["thought"] = ""
    state["next_action"] = ""
    result = get_graph().invoke(state)
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
    阶段感知：collecting阶段优先识别学习目标，避免误判
    """
    msg = message.strip()

    # ===== 收集学情阶段：优先识别学习目标 =====
    if stage == "collecting":
        # 明确的学习目标关键词
        goal_keywords = ["学", "速成", "学会", "掌握", "入门", "精通", "备考", "考研", "考级",
                         "学习", "想学", "要学", "准备学", "开始学", "自学", "培训"]
        # 时间相关词（配合学习目标）
        time_keywords = ["天", "周", "月", "个月", "年", "小时", "之内", "以内"]

        is_goal = any(k in msg for k in goal_keywords)
        has_time = any(k in msg for k in time_keywords)

        # 如果包含学习目标词，直接判定为补充信息
        if is_goal:
            return {"action": "clarify", "summary": "用户提出学习目标"}

        # 用默认设置
        if "默认" in msg and ("设置" in msg or "就行" in msg or "开始" in msg):
            return {"action": "use_default"}

        # 打招呼
        if msg in ["你好", "hi", "hello", "在吗", "在么", "嗨"]:
            return {"action": "greeting"}

        # 收集阶段不触发motivation（除非非常明确的消极情绪）
        if any(k in msg for k in ["想放弃", "学不下去", "太难了不想学"]):
            return {"action": "motivation"}

        # 其他情况都当作补充信息
        return {"action": "clarify", "summary": "用户补充学情信息"}

    # ===== 学习中阶段：完整意图识别 =====
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

    # 取消测试
    if any(k in msg for k in ["取消测试", "不答了", "放弃测试", "重新出题", "换个题"]):
        return {"action": "cancel_quiz"}

    # 情绪/鼓励（必须是明确的消极情绪）
    if any(k in msg for k in ["太难了", "学不会", "想放弃", "好累", "焦虑", "压力大", "没信心", "学不下去", "不想学了"]):
        return {"action": "motivation"}

    # 感谢/结束
    if any(k in msg for k in ["谢谢", "感谢", "辛苦了", "拜拜", "再见"]):
        return {"action": "thanks"}

    # LLM深度判断
    system = """你是对话意图识别专家，判断用户消息的意图。
当前阶段：learning（用户已经有学习计划，正在学习中）
可选意图：
- adjust: 用户汇报学习进度、说某个知识点掌握了/没掌握、遇到困难、要求调整计划
- answer: 用户问知识性问题、概念解释、学习方法
- motivation: 用户表达消极情绪、需要鼓励
只返回JSON：{"action":"adjust/answer/motivation","summary":"一句话摘要"}"""
    result = call_llm(system, f"用户消息：{msg}")
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

        if action == "cancel_quiz":
            conv["quiz_active"] = False
            conv["quiz_questions"] = []
            return "已取消当前测试。你可以说「考考我」重新开始，或者指定阶段，比如「考考我气体」。"

        if action == "quiz":
            # 检查是否正在答题中
            if conv.get("quiz_active"):
                return "你正在答题中，请先回答当前题目。\n回答格式：1.A 2.你的回答 3.C ...\n\n如果想取消，说「取消测试」。"

            # 生成测试题
            skill_tree = conv.get("skill_tree", {})
            plans = skill_tree.get("plans", [])
            if not plans:
                return "还没有学习计划，请先告诉我你的学习目标。"

            stages = plans[0].get("stages", [])
            if not stages:
                return "技能树中没有阶段，请重新生成学习计划。"

            # 从用户消息中提取阶段关键词，尝试匹配指定阶段
            target_stage = None
            user_msg = user_message
            # 移除"考考我""测试题""出题"等词，剩下的可能是阶段名
            keyword = re.sub(r'(考考我|测试题|测试|出题|练习|做题|测验|阶段|章|的)', '', user_msg).strip()

            if keyword and len(keyword) > 1:
                # 尝试匹配包含关键词的阶段
                for stage in stages:
                    stage_name = stage.get("stage_name", "")
                    if keyword in stage_name or stage_name in keyword:
                        target_stage = stage
                        conv["current_stage"] = stage_name
                        break

            # 如果没匹配到指定阶段，找第一个未完全掌握的阶段
            if not target_stage:
                for stage in stages:
                    kps = stage.get("knowledge_points", [])
                    stage_kps = [kp.get("name", "") if isinstance(kp, dict) else str(kp) for kp in kps]
                    if stage_kps and not all(k in conv.get("completed_kps", []) for k in stage_kps):
                        target_stage = stage
                        conv["current_stage"] = stage.get("stage_name", "")
                        break

            if not target_stage:
                return "所有阶段都已掌握！你可以说「重新生成计划」开始新的学习，或者去「学习统计」查看你的成绩。"

            # 调用大模型生成测试题
            quiz = generate_quiz(target_stage, 5)
            if "error" in quiz:
                return f"生成测试题时出错：{quiz['error']}\n\n可能原因：API Key错误、余额不足、或网络问题。请检查左侧边栏的API Key配置。"

            questions = quiz.get("questions", [])
            if not questions:
                return "生成测试题失败，大模型没有返回题目。请稍后重试，或者说「取消测试」。"

            conv["quiz_active"] = True
            conv["quiz_questions"] = questions
            conv["quiz_answers"] = [""] * len(questions)

            stage_name = target_stage.get("stage_name", "")
            reply = f"为你准备了「{stage_name}」阶段的测试题（共{len(questions)}题）：\n\n"
            for i, q in enumerate(questions, 1):
                q_type = q.get("type", "")
                reply += f"{i}. [{q_type}] {q.get('question', '')}\n"
                if q.get("options"):
                    for j, opt in enumerate(q["options"]):
                        letter = chr(65 + j)
                        reply += f"   {letter}. {opt}\n"
                reply += "\n"
            reply += "请按顺序回答，格式：1.A 2.你的回答 3.C ...\n回答后我会批改并记录成绩。\n\n想取消测试说「取消测试」。"
            return reply

        # 检查是否正在答题中（用户输入的是答案）
        if conv.get("quiz_active") and conv.get("quiz_questions"):
            questions = conv["quiz_questions"]
            # 解析用户答案
            user_answers = _parse_quiz_answers(user_message, len(questions))
            if any(user_answers):
                # 批改
                result = grade_quiz(questions, user_answers)
                conv["quiz_active"] = False
                conv["quiz_result"] = result
                conv["quiz_questions"] = []

                # 记录到测试历史
                if "quiz_history" not in conv:
                    conv["quiz_history"] = []
                conv["quiz_history"].append({
                    "stage": conv.get("current_stage", ""),
                    "score": result["score"],
                    "correct": result["correct"],
                    "total": result["total"],
                    "wrong": result["wrong"],
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

                # 更新用户画像
                profile = conv.get("user_profile", {})
                conv["user_profile"] = update_user_profile(profile, conv, result)

                # 生成回复
                reply = f"测试完成！得分：{result['score']}分（{result['correct']}/{result['total']}正确）\n\n"
                if result["score"] >= 80:
                    reply += "表现优秀！这个阶段掌握得很好，可以继续学习下一阶段。\n\n"
                elif result["score"] >= 60:
                    reply += "还不错，但有一些知识点需要加强。\n\n"
                else:
                    reply += "这个阶段还需要多复习，建议重新学习相关知识点。\n\n"

                if result["wrong"]:
                    reply += "错题回顾：\n"
                    for i, w in enumerate(result["wrong"], 1):
                        reply += f"{i}. {w['question']}\n"
                        reply += f"   你的答案：{w['your_answer']}\n"
                        reply += f"   正确答案：{w['correct_answer']}\n"
                        reply += f"   解析：{w['explanation']}\n\n"

                reply += "成绩已记录，可以在下方「学习统计」查看历史成绩。"
                return reply
            else:
                return "没有识别到答案，请按格式回答：1.A 2.回答内容 3.B ..."

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

            # 保存旧计划用于对比
            old_plan = conv.get("plan", {})

            # 调用教练智能体调整计划
            state: LearningState = {
                "goal": conv.get("goal", ""),
                "base": conv.get("base", ""),
                "hours": conv.get("hours", 2),
                "deadline": conv.get("deadline", ""),
                "preference": conv.get("preference", []),
                "skill_tree": conv.get("skill_tree", {}),
                "resources": conv.get("resources", {}),
                "plan": old_plan,
                "completed_kps": completed,
                "feedback": user_message,
                "thought": "",
                "next_action": "",
                "error": ""
            }
            result = adjust_learning_plan(state, user_message)
            if result.get("error"):
                return f"调整计划时出错：{result['error']}"

            new_plan = result.get("plan", old_plan)
            conv["plan"] = new_plan

            # 对比新旧计划，生成变化说明
            change_desc = _compare_plans(old_plan, new_plan, user_message)

            prefix = ""
            if newly_completed:
                prefix = f"已记录你掌握了：{'、'.join(newly_completed)}\n\n"

            return f"{prefix}已根据你的反馈调整了学习计划！\n\n{change_desc}\n\n下方可查看更新后的周计划。"

        if action == "answer":
            # 普通问答，使用推理模型，结合学习上下文给出高质量回答
            goal = conv.get("goal", "")
            base = conv.get("base", "")
            completed = conv.get("completed_kps", [])
            weak = conv.get("user_profile", {}).get("weak_points", [])

            system2 = f"""你是一位资深的学习导师和技术专家，正在辅导用户学习「{goal}」。

用户画像：
- 当前基础：{base}
- 已掌握知识点：{', '.join(completed) if completed else '暂无'}
- 薄弱环节：{', '.join(weak) if weak else '暂无'}

回答要求：
1. 结合用户的学习进度和基础，给出针对性的解释，不要太简单也不要太深入
2. 先给结论，再展开解释，结构清晰
3. 涉及代码时给出可运行的示例，并加注释
4. 涉及概念时用类比帮助理解
5. 如果用户的问题与当前学习内容相关，联系已学知识点
6. 回答末尾可以给出1-2个延伸学习建议
7. 语气友好、鼓励，像一位耐心的私教
8. 不要使用emoji，用简洁专业的语言"""

            return call_llm_text(system2, user_message)

    return "我在听，请告诉我你的学习目标或进度。"
