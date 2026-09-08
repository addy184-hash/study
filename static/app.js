// ========== 全局状态 ==========
let conversations = [];
let currentConvId = null;
let selectedPlanIndex = 0;

const STORAGE_KEY = 'study_planner_conversations';

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    renderConvList();
    renderChat();
    // 检测是否为手机端
    const isMobile = window.innerWidth <= 1024;
    if (isMobile) {
        document.getElementById('mobileTabbar').style.display = 'flex';
    }
    // 如果当前对话有技能树，显示详情面板（桌面端）
    const conv = getCurrentConv();
    if (conv && conv.skill_tree && Object.keys(conv.skill_tree).length > 0) {
        if (!isMobile) {
            const detailPanel = document.getElementById('detailPanel');
            if (detailPanel) detailPanel.style.display = 'flex';
        }
        renderAllDetails();
    }
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
            <div class="conv-item-content">
                <div class="conv-title">${escapeHtml(title)}</div>
                <div class="conv-time">${conv.created_at || ''}</div>
            </div>
            <button class="conv-delete-btn" onclick="event.stopPropagation(); deleteConvFromSidebar('${conv.id}')" title="删除对话">×</button>
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
    const detailPanel = document.getElementById('detailPanel');
    if (detailPanel) detailPanel.style.display = 'none';
    const quickActions = document.getElementById('quickActions');
    if (quickActions) quickActions.style.display = 'none';
}

function selectConversation(id) {
    currentConvId = id;
    renderConvList();
    renderChat();
    const conv = getCurrentConv();
    const detailPanel = document.getElementById('detailPanel');
    if (conv && conv.skill_tree && Object.keys(conv.skill_tree).length > 0) {
        if (detailPanel) detailPanel.style.display = 'flex';
        renderAllDetails();
    } else {
        if (detailPanel) detailPanel.style.display = 'none';
    }
}

// ========== 聊天渲染 ==========
function renderChat() {
    const conv = getCurrentConv();
    const chatTitle = document.getElementById('chatTitle');
    const chatSubtitle = document.getElementById('chatSubtitle');
    const messagesEl = document.getElementById('messages');
    const welcome = document.getElementById('welcomeScreen');
    const quickActions = document.getElementById('quickActions');
    const quickSetup = document.getElementById('quickSetup');

    if (!conv || !messagesEl || !welcome) return;

    // 更新连续打卡徽章
    const streakBadge = document.getElementById('streakBadge');
    const streakCount = document.getElementById('streakCount');
    const streak = (conv.study_log && conv.study_log.streak_days) || 0;
    if (streakBadge && streakCount) {
        if (streak > 0) {
            streakBadge.style.display = 'flex';
            streakCount.textContent = streak;
        } else {
            streakBadge.style.display = 'none';
        }
    }

    if (chatTitle) chatTitle.textContent = conv.goal || '新对话';
    if (chatSubtitle) chatSubtitle.textContent = conv.created_at ? `创建于 ${conv.created_at}` : '';

    if (conv.messages.length <= 1) {
        welcome.style.display = 'flex';
        messagesEl.innerHTML = '';
        if (quickActions) quickActions.style.display = 'none';
        if (quickSetup) quickSetup.style.display = 'none';
        return;
    }
    welcome.style.display = 'none';

    // 检测AI是否在追问学情，显示快速选择面板
    const lastMsg = conv.messages[conv.messages.length - 1];
    const isAsking = lastMsg && lastMsg.role === 'assistant' && 
        (lastMsg.content.includes('还需要了解') || lastMsg.content.includes('用默认设置') || lastMsg.content.includes('请告诉我'));
    if (quickSetup) {
        if (isAsking && conv.stage === 'collecting') {
            quickSetup.style.display = 'block';
        } else {
            quickSetup.style.display = 'none';
        }
    }

    // 有学习计划时显示快捷操作栏
    if (quickActions) {
        if (conv.skill_tree && Object.keys(conv.skill_tree).length > 0) {
            quickActions.style.display = 'flex';
        } else {
            quickActions.style.display = 'none';
        }
    }

    messagesEl.innerHTML = conv.messages.map(msg => {
        const imgHtml = msg.image ? `<img src="${msg.image}" class="message-img" alt="学习记录">` : '';
        return `<div class="message ${msg.role}">
            <div class="message-bubble">${escapeHtml(msg.content)}${imgHtml}</div>
        </div>`;
    }).join('');
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// 学情卡片选择
let setupSelections = {};
function selectSetup(field, value) {
    setupSelections[field] = value;
    // 高亮选中
    document.querySelectorAll('.setup-card').forEach(card => {
        card.classList.remove('selected');
    });
    const cards = document.querySelectorAll('.setup-card');
    cards.forEach(card => {
        const onclick = card.getAttribute('onclick') || '';
        if (onclick.includes(`'${field}','${value}'`)) {
            card.classList.add('selected');
        }
    });
    // 如果基础和时长都选了，自动提交
    if (setupSelections.base && setupSelections.hours) {
        submitSetup();
    }
}

function submitSetup() {
    const base = setupSelections.base || '零基础';
    const hours = setupSelections.hours || '2';
    const conv = getCurrentConv();
    if (conv) {
        conv.base = base;
        conv.hours = parseFloat(hours);
    }
    setupSelections = {};
    document.getElementById('userInput').value = `我的基础是${base}，每天学${hours}小时`;
    sendMessage();
}

function skipSetup() {
    const conv = getCurrentConv();
    if (conv) {
        conv.base = '零基础';
        conv.hours = 2;
    }
    setupSelections = {};
    document.getElementById('userInput').value = '用默认设置直接开始';
    sendMessage();
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

// 图片上传处理
let pendingImage = null;

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        alert('请选择图片文件');
        return;
    }
    // 压缩图片
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            let w = img.width, h = img.height;
            const maxSize = 800;
            if (w > maxSize || h > maxSize) {
                if (w > h) { h = h * maxSize / w; w = maxSize; }
                else { w = w * maxSize / h; h = maxSize; }
            }
            canvas.width = w;
            canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            pendingImage = canvas.toDataURL('image/jpeg', 0.7);
            // 显示预览
            document.getElementById('previewImg').src = pendingImage;
            document.getElementById('imgPreview').style.display = 'inline-block';
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
    event.target.value = '';
}

