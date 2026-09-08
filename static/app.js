// ========== 全局状态 ==========
let conversations = [];
let currentConvId = null;
let selectedPlanIndex = 0;

const STORAGE_KEY = 'study_planner_conversations';

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    renderConvList();
    checkApiStatus();
    autoResizeTextarea();
});

function autoResizeTextarea() {
    const ta = document.getElementById('userInput');
    ta.addEventListener('input', () => {
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    });
}

// ========== localStorage ==========
function loadConversations() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        conversations = data ? JSON.parse(data) : [];
    } catch (e) {
        conversations = [];
    }
}

function saveConversations() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
        console.error('保存失败', e);
    }
}

function getCurrentConv() {
    return conversations.find(c => c.id === currentConvId);
}

function updateConv(conv) {
    const idx = conversations.findIndex(c => c.id === conv.id);
    if (idx >= 0) conversations[idx] = conv;
    saveConversations();
}

// ========== API状态检查 ==========
async function checkApiStatus() {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.status === 'ok') {
            document.querySelector('.status-dot').classList.add('ok');
            document.getElementById('apiStatusText').textContent = '服务正常';
        }
    } catch (e) {
        document.querySelector('.status-dot').classList.add('error');
        document.getElementById('apiStatusText').textContent = '连接失败';
    }
}

// ========== 对话列表 ==========
function renderConvList() {
    const list = document.getElementById('convList');
    if (conversations.length === 0) {
        list.innerHTML = '<div class="conv-empty">暂无对话，点击上方新建</div>';
        return;
    }
    list.innerHTML = conversations.slice().reverse().map(conv => {
        const title = conv.goal || '未命名对话';
        const active = conv.id === currentConvId ? 'active' : '';
        return `<div class="conv-item ${active}" onclick="selectConversation('${conv.id}')">
            <div class="conv-title">${escapeHtml(title)}</div>
            <div class="conv-time">${conv.created_at || ''}</div>
        </div>`;
    }).join('');
}

function newConversation() {
    const conv = {
        id: 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
        goal: '',
        base: '',
        hours: 0,
        deadline: '',
        preference: [],
        skill_tree: {},
        resources: {},
        plan: {},
        completed_kps: [],
        messages: [{
            role: 'assistant',
            content: '你好！我是你的智能学习伴侣。请告诉我你想学什么，比如「我想在1个月内学会Python数据分析」，我会为你生成个性化的学习计划。'
        }],
        stage: 'collecting',
        created_at: new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    };
    conversations.push(conv);
    currentConvId = conv.id;
    saveConversations();
    renderConvList();
    renderChat();
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('detailPanel').style.display = 'none';
}

function selectConversation(id) {
    currentConvId = id;
    renderConvList();
    renderChat();
    const conv = getCurrentConv();
    if (conv && conv.skill_tree && Object.keys(conv.skill_tree).length > 0) {
        document.getElementById('detailPanel').style.display = 'flex';
        renderAllDetails();
    } else {
        document.getElementById('detailPanel').style.display = 'none';
    }
}

// ========== 聊天渲染 ==========
function renderChat() {
    const conv = getCurrentConv();
    if (!conv) return;

    document.getElementById('chatTitle').textContent = conv.goal || '新对话';
    document.getElementById('chatSubtitle').textContent = conv.created_at ? `创建于 ${conv.created_at}` : '';

    const messagesEl = document.getElementById('messages');
    const welcome = document.getElementById('welcomeScreen');

    if (conv.messages.length <= 1) {
        welcome.style.display = 'block';
        messagesEl.innerHTML = '';
        return;
    }
    welcome.style.display = 'none';

    messagesEl.innerHTML = conv.messages.map(msg => {
        return `<div class="message ${msg.role}">
            <div class="message-bubble">${escapeHtml(msg.content)}</div>
        </div>`;
    }).join('');
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendMessage(role, content) {
    const conv = getCurrentConv();
    if (!conv) return;
    conv.messages.push({ role, content });
    updateConv(conv);
    renderChat();
}

// ========== 发送消息 ==========
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function sendExample(text) {
    document.getElementById('userInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message) return;

    const conv = getCurrentConv();
    if (!conv) {
        newConversation();
    }

    input.value = '';
    input.style.height = 'auto';
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('loadingOverlay').style.display = 'flex';

    try {
        const currentConv = getCurrentConv();
        appendMessage('user', message);

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conv: currentConv, message })
        });

        if (!res.ok) throw new Error('API请求失败');
        const data = await res.json();

        // 用后端返回的更新后的conv替换
        const idx = conversations.findIndex(c => c.id === data.conv.id);
        if (idx >= 0) conversations[idx] = data.conv;
        saveConversations();

        appendMessage('assistant', data.reply);

        // 更新标题
        if (data.conv.goal && !conv.goal) {
            document.getElementById('chatTitle').textContent = data.conv.goal;
        }

        // 显示详情面板
        if (data.conv.skill_tree && Object.keys(data.conv.skill_tree).length > 0) {
            document.getElementById('detailPanel').style.display = 'flex';
            selectedPlanIndex = 0;
            renderAllDetails();
        }

        renderConvList();
    } catch (e) {
        appendMessage('assistant', '抱歉，处理你的消息时出错了：' + e.message + '\n\n请稍后重试，或检查网络连接。');
    } finally {
        document.getElementById('sendBtn').disabled = false;
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// ========== Tab切换 ==========
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
}

