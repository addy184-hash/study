"""智能学习伴侣 - 对话式界面"""
import streamlit as st
import json
import uuid
from datetime import datetime
from agents import process_chat_message, generate_ics
from streamlit_js_eval import streamlit_js_eval
import config

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智能学习伴侣 | AI学习路径规划",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' fill='%232563eb'/%3E%3Cpath d='M30 50 L45 65 L70 35' stroke='white' stroke-width='8' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== localStorage 工具 ==========
def load_conversations_from_storage():
    """从localStorage读取数据（streamlit-js-eval异步，第一次返回None）"""
    data = streamlit_js_eval(js_expressions="localStorage.getItem('study_chat_b64')", key="load_storage")
    if data and isinstance(data, str):
        try:
            import base64
            decoded = base64.b64decode(data).decode('utf-8')
            return json.loads(decoded)
        except:
            return []
    return None  # None表示JS还没执行完，需要等下一次渲染


def save_conversations(convs):
    """保存到localStorage"""
    try:
        import base64
        data = json.dumps(convs, ensure_ascii=False)
        encoded = base64.b64encode(data.encode('utf-8')).decode('ascii')
        streamlit_js_eval(js_expressions=f"localStorage.setItem('study_chat_b64', '{encoded}')", key="save_storage")
    except:
        pass


# ========== 初始化状态 ==========
if 'conversations' not in st.session_state:
    st.session_state.conversations = []
if 'current_conv_id' not in st.session_state:
    st.session_state.current_conv_id = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# 从localStorage加载数据（处理streamlit-js-eval异步时序）
if not st.session_state.data_loaded:
    loaded = load_conversations_from_storage()
    if loaded is not None:
        st.session_state.conversations = loaded
        st.session_state.data_loaded = True
        st.rerun()
    # 如果loaded是None，说明JS还没执行完，等下一次渲染自动重试

# ========== 主题配色（固定浅色） ==========
bg = "#f1f5f9"
card_bg = "#ffffff"
text_color = "#1e293b"
sub_text = "#64748b"
border = "#e2e8f0"
primary = "#3b82f6"
user_bubble = "#dbeafe"
assistant_bubble = "#f8fafc"