function removeImage() {
    pendingImage = null;
    document.getElementById('imgPreview').style.display = 'none';
    document.getElementById('previewImg').src = '';
}

function sendExample(text) {
    document.getElementById('userInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    const message = input.value.trim();
    if (!message) return;

    // 确保有当前对话
    let conv = getCurrentConv();
    if (!conv) {
        newConversation();
        conv = getCurrentConv();
    }
    if (!conv) return;

    // 智能补全：收集阶段自动填充默认值，不追问
    if (conv.stage === 'collecting') {
        if (!conv.base) conv.base = '零基础';
        if (!conv.hours || conv.hours === 0) conv.hours = 2;
        if (!conv.deadline) conv.deadline = '1个月';
    }

    input.value = '';
    input.style.height = 'auto';
    if (sendBtn) sendBtn.disabled = true;
    if (typingIndicator) typingIndicator.style.display = 'block';

    // 清除图片预览
    const hasImage = !!pendingImage;
    const imageData = pendingImage;
    removeImage();

    try {
        // 先添加用户消息（带图片）
        const userMsg = { role: 'user', content: message };
        if (imageData) userMsg.image = imageData;
        conv.messages.push(userMsg);
        updateConv(conv);
        renderChat();

        // 发送API请求（带图片）
        const payload = { conv: conv, message: message };
        if (imageData) payload.image = imageData;
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errText = await res.text().catch(() => '');
            throw new Error(`API请求失败 (${res.status}) ${errText}`);
        }

        const data = await res.json();
        if (!data || !data.conv) {
            throw new Error('API返回数据格式错误');
        }

        // 合并后端返回的状态，保留前端消息记录
        const idx = conversations.findIndex(c => c.id === data.conv.id);
        if (idx >= 0) {
            const preservedMessages = conversations[idx].messages;
            conversations[idx] = data.conv;
            conversations[idx].messages = preservedMessages;
            conversations[idx].messages.push({ role: 'assistant', content: data.reply || '（无回复）' });
            saveConversations();
            renderChat();
        }

        // 更新标题
        const chatTitle = document.getElementById('chatTitle');
        if (chatTitle && data.conv.goal) {
            chatTitle.textContent = data.conv.goal;
        }

        // 显示详情面板和快捷操作栏
        if (data.conv.skill_tree && Object.keys(data.conv.skill_tree).length > 0) {
            const detailPanel = document.getElementById('detailPanel');
            if (detailPanel) detailPanel.style.display = 'flex';
            const quickActions = document.getElementById('quickActions');
            if (quickActions) quickActions.style.display = 'flex';
            selectedPlanIndex = 0;
            renderAllDetails();
        }

        renderConvList();
    } catch (e) {
        console.error('sendMessage error:', e);
        const errConv = getCurrentConv();
        if (errConv) {
            errConv.messages.push({ role: 'assistant', content: '抱歉，处理你的消息时出错了：' + e.message + '\n\n请稍后重试，或检查网络连接和API Key配置。' });
            updateConv(errConv);
            renderChat();
        }
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        if (typingIndicator) typingIndicator.style.display = 'none';
    }
}