// ========== 渲染所有详情 ==========
function renderAllDetails() {
    renderSkillTree();
    renderResources();
    renderPlan();
    renderQuiz();
    renderStats();
}

// ========== 技能树 ==========
function renderSkillTree() {
    const conv = getCurrentConv();
    const el = document.getElementById('tab-skilltree');
    if (!conv || !conv.skill_tree) { el.innerHTML = ''; return; }

    const plans = conv.skill_tree.plans || [];
    if (!plans.length) { el.innerHTML = ''; return; }

    let html = '<div class="plan-selector">';
    plans.forEach((p, i) => {
        html += `<div class="plan-option ${i === selectedPlanIndex ? 'active' : ''}" onclick="selectPlan(${i})">
            <div class="plan-option-name">${escapeHtml(p.plan_name || '方案' + (i+1))}</div>
            <div class="plan-option-desc">${escapeHtml(p.description || '')}</div>
        </div>`;
    });
    html += '</div>';

    const p = plans[selectedPlanIndex];
    const stages = p.stages || [];
    const totalKps = stages.reduce((sum, s) => sum + (s.knowledge_points || []).length, 0);
    const totalDays = stages.reduce((sum, s) => sum + (s.suggested_days || 0), 0);
    const completed = (conv.completed_kps || []).length;
    const pct = totalKps > 0 ? Math.round(completed / totalKps * 100) : 0;

    html += `<div class="metrics-row">
        <div class="metric-card"><div class="metric-value">${stages.length}</div><div class="metric-label">学习阶段</div></div>
        <div class="metric-card"><div class="metric-value">${totalKps}</div><div class="metric-label">知识点</div></div>
        <div class="metric-card"><div class="metric-value">${totalDays}天</div><div class="metric-label">预计周期</div></div>
        <div class="metric-card"><div class="progress-ring" style="--progress:${pct}%"><div class="progress-ring-inner">${pct}%</div></div><div class="metric-label">完成进度</div></div>
    </div>`;

    stages.forEach((stage, i) => {
        html += `<div class="stage-block">
            <div class="stage-header" onclick="toggleStage(this)">
                <span class="stage-name">阶段${i+1}：${escapeHtml(stage.stage_name || '')}</span>
                <span class="stage-meta">约${stage.suggested_days || '?'}天</span>
            </div>
            <div class="stage-body ${i === 0 ? 'open' : ''}">
                <div class="stage-ability">达成能力：${escapeHtml(stage.expected_ability || '')}</div>`;
        (stage.knowledge_points || []).forEach(kp => {
            const name = typeof kp === 'object' ? kp.name : kp;
            const diff = typeof kp === 'object' ? kp.difficulty : '';
            const prereq = typeof kp === 'object' ? (kp.prerequisites || []) : [];
            const hours = typeof kp === 'object' ? kp.hours : '';
            const isCompleted = (conv.completed_kps || []).includes(name);
            const diffClass = diff === '入门' ? 'tag-easy' : (diff === '进阶' ? 'tag-mid' : 'tag-hard');

            html += `<div class="kp-item">
                <input type="checkbox" class="kp-checkbox" ${isCompleted ? 'checked' : ''} onchange="toggleKp('${escapeJs(name)}')">
                <div class="kp-info">
                    <div class="kp-name ${isCompleted ? 'completed' : ''}">${escapeHtml(name)}</div>
                    <div class="kp-meta">
                        ${diff ? `<span class="tag ${diffClass}">${diff}</span>` : ''}
                        ${prereq.length ? `<span>先修：${escapeHtml(prereq.join('、'))}</span>` : ''}
                        ${hours ? `<span>约${hours}小时</span>` : ''}
                    </div>
                </div>
            </div>`;
        });
        html += '</div></div>';
    });

    el.innerHTML = html;
}

function selectPlan(idx) {
    selectedPlanIndex = idx;
    renderSkillTree();
}

function toggleStage(header) {
    header.nextElementSibling.classList.toggle('open');
}

