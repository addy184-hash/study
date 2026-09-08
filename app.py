"""智能学习伴侣 - Streamlit 前端界面"""
import streamlit as st
import json
from datetime import datetime
from agents import decompose_skill, recommend_resources, generate_plan, adjust_plan
import config

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智能学习伴侣 | AI学习路径规划",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' fill='%232563eb'/%3E%3Cpath d='M30 50 L45 65 L70 35' stroke='white' stroke-width='8' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========== 暗黑模式状态 ==========
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

dark = st.session_state.dark_mode
bg = "#0f172a" if dark else "#f8fafc"
card_bg = "#1e293b" if dark else "#ffffff"
text_color = "#e2e8f0" if dark else "#1e293b"
sub_text = "#94a3b8" if dark else "#64748b"
border = "#334155" if dark else "#e2e8f0"
primary = "#3b82f6"

# ========== 全局样式 ==========
st.markdown(f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
    #stDecoration {{display: none;}}
    .stApp {{
        max-width: 1200px;
        margin: 0 auto;
        background-color: {bg};
        color: {text_color};
    }}
    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }}
    h1 {{
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.3rem !important;
        color: {text_color};
    }}
    .subtitle {{
        color: {sub_text};
        font-size: 0.9rem;
        margin-bottom: 1.2rem;
    }}
    .card {{
        background: {card_bg};
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border: 1px solid {border};
        margin-bottom: 0.8rem;
    }}
    .card-title {{
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.5rem;
        color: {text_color};
    }}
    .stage-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.6rem 1rem;
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }}
    .kp-item {{
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        padding: 0.5rem 0.8rem;
        margin-left: 1rem;
        border-left: 2px solid {primary};
        margin-bottom: 0.3rem;
    }}
    .kp-name {{
        font-weight: 500;
        color: {text_color};
    }}
    .kp-meta {{
        font-size: 0.75rem;
        color: {sub_text};
        margin-top: 0.2rem;
    }}
    .tag {{
        display: inline-block;
        padding: 0.1rem 0.5rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 500;
        margin-right: 0.3rem;
    }}
    .tag-easy {{background: #dcfce7; color: #166534;}}
    .tag-mid {{background: #fef9c3; color: #854d0e;}}
    .tag-hard {{background: #fee2e2; color: #991b1b;}}
    .progress-ring {{
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: conic-gradient({primary} var(--progress), {border} 0);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }}
    .progress-ring-inner {{
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: {card_bg};
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        color: {text_color};
    }}
    .timeline-item {{
        position: relative;
        padding-left: 1.5rem;
        padding-bottom: 0.8rem;
        border-left: 2px solid {border};
    }}
    .timeline-item::before {{
        content: '';
        position: absolute;
        left: -6px;
        top: 0.3rem;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: {primary};
    }}
    .timeline-day {{
        font-weight: 600;
        color: {text_color};
        font-size: 0.9rem;
    }}
    .timeline-task {{
        color: {sub_text};
        font-size: 0.85rem;
        margin-top: 0.2rem;
    }}
    .review-node {{
        background: linear-gradient(135deg, {primary}15, {primary}05);
        border: 1px solid {primary}40;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.5rem;
    }}
    .search-link {{
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        text-decoration: none;
        margin-right: 0.3rem;
        border: 1px solid {border};
        color: {primary};
    }}
    .search-link:hover {{
        background: {primary}15;
    }}
    .metric-card {{
        text-align: center;
        padding: 0.8rem;
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    .metric-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {primary};
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: {sub_text};
        margin-top: 0.2rem;
    }}
    .plan-tab {{
        padding: 0.5rem 1rem;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 500;
        text-align: center;
        border: 1px solid {border};
    }}
    .plan-tab.active {{
        background: {primary};
        color: white;
        border-color: {primary};
    }}
    .history-item {{
        padding: 0.8rem 1rem;
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 8px;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }}
    .history-item:hover {{
        border-color: {primary};
    }}
</style>
""", unsafe_allow_html=True)

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### 设置")
    api_key = st.text_input("DeepSeek API Key", type="password")
    if api_key:
        config.DEEPSEEK_API_KEY = api_key
        st.success("已配置")

    st.markdown("---")
    if st.toggle("暗黑模式", value=dark):
        st.session_state.dark_mode = True
    else:
        st.session_state.dark_mode = False
    if st.button("应用主题", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.caption("没有Key？前往 platform.deepseek.com 注册")

# ========== 标题 ==========
st.title("智能学习伴侣")
st.markdown('<p class="subtitle">输入学习目标，AI为你拆解技能树、匹配资源、排定周计划，动态调整学习节奏</p>', unsafe_allow_html=True)

# ========== 历史记录初始化 ==========
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_plan_idx' not in st.session_state:
    st.session_state.current_plan_idx = None

# ========== Tab切换 ==========
tab1, tab2, tab3, tab4 = st.tabs(["生成计划", "资源推荐", "进度调优", "历史记录"])

# ========== Tab1: 生成计划 ==========
with tab1:
    if 'skill_tree' not in st.session_state:
        with st.expander("使用说明", expanded=True):
            st.markdown("""
            **三步生成专属学习计划**

            1. 填写学情 — 输入学习目标、现有基础、每日可投入时间
            2. AI拆解 — 自动生成两套方案（速成版/扎实版），含先修知识、难度分级
            3. 执行反馈 — 学习后在「进度调优」页反馈，AI自动调整后续计划

            首次使用请在左侧边栏填入 DeepSeek API Key，或由管理员预配置。
            """)

    st.subheader("填写学情")
    col1, col2 = st.columns(2)
    with col1:
        goal = st.text_input("学习目标", placeholder="例如：1个月学会Python数据分析")
        base = st.selectbox("现有基础", ["零基础", "了解基本概念", "有一定实践经验", "比较熟练"])
    with col2:
        hours = st.slider("每日可投入时长（小时）", 0.5, 8.0, 2.0, 0.5)
        deadline = st.text_input("目标完成时间", placeholder="例如：4周后 / 2026-10-01")

    st.multiselect("学习偏好（可选）",
                   ["视频课程", "文档阅读", "实战项目", "理论推导", "刷题练习"],
                   default=["视频课程", "实战项目"])

    if st.button("生成学习路线", type="primary", use_container_width=True):
        if not config.DEEPSEEK_API_KEY:
            st.error("请先在左侧边栏填写 DeepSeek API Key")
        elif not goal:
            st.warning("请填写学习目标")
        else:
            progress = st.progress(0, text="准备中...")
            progress.progress(25, text="正在拆解技能树...")
            skill_tree = decompose_skill(goal, base, hours, deadline)
            if "error" in skill_tree:
                st.error(f"技能拆解失败：{skill_tree['error']}")
                st.stop()
            st.session_state.skill_tree = skill_tree

            progress.progress(50, text="正在匹配学习资源...")
            resources = recommend_resources(skill_tree)
            if "error" in resources:
                st.error(f"资源推荐失败：{resources['error']}")
                st.stop()
            st.session_state.resources = resources

            progress.progress(75, text="正在排定周计划...")
            plan = generate_plan(skill_tree, hours)
            if "error" in plan:
                st.error(f"计划生成失败：{plan['error']}")
                st.stop()
            st.session_state.plan = plan

            # 保存到历史
            record = {
                "goal": goal,
                "base": base,
                "hours": hours,
                "deadline": deadline,
                "skill_tree": skill_tree,
                "resources": resources,
                "plan": plan,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "completed_kps": []
            }
            st.session_state.history.append(record)
            st.session_state.current_plan_idx = len(st.session_state.history) - 1

            progress.progress(100, text="完成")
            st.success("学习路线生成完成！切换标签查看详情")

    # 展示技能树
    if 'skill_tree' in st.session_state:
        st.markdown("---")
        st.subheader("技能树")

        tree = st.session_state.skill_tree
        plans = tree.get('plans', [])

        # 方案切换
        if len(plans) > 1:
            plan_names = [p.get('plan_name', f'方案{i+1}') for i, p in enumerate(plans)]
            cols = st.columns(len(plans))
            if 'selected_plan' not in st.session_state:
                st.session_state.selected_plan = 0
            for i, (col, name) in enumerate(zip(cols, plan_names)):
                if col.button(name, use_container_width=True,
                             type="primary" if st.session_state.selected_plan == i else "secondary"):
                    st.session_state.selected_plan = i

        current_plan = plans[st.session_state.get('selected_plan', 0)] if plans else {}

        # 统计指标
        stages = current_plan.get('stages', [])
        total_kps = sum(len(s.get('knowledge_points', [])) for s in stages)
        total_days = sum(s.get('suggested_days', 0) for s in stages)
        idx = st.session_state.current_plan_idx
        completed = len(st.session_state.history[idx].get('completed_kps', [])) if idx is not None else 0
        progress_pct = int(completed / total_kps * 100) if total_kps > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-card"><div class="metric-value">{len(stages)}</div><div class="metric-label">学习阶段</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="metric-value">{total_kps}</div><div class="metric-label">知识点</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div class="metric-value">{total_days}天</div><div class="metric-label">预计周期</div></div>', unsafe_allow_html=True)
        m4.markdown(f'''<div class="metric-card"><div class="progress-ring" style="--progress:{progress_pct}%"><div class="progress-ring-inner">{progress_pct}%</div></div><div class="metric-label">完成进度</div></div>''', unsafe_allow_html=True)

        st.markdown(f"**当前方案：** {current_plan.get('plan_name','')} — {current_plan.get('description','')}")

        # 技能树展开
        for i, stage in enumerate(stages, 1):
            with st.expander(f"阶段{i}：{stage.get('stage_name','')}  |  约{stage.get('suggested_days','?')}天", expanded=(i==1)):
                st.markdown(f"**达成能力：** {stage.get('expected_ability','')}")
                st.markdown("**核心知识点：**")
                for kp in stage.get('knowledge_points', []):
                    kp_name = kp.get('name', '') if isinstance(kp, dict) else str(kp)
                    diff = kp.get('difficulty', '') if isinstance(kp, dict) else ''
                    prereq = kp.get('prerequisites', []) if isinstance(kp, dict) else []
                    kp_hours = kp.get('hours', '') if isinstance(kp, dict) else ''

                    diff_class = 'tag-easy' if diff == '入门' else ('tag-mid' if diff == '进阶' else 'tag-hard')
                    checked = kp_name in (st.session_state.history[idx].get('completed_kps', []) if idx is not None else [])

                    # 构造meta文本，避免HTML内条件表达式导致解析异常
                    meta_parts = [f'<span class="tag {diff_class}">{diff}</span>']
                    if prereq:
                        meta_parts.append(f"先修：{'、'.join(prereq)}")
                    if kp_hours:
                        meta_parts.append(f"约{kp_hours}小时")
                    meta_text = " · ".join(meta_parts[1:]) if len(meta_parts) > 1 else ""
                    meta_html = meta_parts[0] + (f" · {meta_text}" if meta_text else "")

                    c1, c2 = st.columns([0.85, 0.15])
                    with c1:
                        st.markdown(
                            f'<div class="kp-item"><div class="kp-name">{kp_name}</div>'
                            f'<div class="kp-meta">{meta_html}</div></div>',
                            unsafe_allow_html=True
                        )
                    with c2:
                        if st.checkbox("已掌握", value=checked, key=f"kp_{i}_{kp_name}", label_visibility="collapsed"):
                            if idx is not None and kp_name not in st.session_state.history[idx]['completed_kps']:
                                st.session_state.history[idx]['completed_kps'].append(kp_name)
                                st.rerun()
                        else:
                            if idx is not None and kp_name in st.session_state.history[idx]['completed_kps']:
                                st.session_state.history[idx]['completed_kps'].remove(kp_name)
                                st.rerun()

        # 导出
        st.markdown("---")
        if st.button("导出学习计划 (Markdown)"):
            md = f"# {goal} - 学习计划\n\n"
            md += f"- 方案：{current_plan.get('plan_name','')}\n"
            md += f"- 现有基础：{base}\n"
            md += f"- 每日投入：{hours}小时\n"
            md += f"- 目标时间：{deadline}\n\n"
            for i, stage in enumerate(stages, 1):
                md += f"## 阶段{i}：{stage.get('stage_name','')}\n"
                md += f"- 达成能力：{stage.get('expected_ability','')}\n"
                md += f"- 预计天数：{stage.get('suggested_days','')}\n"
                md += "- 知识点：\n"
                for kp in stage.get('knowledge_points', []):
                    name = kp.get('name', '') if isinstance(kp, dict) else str(kp)
                    md += f"  - [{kp.get('difficulty','')}] {name}\n"
                md += "\n"
            st.download_button("下载 plan.md", md, file_name="学习计划.md", mime="text/markdown")

# ========== Tab2: 资源推荐 ==========
with tab2:
    if 'resources' not in st.session_state:
        st.info("请先在「生成计划」标签页生成学习路线")
    else:
        st.subheader("匹配的学习资源")
        res = st.session_state.resources
        for item in res.get('resources', []):
            kp_name = item.get('knowledge_point', '')
            with st.expander(kp_name, expanded=False):
                for level, label in [('beginner', '入门材料'), ('advanced', '进阶材料'), ('practice', '实战练习')]:
                    items = item.get(level, [])
                    if items:
                        st.markdown(f"**{label}**")
                        for r in items:
                            name = r.get('name', '') if isinstance(r, dict) else str(r)
                            rtype = r.get('type', '') if isinstance(r, dict) else ''
                            search_bilibili = f"https://search.bilibili.com/all?keyword={kp_name}+{name}"
                            search_baidu = f"https://www.baidu.com/s?wd={kp_name}+{name}"
                            st.markdown(f'''
                            <div style="padding:0.4rem 0;">
                                <span style="font-weight:500;">{name}</span>
                                <span class="tag" style="background:{primary}15;color:{primary};">{rtype}</span>
                                <a href="{search_bilibili}" target="_blank" class="search-link">B站搜索</a>
                                <a href="{search_baidu}" target="_blank" class="search-link">百度搜索</a>
                            </div>''', unsafe_allow_html=True)

# ========== Tab3: 进度调优 ==========
with tab3:
    if 'plan' not in st.session_state:
        st.info("请先生成学习计划")
    else:
        st.subheader("当前周计划")
        plan = st.session_state.plan

        # 艾宾浩斯复习节点
        review_nodes = plan.get('review_nodes', [])
        if review_nodes:
            st.markdown("**艾宾浩斯复习节点**")
            for node in review_nodes:
                st.markdown(f'''
                <div class="review-node">
                    <span style="font-weight:600;">学习后第{node.get('after_day','')}天</span>
                    <span style="color:{sub_text};margin-left:0.5rem;">{node.get('content','')}</span>
                </div>''', unsafe_allow_html=True)

        # 时间线展示
        for week in plan.get('weekly_plan', []):
            with st.expander(f"第{week['week']}周：{week.get('theme','')}", expanded=True):
                for day in week.get('days', []):
                    d = day.get('day', '')
                    task = day.get('task', '')
                    h = day.get('hours', '')
                    t = day.get('type', '')
                    st.markdown(f'''
                    <div class="timeline-item">
                        <div class="timeline-day">{d}  ({h}h · {t})</div>
                        <div class="timeline-task">{task}</div>
                    </div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("反馈调优")
        feedback = st.text_area("描述学习进度和薄弱点",
                               placeholder="例如：第一周Python基础已掌握，但Pandas不熟练，需要更多练习...",
                               height=100)
        if st.button("重新调整计划", type="primary"):
            if not feedback:
                st.warning("请先填写反馈")
            else:
                with st.spinner("AI正在重新规划..."):
                    new_plan = adjust_plan(plan, feedback)
                    if "error" in new_plan:
                        st.error(f"调优失败：{new_plan['error']}")
                    else:
                        st.session_state.plan = new_plan
                        idx = st.session_state.current_plan_idx
                        if idx is not None:
                            st.session_state.history[idx]['plan'] = new_plan
                        st.success("计划已更新！上方周计划已刷新")

# ========== Tab4: 历史记录 ==========
with tab4:
    st.subheader("历史学习计划")
    if not st.session_state.history:
        st.info("暂无历史记录，生成计划后会自动保存")
    else:
        for i, record in enumerate(reversed(st.session_state.history)):
            real_idx = len(st.session_state.history) - 1 - i
            with st.expander(f"{record['goal']}  |  {record['created_at']}"):
                st.markdown(f"**基础：** {record['base']}  |  **每日：** {record['hours']}小时  |  **截止：** {record['deadline']}")
                plans = record['skill_tree'].get('plans', [])
                if plans:
                    st.markdown(f"**方案：** {plans[0].get('plan_name','')}")
                    stages = plans[0].get('stages', [])
                    st.markdown(f"**阶段数：** {len(stages)}  |  **知识点：** {sum(len(s.get('knowledge_points',[])) for s in stages)}")
                completed = len(record.get('completed_kps', []))
                total = sum(len(s.get('knowledge_points',[])) for s in (plans[0].get('stages',[]) if plans else []))
                st.markdown(f"**完成进度：** {completed}/{total} 知识点")
                if st.button("加载此计划", key=f"load_{real_idx}", use_container_width=True):
                    st.session_state.skill_tree = record['skill_tree']
                    st.session_state.resources = record['resources']
                    st.session_state.plan = record['plan']
                    st.session_state.current_plan_idx = real_idx
                    st.success("计划已加载，切换标签查看")
                    st.rerun()

# ========== 底部 ==========
st.markdown("---")
st.caption("智能学习伴侣 · 基于DeepSeek大模型 · 数据仅在本地浏览器会话中保存")