// 快捷操作
function quickAction(type) {
    const conv = getCurrentConv();
    if (!conv) return;
    const messages = {
        quiz: '考考我',
        adjust: '帮我调整一下学习计划',
        next: '我下一步应该学什么',
        record: '',
        export: ''
    };
    if (type === 'export') {
        downloadICS();
        return;
    }
    if (type === 'record') {
        // 显示时长快速选择
        showRecordPicker();
        return;
    }
    document.getElementById('userInput').value = messages[type];
    sendMessage();
}

// 学习时长快速选择器
function showRecordPicker() {
    const existing = document.getElementById('recordPicker');
    if (existing) { existing.remove(); return; }
    const picker = document.createElement('div');
    picker.id = 'recordPicker';
    picker.className = 'record-picker';
    picker.innerHTML = `
        <div class="picker-title">今天学了多久？</div>
        <div class="picker-options">
            <button onclick="recordHours(0.5)">30分钟</button>
            <button onclick="recordHours(1)">1小时</button>
            <button onclick="recordHours(2)">2小时</button>
            <button onclick="recordHours(3)">3小时</button>
            <button onclick="recordHours(4)">4小时+</button>
        </div>
    `;
    const inputArea = document.querySelector('.input-area');
    inputArea.parentNode.insertBefore(picker, inputArea);
}

function recordHours(hours) {
    const picker = document.getElementById('recordPicker');
    if (picker) picker.remove();
    document.getElementById('userInput').value = `今天学了${hours}小时`;
    sendMessage();
}

// ========== Tab切换 ==========
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
}

// ========== 手机端底部Tab切换 ==========
function switchMobileTab(tab) {
    const chatArea = document.getElementById('chatArea');
    const detailPanel = document.getElementById('detailPanel');
    const tabs = document.querySelectorAll('.mobile-tab');

    tabs.forEach(t => t.classList.remove('active'));
    document.querySelector(`.mobile-tab[data-mtab="${tab}"]`).classList.add('active');

    if (tab === 'chat') {
        chatArea.style.display = 'flex';
        detailPanel.classList.remove('mobile-show');
        detailPanel.style.display = 'none';
    } else {
        // 切换到学习路线前，确保详情已渲染
        const conv = getCurrentConv();
        if (conv && conv.skill_tree && Object.keys(conv.skill_tree).length > 0) {
            renderAllDetails();
            chatArea.style.display = 'none';
            detailPanel.classList.add('mobile-show');
            detailPanel.style.display = 'flex';
        } else {
            // 还没有生成计划，提示用户
            alert('请先在聊天中输入学习目标，生成学习计划后再查看路线');
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelector('.mobile-tab[data-mtab="chat"]').classList.add('active');
        }
    }
}