function toggleKp(name) {
    const conv = getCurrentConv();
    if (!conv) return;
    if (!conv.completed_kps) conv.completed_kps = [];
    const idx = conv.completed_kps.indexOf(name);
    if (idx >= 0) {
        conv.completed_kps.splice(idx, 1);
    } else {
        conv.completed_kps.push(name);
    }
    updateConv(conv);
    renderSkillTree();
    renderStats();
}

// ========== 资源推荐 ==========
function renderResources() {
    const conv = getCurrentConv();
    const el = document.getElementById('tab-resources');
    if (!conv || !conv.resources) { el.innerHTML = ''; return; }

    const resources = conv.resources.resources || [];
    if (!resources.length) {
        el.innerHTML = '<div class="quiz-empty">暂无资源推荐</div>';
        return;
    }

    let html = '';
    resources.forEach((item, i) => {
        const kpName = item.knowledge_point || '';
        html += `<div class="resource-block">
            <div class="resource-header" onclick="toggleResource(this)">${escapeHtml(kpName)}</div>
            <div class="resource-body ${i === 0 ? 'open' : ''}">`;

        [['beginner', '入门材料'], ['advanced', '进阶材料'], ['practice', '实战练习']].forEach(([level, label]) => {
            const items = item[level] || [];
            if (items.length) {
                html += `<div class="resource-level">${label}</div>`;
                items.forEach(r => {
                    const name = typeof r === 'object' ? r.name : r;
                    const url = typeof r === 'object' ? r.url : '';
                    const author = typeof r === 'object' ? r.author : '';
                    const source = typeof r === 'object' ? r.source : '';
                    const rtype = typeof r === 'object' ? r.type : '';

                    if (url) {
                        html += `<div class="resource-item">
                            <a href="${url}" target="_blank">${escapeHtml(name)}</a>
                            ${source ? `<span class="tag tag-source">${source}</span>` : ''}
                            ${author ? `<span class="resource-author"> - ${escapeHtml(author)}</span>` : ''}
                        </div>`;
                    } else {
                        const searchUrl = `https://search.bilibili.com/all?keyword=${encodeURIComponent(kpName + ' ' + name)}`;
                        html += `<div class="resource-item">
                            <strong>${escapeHtml(name)}</strong> (${rtype})
                            <a href="${searchUrl}" target="_blank" style="margin-left:8px;">B站搜索</a>
                        </div>`;
                    }
                });
            }
        });
        html += '</div></div>';
    });
    el.innerHTML = html;
}

function toggleResource(header) {
    header.nextElementSibling.classList.toggle('open');
}

// ========== 学习计划 ==========
function renderPlan() {
    const conv = getCurrentConv();
    const el = document.getElementById('tab-plan');
    if (!conv || !conv.plan) { el.innerHTML = ''; return; }

    const plan = conv.plan;
    const goal = conv.goal || '学习计划';
    let html = '';

    if (plan.weekly_plan && plan.weekly_plan.length) {
        html += `<button class="ics-download-btn" onclick="downloadICS()">下载日历文件 (导入手机/电脑日历)</button>
            <div class="ics-hint">下载后双击导入系统日历，含提前30分钟提醒</div>`;
    }

    const reviewNodes = plan.review_nodes || [];
    if (reviewNodes.length) {
        html += '<div class="review-nodes"><div class="review-title">艾宾浩斯复习节点</div>';
        reviewNodes.forEach(node => {
            html += `<div class="review-item">学习后第${node.after_day || ''}天：${escapeHtml(node.content || '')}</div>`;
        });
        html += '</div>';
    }

    (plan.weekly_plan || []).forEach(week => {
        html += `<div class="week-block">
            <div class="week-header" onclick="toggleWeek(this)">第${week.week}周：${escapeHtml(week.theme || '')}</div>
            <div class="week-body">`;
        (week.days || []).forEach(day => {
            html += `<div class="timeline-item">
                <div class="timeline-day">${escapeHtml(day.day || '')} (${day.hours || ''}h · ${escapeHtml(day.type || '')})</div>
                <div class="timeline-task">${escapeHtml(day.task || '')}</div>
            </div>`;
        });
        html += '</div></div>';
    });

    if (!html) html = '<div class="quiz-empty">暂无学习计划</div>';
    el.innerHTML = html;
}

function toggleWeek(header) {
    header.nextElementSibling.classList.toggle('open');
}

async function downloadICS() {
    const conv = getCurrentConv();
    if (!conv || !conv.plan) return;
    try {
        const res = await fetch('/api/ics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan: conv.plan, goal: conv.goal })
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const safeGoal = (conv.goal || 'study').replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);
        a.download = `${safeGoal}_study_plan.ics`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('下载失败：' + e.message);
    }
}