# ========== 全局样式 ==========
st.markdown(f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
    #stDecoration {{display: none;}}
    .stApp {{background-color: {bg}; color: {text_color};}}
    .main .block-container {{padding-top: 1rem; padding-bottom: 1rem; max-width: 100%;}}
    section[data-testid="stSidebar"] {{background-color: {card_bg}; border-right: 1px solid {border}; width: 280px !important;}}
    .chat-message {{padding: 1rem; margin-bottom: 0.8rem; border-radius: 12px; max-width: 85%;}}
    .chat-user {{background-color: {user_bubble}; color: #1e3a8a; margin-left: auto; text-align: right;}}
    .chat-assistant {{background-color: {assistant_bubble}; color: {text_color}; border: 1px solid {border};}}
    .conv-item {{padding: 0.7rem 0.8rem; border-radius: 8px; cursor: pointer; margin-bottom: 0.3rem; border: 1px solid transparent;}}
    .conv-item:hover {{background-color: {bg};}}
    .conv-item.active {{background-color: {primary}15; border-color: {primary};}}
    .conv-title {{font-weight: 600; font-size: 0.9rem; color: {text_color}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}}
    .conv-time {{font-size: 0.75rem; color: {sub_text}; margin-top: 0.2rem;}}
    .new-chat-btn {{background-color: {primary}; color: white; padding: 0.6rem; border-radius: 8px; text-align: center; cursor: pointer; font-weight: 500; margin-bottom: 1rem;}}
    .new-chat-btn:hover {{opacity: 0.9;}}
    .detail-panel {{background-color: {card_bg}; border: 1px solid {border}; border-radius: 10px; padding: 1rem; margin-top: 1rem;}}
    .kp-item {{padding: 0.4rem 0.8rem; margin-left: 0.5rem; border-left: 2px solid {primary}; margin-bottom: 0.3rem;}}
    .tag {{display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 500; margin-right: 0.3rem;}}
    .tag-easy {{background: #dcfce7; color: #166534;}}
    .tag-mid {{background: #fef9c3; color: #854d0e;}}
    .tag-hard {{background: #fee2e2; color: #991b1b;}}
    .progress-ring {{width: 70px; height: 70px; border-radius: 50%; background: conic-gradient({primary} var(--progress), {border} 0); display: flex; align-items: center; justify-content: center; margin: 0 auto;}}
    .progress-ring-inner {{width: 52px; height: 52px; border-radius: 50%; background: {card_bg}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1rem; color: {text_color};}}
    .metric-card {{text-align: center; padding: 0.6rem; background: {bg}; border-radius: 8px;}}
    .metric-value {{font-size: 1.3rem; font-weight: 700; color: {primary};}}
    .metric-label {{font-size: 0.7rem; color: {sub_text};}}
    .timeline-item {{position: relative; padding-left: 1.2rem; padding-bottom: 0.6rem; border-left: 2px solid {border};}}
    .timeline-item::before {{content: ''; position: absolute; left: -5px; top: 0.3rem; width: 8px; height: 8px; border-radius: 50%; background: {primary};}}
    div.stButton > button:first-child {{border-radius: 8px;}}
    .search-link {{display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; text-decoration: none; margin-right: 0.3rem; border: 1px solid {border}; color: {primary};}}
</style>
""", unsafe_allow_html=True)

# ========== 侧边栏：对话列表 ==========
with st.sidebar:
    st.markdown("### 智能学习伴侣")
    st.caption("AI驱动的个性化学习规划")

    if st.button("+ 新建对话", use_container_width=True, type="primary"):
        new_conv = {
            "id": str(uuid.uuid4()),
            "goal": "",
            "base": "",
            "hours": 0,
            "deadline": "",
            "preference": [],
            "skill_tree": {},
            "resources": {},
            "plan": {},
            "completed_kps": [],
            "messages": [{"role": "assistant", "content": "你好！我是你的智能学习伴侣。请告诉我你想学什么，比如「我想在1个月内学会Python数据分析」，我会为你生成个性化的学习计划。"}],
            "stage": "collecting",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        st.session_state.conversations.append(new_conv)
        st.session_state.current_conv_id = new_conv["id"]
        save_conversations(st.session_state.conversations)
        st.rerun()

    st.markdown("---")
    st.markdown("**历史对话**")

    if not st.session_state.conversations:
        st.caption("暂无对话，点击上方新建")
    else:
        for conv in reversed(st.session_state.conversations):
            title = conv.get("goal", "新对话") if conv.get("goal") else "未命名对话"
            is_active = conv["id"] == st.session_state.current_conv_id
            if st.button(f"{title}\n{conv['created_at']}", key=f"conv_{conv['id']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"):
                st.session_state.current_conv_id = conv["id"]
                st.rerun()

    st.markdown("---")

    api_key = st.text_input("DeepSeek API Key", type="password", key="api_key_input")
    if api_key:
        config.DEEPSEEK_API_KEY = api_key
        st.success("API Key已配置")
    elif config.DEEPSEEK_API_KEY:
        st.success("API Key已从环境变量加载")
    else:
        st.warning("未配置API Key，无法使用AI功能")
        st.caption("在上方填写Key，或在Render环境变量中设置DEEPSEEK_API_KEY")

# ========== 获取当前对话 ==========
current_conv = None
if st.session_state.current_conv_id:
    for c in st.session_state.conversations:
        if c["id"] == st.session_state.current_conv_id:
            current_conv = c
            break

if not current_conv:
    st.info("👈 点击左侧「新建对话」开始你的学习规划")
    st.stop()

# ========== 主区域：聊天界面 ==========
st.markdown(f"#### {current_conv.get('goal', '新对话') if current_conv.get('goal') else '新对话'}")
st.caption(f"创建于 {current_conv['created_at']}")

# 显示聊天消息
for msg in current_conv.get("messages", []):
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-message chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message chat-assistant">{msg["content"].replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

# 输入框
user_input = st.chat_input("输入你的学习目标或进度反馈...")
if user_input:
    if not config.DEEPSEEK_API_KEY:
        st.error("请先在左侧边栏填写 DeepSeek API Key")
    else:
        current_conv["messages"].append({"role": "user", "content": user_input})
        with st.spinner("AI正在思考..."):
            reply = process_chat_message(current_conv, user_input)
        current_conv["messages"].append({"role": "assistant", "content": reply})
        save_conversations(st.session_state.conversations)
        st.rerun()

# ========== 详情面板：技能树/资源/计划 ==========
if current_conv.get("skill_tree"):
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["技能树", "资源推荐", "学习计划", "测试记录", "学习统计"])

    with tab1:
        tree = current_conv["skill_tree"]
        plans = tree.get("plans", [])
        if plans:
            plan_names = [p.get("plan_name", f"方案{i+1}") for i, p in enumerate(plans)]
            selected = st.radio("选择方案", plan_names, horizontal=True, key="plan_select")
            idx = plan_names.index(selected) if selected in plan_names else 0
            p = plans[idx]
            stages = p.get("stages", [])
            total_kps = sum(len(s.get("knowledge_points", [])) for s in stages)
            total_days = sum(s.get("suggested_days", 0) for s in stages)
            completed = len(current_conv.get("completed_kps", []))
            pct = int(completed / total_kps * 100) if total_kps > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{len(stages)}</div><div class="metric-label">学习阶段</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{total_kps}</div><div class="metric-label">知识点</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-value">{total_days}天</div><div class="metric-label">预计周期</div></div>', unsafe_allow_html=True)
            m4.markdown(f'''<div class="metric-card"><div class="progress-ring" style="--progress:{pct}%"><div class="progress-ring-inner">{pct}%</div></div><div class="metric-label">完成进度</div></div>''', unsafe_allow_html=True)

            st.markdown(f"**{p.get('plan_name','')}** — {p.get('description','')}")
            for i, stage in enumerate(stages, 1):
                with st.expander(f"阶段{i}：{stage.get('stage_name','')}  |  约{stage.get('suggested_days','?')}天", expanded=(i==1)):
                    st.markdown(f"**达成能力：** {stage.get('expected_ability','')}")
                    for kp in stage.get("knowledge_points", []):
                        kp_name = kp.get("name", "") if isinstance(kp, dict) else str(kp)
                        diff = kp.get("difficulty", "") if isinstance(kp, dict) else ""
                        prereq = kp.get("prerequisites", []) if isinstance(kp, dict) else []
                        kp_hours = kp.get("hours", "") if isinstance(kp, dict) else ""
                        diff_class = 'tag-easy' if diff == "入门" else ('tag-mid' if diff == "进阶" else "tag-hard")
                        checked = kp_name in current_conv.get("completed_kps", [])
                        meta_parts = [f'<span class="tag {diff_class}">{diff}</span>']
                        if prereq:
                            meta_parts.append(f"先修：{'、'.join(prereq)}")
                        if kp_hours:
                            meta_parts.append(f"约{kp_hours}小时")
                        c1, c2 = st.columns([0.85, 0.15])
                        c1.markdown(f'<div class="kp-item"><div style="font-weight:500;">{kp_name}</div><div style="font-size:0.75rem;color:{sub_text};margin-top:0.2rem;">{" · ".join(meta_parts[1:]) if len(meta_parts)>1 else ""}</div></div>', unsafe_allow_html=True)
                        if c2.checkbox("已掌握", value=checked, key=f"kp_{current_conv['id']}_{i}_{kp_name}", label_visibility="collapsed"):
                            if kp_name not in current_conv["completed_kps"]:
                                current_conv["completed_kps"].append(kp_name)
                                save_conversations(st.session_state.conversations)
                                st.rerun()
                        else:
                            if kp_name in current_conv["completed_kps"]:
                                current_conv["completed_kps"].remove(kp_name)
                                save_conversations(st.session_state.conversations)
                                st.rerun()

    with tab2:
        res = current_conv.get("resources", {})
        for item in res.get("resources", []):
            kp_name = item.get("knowledge_point", "")
            with st.expander(kp_name, expanded=False):
                for level, label in [("beginner", "入门材料"), ("advanced", "进阶材料"), ("practice", "实战练习")]:
                    items = item.get(level, [])
                    if items:
                        st.markdown(f"**{label}**")
                        for r in items:
                            name = r.get("name", "") if isinstance(r, dict) else str(r)
                            rtype = r.get("type", "") if isinstance(r, dict) else ""
                            url = r.get("url", "") if isinstance(r, dict) else ""
                            author = r.get("author", "") if isinstance(r, dict) else ""
                            if url:
                                # 真实链接，可直接点击，显示来源标签
                                source = r.get("source", "")
                                source_tag = f" <span class='tag tag-mid'>{source}</span>" if source else ""
                                author_info = f" - {author}" if author else ""
                                st.markdown(f'- [{name}]({url}){source_tag}{author_info}', unsafe_allow_html=True)
                            else:
                                st.markdown(f'- **{name}** ({rtype})  [B站搜索](https://search.bilibili.com/all?keyword={kp_name} {name}) · [百度搜索](https://www.baidu.com/s?wd={kp_name} {name})')

    with tab3:
        plan = current_conv.get("plan", {})
        goal = current_conv.get("goal", "学习计划")

        # ICS下载按钮
        if plan.get("weekly_plan"):
            ics_content = generate_ics(plan, goal)
            st.download_button(
                "下载日历文件 (导入手机/电脑日历)",
                data=ics_content,
                file_name=f"{goal}_学习计划.ics",
                mime="text/calendar",
                use_container_width=True
            )
            st.caption("下载后双击即可导入系统日历，支持iPhone/安卓/Windows/Mac，含提前30分钟提醒")

        review_nodes = plan.get("review_nodes", [])
        if review_nodes:
            st.markdown("**艾宾浩斯复习节点**")
            for node in review_nodes:
                st.info(f"学习后第{node.get('after_day','')}天：{node.get('content','')}")
        for week in plan.get("weekly_plan", []):
            with st.expander(f"第{week['week']}周：{week.get('theme','')}", expanded=True):
                for day in week.get("days", []):
                    st.markdown(f'<div class="timeline-item"><div style="font-weight:600;font-size:0.9rem;">{day.get("day","")} ({day.get("hours","")}h · {day.get("type","")})</div><div style="color:{sub_text};font-size:0.85rem;margin-top:0.2rem;">{day.get("task","")}</div></div>', unsafe_allow_html=True)

    with tab4:
        st.markdown("**测试记录**")
        quiz_history = current_conv.get("quiz_history", [])
        if not quiz_history:
            st.info("还没有测试记录，在对话框说「考考我」即可开始测试")
        else:
            scores = [q["score"] for q in quiz_history]
            avg_score = int(sum(scores) / len(scores))
            m1, m2, m3 = st.columns(3)
            m1.markdown(f'<div class="metric-card"><div class="metric-value">{len(quiz_history)}</div><div class="metric-label">测试次数</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-value">{avg_score}分</div><div class="metric-label">平均成绩</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-value">{max(scores)}分</div><div class="metric-label">最高分</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            for q in reversed(quiz_history):
                with st.expander(f"{q['stage']}  |  {q['date']}  |  {q['score']}分"):
                    st.markdown(f"正确：{q['correct']}/{q['total']}")
                    if q.get("wrong"):
                        st.markdown("**错题：**")
                        for w in q["wrong"]:
                            st.markdown(f"- {w['question']}")
                            st.markdown(f"  正确答案：{w['correct_answer']}")

    with tab5:
        st.markdown("**学习统计**")
        profile = current_conv.get("user_profile", {})
        completed = current_conv.get("completed_kps", [])

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-card"><div class="metric-value">{len(completed)}</div><div class="metric-label">已掌握知识点</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="metric-value">{profile.get("total_quizzes", 0)}</div><div class="metric-label">测试次数</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div class="metric-value">{profile.get("avg_score", 0)}分</div><div class="metric-label">平均成绩</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-card"><div class="metric-value">{current_conv.get("hours", 0)}h/天</div><div class="metric-label">每日投入</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        weak = profile.get("weak_points", [])
        strong = profile.get("strong_points", [])
        if weak:
            st.markdown("**需要加强的知识点：**")
            for w in weak:
                st.markdown(f"- {w}")
        if strong:
            st.markdown("**已掌握扎实的阶段：**")
            for s in strong:
                st.markdown(f"- {s}")

        st.markdown("---")
        st.markdown("**已掌握知识点：**")
        if completed:
            for kp in completed:
                st.markdown(f"- {kp}")
        else:
            st.caption("还没有掌握的知识点，去技能树页勾选吧")

        st.markdown("---")
        if st.button("删除此对话", use_container_width=True):
            st.session_state.conversations = [c for c in st.session_state.conversations if c["id"] != current_conv["id"]]
            st.session_state.current_conv_id = None
            save_conversations(st.session_state.conversations)
            st.rerun()

st.markdown("---")
st.caption("智能学习伴侣 · 对话数据保存在浏览器本地，刷新不丢失")