// ========== 手机端侧边栏开关 ==========
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
    // 创建或切换遮罩层
    let overlay = document.getElementById('sidebarOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'sidebarOverlay';
        overlay.className = 'sidebar-overlay';
        overlay.onclick = toggleSidebar;
        document.querySelector('.app').appendChild(overlay);
    }
    overlay.classList.toggle('show');
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
    const isCompleting = idx < 0; // 是否是刚勾选（不是取消）
    if (idx >= 0) {
        conv.completed_kps.splice(idx, 1);
    } else {
        conv.completed_kps.push(name);
    }
    updateConv(conv);
    renderSkillTree();
    renderStats();

    // 勾选时触发点亮动画
    if (isCompleting) {
        setTimeout(() => {
            const checkboxes = document.querySelectorAll('.kp-checkbox');
            checkboxes.forEach(cb => {
                if (cb.checked && cb.nextElementSibling) {
                    const kpName = cb.nextElementSibling.querySelector('.kp-name');
                    if (kpName && kpName.textContent === name) {
                        const item = cb.closest('.kp-item');
                        if (item) {
                            item.classList.add('kp-anim');
                            setTimeout(() => item.classList.remove('kp-anim'), 1000);
                        }
                    }
                }
            });
        }, 50);
    }
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
    const studyLog = conv.study_log || { total_hours: 0, daily: {}, streak_days: 0, week_hours: 0 };

    // 学习计时器
    const isTiming = window._timerRunning;
    const timerDisplay = isTiming ? formatTimer(window._timerSeconds) : '00:00:00';
    const timerBtnText = isTiming ? '结束学习' : '开始学习';
    const timerBtnClass = isTiming ? 'timer-btn stop' : 'timer-btn start';

    let html = `<div class="stats-section">
        <div class="stats-section-title">学习计时器</div>
        <div class="timer-card">
            <div class="timer-display" id="timerDisplay">${timerDisplay}</div>
            <button class="${timerBtnClass}" id="timerBtn" onclick="toggleTimer()">${timerBtnText}</button>
            <div class="timer-hint">点击开始，结束后自动记录学习时长</div>
        </div>
    </div>`;

    // 学习时长看板
    const totalHours = studyLog.total_hours || 0;
    const weekHours = studyLog.week_hours || 0;
    const studyDays = Object.keys(studyLog.daily || {}).length;
    const streak = studyLog.streak_days || 0;

    // 最近7天柱状图数据
    const today = new Date();
    const dayNames = ['日', '一', '二', '三', '四', '五', '六'];
    let chartBars = '';
    let maxHours = 0;
    const last7 = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dStr = d.toISOString().split('T')[0];
        const h = (studyLog.daily && studyLog.daily[dStr]) || 0;
        last7.push({ day: dayNames[d.getDay()], hours: h, date: dStr });
        if (h > maxHours) maxHours = h;
    }
    last7.forEach(item => {
        const hPercent = maxHours > 0 ? (item.hours / maxHours * 100) : 0;
        const isToday = item.date === today.toISOString().split('T')[0];
        chartBars += `<div class="chart-col">
            <div class="chart-bar-wrap">
                <div class="chart-bar ${isToday ? 'today' : ''}" style="height:${Math.max(hPercent, 4)}%"></div>
            </div>
            <div class="chart-label">${item.day}</div>
            <div class="chart-value">${item.hours > 0 ? item.hours + 'h' : ''}</div>
        </div>`;
    });

    html += `<div class="stats-section">
        <div class="stats-section-title">学习时长统计</div>
        <div class="time-grid">
            <div class="time-card">
                <div class="time-value">${totalHours}h</div>
                <div class="time-label">累计总时长</div>
            </div>
            <div class="time-card">
                <div class="time-value">${weekHours}h</div>
                <div class="time-label">本周学习</div>
            </div>
            <div class="time-card">
                <div class="time-value">${studyDays}天</div>
                <div class="time-label">学习天数</div>
            </div>
            <div class="time-card">
                <div class="time-value">${streak}天</div>
                <div class="time-label">连续打卡</div>
            </div>
        </div>
        <div class="week-chart">
            <div class="chart-title">最近7天学习时长</div>
            <div class="chart-bars">${chartBars}</div>
        </div>
        <div class="record-hint">在对话框输入「今天学了2小时」即可自动记录</div>
    </div>`;

    html += `<div class="stats-grid">
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

// ========== 学习计时器 ==========
window._timerRunning = false;
window._timerSeconds = 0;
window._timerInterval = null;

function formatTimer(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function toggleTimer() {
    if (window._timerRunning) {
        stopTimer();
    } else {
        startTimer();
    }
}

function startTimer() {
    window._timerRunning = true;
    window._timerSeconds = 0;
    const btn = document.getElementById('timerBtn');
    const display = document.getElementById('timerDisplay');
    if (btn) { btn.textContent = '结束学习'; btn.className = 'timer-btn stop'; }
    window._timerInterval = setInterval(() => {
        window._timerSeconds++;
        if (display) display.textContent = formatTimer(window._timerSeconds);
    }, 1000);
}

function stopTimer() {
    window._timerRunning = false;
    clearInterval(window._timerInterval);
    const hours = window._timerSeconds / 3600;
    const btn = document.getElementById('timerBtn');
    if (btn) { btn.textContent = '开始学习'; btn.className = 'timer-btn start'; }

    if (window._timerSeconds < 60) {
        alert('学习时间太短啦，至少学1分钟再记录吧~');
        window._timerSeconds = 0;
        return;
    }

    // 自动记录学习时长
    const conv = getCurrentConv();
    if (conv) {
        const hoursRounded = Math.round(hours * 10) / 10;
        document.getElementById('userInput').value = `今天学了${hoursRounded}小时`;
        sendMessage();
    }
    window._timerSeconds = 0;
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

function deleteConvFromSidebar(id) {
    if (!confirm('确定要删除这个对话吗？此操作不可恢复。')) return;
    conversations = conversations.filter(c => c.id !== id);
    if (currentConvId === id) {
        currentConvId = null;
        document.getElementById('messages').innerHTML = '';
        document.getElementById('welcomeScreen').style.display = 'block';
        document.getElementById('detailPanel').style.display = 'none';
        document.getElementById('chatTitle').textContent = '智能学习伴侣';
        document.getElementById('chatSubtitle').textContent = '输入你的学习目标，AI为你规划';
    }
    saveConversations();
    renderConvList();
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
