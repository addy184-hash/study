"""智能学习伴侣 - Streamlit 前端界面"""
import streamlit as st
import json
from agents import decompose_skill, recommend_resources, generate_plan, adjust_plan
import config

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智能学习伴侣 | AI学习路径规划",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========== 隐藏默认UI元素 ==========
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    #stDecoration {display: none;}
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.2rem !important;
    }
    .subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .step-badge {
        display: inline-block;
        background: #2563eb;
        color: white;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        text-align: center;
        line-height: 24px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ========== 侧边栏：API Key ==========
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("DeepSeek API Key", type="password",
                           help="在 platform.deepseek.com 申请")
    if api_key:
        config.DEEPSEEK_API_KEY = api_key
        st.success("已配置")
    st.markdown("---")
    st.caption("没有Key？前往 platform.deepseek.com 注册，新用户送额度")

# ========== 标题区 ==========
st.title("🎯 智能学习伴侣")
st.markdown('<p class="subtitle">输入学习目标，AI为你拆解技能树、匹配资源、排定周计划，动态调整学习节奏</p>', unsafe_allow_html=True)

# ========== Tab切换 ==========
tab1, tab2, tab3 = st.tabs(["📋 生成计划", "📚 资源推荐", "🔄 进度调优"])

# ========== Tab1: 生成计划 ==========
with tab1:
    # 首次访问显示使用说明
    if 'skill_tree' not in st.session_state:
        with st.expander("📖 使用说明（点击展开）", expanded=True):
            st.markdown("""
            **三步生成你的专属学习计划：**

            1. **填写学情** — 输入学习目标、现有基础、每日可投入时间
            2. **AI拆解** — 系统自动拆解技能树、匹配学习资源、排定周计划
            3. **执行反馈** — 学习后在「进度调优」页反馈，AI自动调整后续计划

            > 💡 首次使用请在左侧边栏填入 DeepSeek API Key，或由管理员预配置。
            """)

    st.subheader("填写你的学情")

    col1, col2 = st.columns(2)
    with col1:
        goal = st.text_input("学习目标", placeholder="例如：1个月学会Python数据分析")
        base = st.selectbox("现有基础", ["零基础", "了解基本概念", "有一定实践经验", "比较熟练"])
    with col2:
        hours = st.slider("每日可投入时长", 0.5, 8.0, 2.0, 0.5)
        deadline = st.text_input("目标完成时间", placeholder="例如：4周后 / 2026-10-01")

    st.multiselect("学习偏好（可选）",
                   ["视频课程", "文档阅读", "实战项目", "理论推导", "刷题练习"],
                   default=["视频课程", "实战项目"])

    if st.button("🚀 生成我的学习路线", type="primary", use_container_width=True):
        if not config.DEEPSEEK_API_KEY:
            st.error("⚠️ 请先在左侧边栏填写 DeepSeek API Key")
        elif not goal:
            st.warning("请填写学习目标")
        else:
            # 分步加载进度
            progress = st.progress(0, text="准备中...")

            progress.progress(20, text="🔧 正在拆解技能树...")
            skill_tree = decompose_skill(goal, base, hours, deadline)
            if "error" in skill_tree:
                st.error(f"❌ 技能拆解失败：{skill_tree['error']}")
                st.stop()
            st.session_state.skill_tree = skill_tree

            progress.progress(50, text="📚 正在匹配学习资源...")
            resources = recommend_resources(skill_tree)
            if "error" in resources:
                st.error(f"❌ 资源推荐失败：{resources['error']}")
                st.stop()
            st.session_state.resources = resources

            progress.progress(80, text="📅 正在排定周计划...")
            plan = generate_plan(skill_tree, hours)
            if "error" in plan:
                st.error(f"❌ 计划生成失败：{plan['error']}")
                st.stop()
            st.session_state.plan = plan

            progress.progress(100, text="✅ 完成！")
            st.success("🎉 学习路线生成完成！切换上方标签查看详情")

    # 展示技能树
    if 'skill_tree' in st.session_state:
        st.markdown("---")
        st.subheader("🌳 你的技能树")
        tree = st.session_state.skill_tree
        stages = tree.get('stages', [])
        total_weeks = tree.get('total_weeks', len(stages))

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("学习阶段", f"{len(stages)} 个")
        col_b.metric("预计周期", f"{total_weeks} 周")
        col_c.metric("每日投入", f"{hours} 小时")

        for i, stage in enumerate(stages, 1):
            with st.expander(f"**阶段{i}：{stage.get('stage_name','')}**  ·  约{stage.get('suggested_days','?')}天", expanded=True):
                st.markdown(f"**🎯 达成能力：** {stage.get('expected_ability','')}")
                st.markdown("**📌 核心知识点：**")
                for kp in stage.get('knowledge_points', []):
                    st.markdown(f"- {kp}")

        # 导出按钮
        st.markdown("---")
        if st.button("📥 导出学习计划为 Markdown"):
            md = f"# {goal} - 学习计划\n\n"
            md += f"- **现有基础：** {base}\n"
            md += f"- **每日投入：** {hours}小时\n"
            md += f"- **目标时间：** {deadline}\n\n"
            md += "## 技能树\n\n"
            for i, stage in enumerate(stages, 1):
                md += f"### 阶段{i}：{stage.get('stage_name','')}\n"
                md += f"- **达成能力：** {stage.get('expected_ability','')}\n"
                md += f"- **预计天数：** {stage.get('suggested_days','')}\n"
                md += "- **知识点：**\n"
                for kp in stage.get('knowledge_points', []):
                    md += f"  - {kp}\n"
                md += "\n"
            st.download_button("⬇️ 下载 plan.md", md, file_name="学习计划.md", mime="text/markdown")

# ========== Tab2: 资源推荐 ==========
with tab2:
    if 'resources' not in st.session_state:
        st.info("👈 请先在「生成计划」标签页生成学习路线")
    else:
        st.subheader("📚 匹配的学习资源")
        res = st.session_state.resources
        for item in res.get('resources', []):
            with st.expander(f"📌 {item['knowledge_point']}", expanded=False):
                if item.get('beginner'):
                    st.markdown("**🟢 入门材料**")
                    for r in item['beginner']:
                        st.markdown(f"- {r}")
                if item.get('advanced'):
                    st.markdown("**🔵 进阶材料**")
                    for r in item['advanced']:
                        st.markdown(f"- {r}")
                if item.get('practice'):
                    st.markdown("**✏️ 实战练习**")
                    for r in item['practice']:
                        st.markdown(f"- {r}")

# ========== Tab3: 进度调优 ==========
with tab3:
    if 'plan' not in st.session_state:
        st.info("👈 请先生成学习计划")
    else:
        st.subheader("📅 当前周计划")
        plan = st.session_state.plan
        for week in plan.get('weekly_plan', []):
            with st.expander(f"**第{week['week']}周：{week.get('theme','')}**", expanded=True):
                for day in week.get('days', []):
                    st.markdown(
                        f"- **{day['day']}** （{day.get('hours','')}h · {day.get('type','')}）：{day['task']}"
                    )

        st.markdown("---")
        st.subheader("🔄 反馈调优")
        feedback = st.text_area("描述你的学习进度和薄弱点",
                               placeholder="例如：第一周Python基础已掌握，但Pandas不熟练，需要更多练习...",
                               height=100)
        if st.button("✨ 重新调整计划", type="primary"):
            if not feedback:
                st.warning("请先填写反馈")
            else:
                with st.spinner("AI正在重新规划..."):
                    new_plan = adjust_plan(plan, feedback)
                    if "error" in new_plan:
                        st.error(f"❌ 调优失败：{new_plan['error']}")
                    else:
                        st.session_state.plan = new_plan
                        st.success("✅ 计划已更新！上方周计划已刷新")

# ========== 底部 ==========
st.markdown("---")
st.caption("💡 智能学习伴侣 · 基于DeepSeek大模型 · 数据仅在本次会话中使用")