// ========== 测试记录 ==========
function renderQuiz() {
    const conv = getCurrentConv();
    const el = document.getElementById('tab-quiz');
    if (!conv) { el.innerHTML = ''; return; }

    const history = conv.quiz_history || [];
    if (!history.length) {
        el.innerHTML = '<div class="quiz-empty">还没有测试记录<br>在对话框说「考考我」即可开始测试</div>';
        return;
    }

    const scores = history.map(q => q.score);
    const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    const max = Math.max(...scores);

    let html = `<div class="quiz-stats">
        <div class="metric-card"><div class="metric-value">${history.length}</div><div class="metric-label">测试次数</div></div>
        <div class="metric-card"><div class="metric-value">${avg}分</div><div class="metric-label">平均成绩</div></div>
        <div class="metric-card"><div class="metric-value">${max}分</div><div class="metric-label">最高分</div></div>
    </div>`;

    history.slice().reverse().forEach(q => {
        const scoreClass = q.score >= 80 ? 'high' : (q.score >= 60 ? 'mid' : 'low');
        html += `<div class="quiz-item" onclick="toggleQuiz(this)">
            <div class="quiz-item-header">
                <span class="quiz-stage">${escapeHtml(q.stage || '')}</span>
                <span class="quiz-score ${scoreClass}">${q.score}分</span>
            </div>
            <div class="quiz-date">${q.date || ''} · 正确${q.correct}/${q.total}</div>
            <div class="quiz-detail">`;
        (q.wrong || []).forEach(w => {
            html += `<div class="wrong-item">
                <div class="wrong-question">${escapeHtml(w.question)}</div>
                <div class="wrong-answer">你的答案：${escapeHtml(w.your_answer)}</div>
                <div class="correct-answer">正确答案：${escapeHtml(w.correct_answer)}</div>
            </div>`;
        });
        if (!q.wrong || !q.wrong.length) {
            html += '<div style="font-size:12px;color:#10b981;">全部正确！</div>';
        }
        html += '</div></div>';
    });

    el.innerHTML = html;
}

function toggleQuiz(item) {
    item.querySelector('.quiz-detail').classList.toggle('open');
}

// ========== 学习统计 ==========
function renderStats() {
    const conv = getCurrentConv();
    const el = document.getElementById('tab-stats');
    if (!conv) { el.innerHTML = ''; return; }

    const profile = conv.user_profile || {};
    const completed = conv.completed_kps || [];

    let html = `<div class="stats-grid">
        <div class="metric-card"><div class="metric-value">${completed.length}</div><div class="metric-label">已掌握知识点</div></div>
        <div class="metric-card"><div class="metric-value">${profile.total_quizzes || 0}</div><div class="metric-label">测试次数</div></div>
        <div class="metric-card"><div class="metric-value">${profile.avg_score || 0}分</div><div class="metric-label">平均成绩</div></div>
        <div class="metric-card"><div class="metric-value">${conv.hours || 0}h/天</div><div class="metric-label">每日投入</div></div>
    </div>`;

    const weak = profile.weak_points || [];
    if (weak.length) {
        html += '<div class="stats-section"><div class="stats-section-title">需要加强的知识点</div><div class="stats-list">';
        weak.forEach(w => html += `<div class="stats-list-item">· ${escapeHtml(w)}</div>`);
        html += '</div></div>';
    }

    const strong = profile.strong_points || [];
    if (strong.length) {
        html += '<div class="stats-section"><div class="stats-section-title">已掌握扎实的阶段</div><div class="stats-list">';
        strong.forEach(s => html += `<div class="stats-list-item">· ${escapeHtml(s)}</div>`);
        html += '</div></div>';
    }

    html += '<div class="stats-section"><div class="stats-section-title">已掌握知识点</div><div class="stats-list">';
    if (completed.length) {
        completed.forEach(kp => html += `<div class="stats-list-item">· ${escapeHtml(kp)}</div>`);
    } else {
        html += '<div class="stats-list-item" style="color:#94a3b8;">还没有掌握的知识点，去技能树页勾选吧</div>';
    }
    html += '</div></div>';

    html += `<button class="delete-btn" onclick="deleteConversation()">删除此对话</button>`;

    el.innerHTML = html;
}

function deleteConversation() {
    if (!confirm('确定要删除这个对话吗？此操作不可恢复。')) return;
    conversations = conversations.filter(c => c.id !== currentConvId);
    currentConvId = null;
    saveConversations();
    renderConvList();
    document.getElementById('messages').innerHTML = '';
    document.getElementById('welcomeScreen').style.display = 'block';
    document.getElementById('detailPanel').style.display = 'none';
    document.getElementById('chatTitle').textContent = '智能学习伴侣';
    document.getElementById('chatSubtitle').textContent = '输入你的学习目标，AI为你规划';
}

// ========== 工具函数 ==========
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeJs(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}
