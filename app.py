import streamlit as st
import json
from agents import decompose_skill, recommend_resources, generate_plan, adjust_plan

st.set_page_config(page_title="智能学习伴侣", page_icon="📚", layout="wide")

st.title("📚 智能学习伴侣 — 个性化学习路径规划师")
st.caption("输入你的学习目标，AI为你拆解技能树、匹配资源、排定周计划")

# 侧边栏：API Key 输入
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("DeepSeek API Key", type="password", 
                           help="在 platform.deepseek.com 申请")
    if api_key:
        import config
        config.DEEPSEEK_API_KEY = api_key
        st.success("API Key 已设置")
    st.markdown("---")
    st.markdown("**没有Key？**")
    st.markdown("前往 [platform.deepseek.com](https://platform.deepseek.com) 注册，新用户送额度")

# Tab 切换
tab1, tab2, tab3 = st.tabs(["🎯 生成学习计划", "📖 查看资源推荐", "🔄 进度反馈调优"])

# ========== Tab1: 生成计划 ==========
with tab1:
    st.subheader("第一步：填写你的学情")
    
    col1, col2 = st.columns(2)
    with col1:
        goal = st.text_input("学习目标", placeholder="例如：1个月学会Python数据分析")
        base = st.selectbox("现有基础", ["零基础", "了解基本概念", "有一定实践经验", "比较熟练"])
    with col2:
        hours = st.slider("每日可投入时长（小时）", 0.5, 8.0, 2.0, 0.5)
        deadline = st.text_input("目标完成时间", placeholder="例如：4周后 / 2026-10-01")
    
    preference = st.multiselect("学习偏好", ["视频课程", "文档阅读", "实战项目", "理论推导", "刷题练习"],
                               default=["视频课程", "实战项目"])
    
    if st.button("🚀 生成我的学习路线", type="primary", use_container_width=True):
        if not api_key:
            st.error("请先在左侧填写 DeepSeek API Key")
        elif not goal:
            st.warning("请填写学习目标")
        else:
            with st.spinner("AI正在拆解技能树..."):
                # 1. 技能拆解
                skill_tree = decompose_skill(goal, base, hours, deadline)
                st.session_state.skill_tree = skill_tree
                
                # 2. 资源推荐
                resources = recommend_resources(skill_tree)
                st.session_state.resources = resources
                
                # 3. 计划生成
                plan = generate_plan(skill_tree, hours)
                st.session_state.plan = plan
                
                st.success("✅ 学习路线生成完成！切换上方标签查看详情")
    
    # 展示技能树
    if 'skill_tree' in st.session_state:
        st.markdown("---")
        st.subheader("🌳 你的技能树")
        tree = st.session_state.skill_tree
        if 'stages' in tree:
            for i, stage in enumerate(tree['stages'], 1):
                with st.expander(f"阶段{i}：{stage.get('stage_name','')}（约{stage.get('suggested_days','?')}天）", expanded=True):
                    st.markdown(f"**🎯 达成能力：** {stage.get('expected_ability','')}")
                    st.markdown("**📌 知识点：**")
                    for kp in stage.get('knowledge_points', []):
                        st.markdown(f"- {kp}")

# ========== Tab2: 资源推荐 ==========
with tab2:
    if 'resources' not in st.session_state:
        st.info("请先在「生成学习计划」标签页生成路线")
    else:
        st.subheader("📖 匹配的学习资源")
        res = st.session_state.resources
        if 'resources' in res:
            for item in res['resources']:
                with st.expander(f"📌 {item['knowledge_point']}", expanded=False):
                    if item.get('beginner'):
                        st.markdown("**🟢 入门材料：**")
                        for r in item['beginner']:
                            st.markdown(f"- {r}")
                    if item.get('advanced'):
                        st.markdown("**🔵 进阶材料：**")
                        for r in item['advanced']:
                            st.markdown(f"- {r}")
                    if item.get('practice'):
                        st.markdown("**✏️ 实战练习：**")
                        for r in item['practice']:
                            st.markdown(f"- {r}")

# ========== Tab3: 进度反馈 ==========
with tab3:
    if 'plan' not in st.session_state:
        st.info("请先生成学习计划")
    else:
        st.subheader("📅 当前周计划")
        plan = st.session_state.plan
        if 'weekly_plan' in plan:
            for week in plan['weekly_plan']:
                with st.expander(f"第{week['week']}周：{week.get('theme','')}", expanded=True):
                    for day in week.get('days', []):
                        st.markdown(f"**{day['day']}**（{day.get('hours','')}h，{day.get('type','')}）：{day['task']}")
        
        st.markdown("---")
        st.subheader("🔄 反馈调优")
        feedback = st.text_area("描述你的学习进度和薄弱点", 
                               placeholder="例如：第一周的Python基础已经掌握，但Pandas部分不太熟练，需要更多练习...",
                               height=100)
        if st.button("✨ 重新调整计划", type="primary"):
            if feedback:
                with st.spinner("AI正在重新规划..."):
                    new_plan = adjust_plan(plan, feedback)
                    st.session_state.plan = new_plan
                    st.success("✅ 计划已更新！上方周计划已刷新")
            else:
                st.warning("请先填写反馈")

# 底部
st.markdown("---")
st.caption("💡 提示：API Key仅在本次会话中使用，不会上传存储。数据通过DeepSeek国内API处理。")
