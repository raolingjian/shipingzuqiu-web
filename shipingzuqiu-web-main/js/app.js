// ==============================
// 应用主逻辑
// ==============================

let currentConfig = null
let tasksSubscription = null

// 初始化
async function initApp() {
    try {
        await loadConfig()
        await loadTasks()
        await loadVideos()
        startRealtimeSubscription()
        updateStatus('online')
    } catch (e) {
        console.error('Init error:', e)
        updateStatus('error')
        showToast('⚠️ 连接 Supabase 失败，请检查表是否已创建')
    }
}

// ==============================
// 状态更新
// ==============================
function updateStatus(status) {
    const dot = document.getElementById('statusDot')
    const text = document.getElementById('statusText')
    if (status === 'online') {
        dot.style.background = '#4caf50'
        text.textContent = '已连接'
    } else if (status === 'loading') {
        dot.style.background = '#ff9800'
        text.textContent = '加载中...'
    } else {
        dot.style.background = '#f44336'
        text.textContent = '未连接'
    }
}

// ==============================
// Toast
// ==============================
function showToast(msg, duration = 2000) {
    const toast = document.getElementById('toast')
    toast.textContent = msg
    toast.style.display = 'block'
    clearTimeout(toast._timer)
    toast._timer = setTimeout(() => { toast.style.display = 'none' }, duration)
}

// ==============================
// Tab 切换
// ==============================
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'))
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'))
    event.target.closest('.tab-btn').classList.add('active')
    document.getElementById('panel-' + tabName).classList.add('active')
}

// ==============================
// 配置管理
// ==============================
async function loadConfig() {
    try {
        currentConfig = await getConfig()
        if (!currentConfig) {
            showToast('⚠️ 请先在 Supabase 中创建 configs 表')
            return
        }
        renderConfigForm(currentConfig)
    } catch (e) {
        console.error('Load config error:', e)
        showToast('⚠️ 加载配置失败：' + e.message)
    }
}

function renderConfigForm(config) {
    document.getElementById('panel-config').innerHTML = `
        <div class="card">
            <div class="card-title">🤖 LLM 配置</div>
            <div class="form-group">
                <label class="form-label">API Key</label>
                <input class="form-input" id="cfg_llm_key" value="${config.llm_api_key || ''}" placeholder="sk-...">
            </div>
            <div class="form-group">
                <label class="form-label">模型</label>
                <input class="form-input" id="cfg_llm_model" value="${config.llm_model || 'deepseek-chat'}">
            </div>
            <div class="form-group">
                <label class="form-label">Base URL</label>
                <input class="form-input" id="cfg_llm_url" value="${config.llm_base_url || 'https://api.deepseek.com'}">
            </div>
        </div>
        <div class="card">
            <div class="card-title">📰 新闻配置</div>
            <div class="form-group">
                <label class="form-label">新闻源 (逗号分隔)</label>
                <input class="form-input" id="cfg_news_sources" value="${(config.news_sources || []).join(',')}">
            </div>
            <div class="form-group">
                <label class="form-label">最大结果数</label>
                <input class="form-input" id="cfg_max_news" type="number" value="${config.max_news_results || 10}">
            </div>
        </div>
        <div class="card">
            <div class="card-title">🎤 TTS 配置</div>
            <div class="form-group">
                <label class="form-label">语音</label>
                <select class="form-select" id="cfg_tts_voice">
                    <option value="zh-CN-YunxiNeural" ${config.tts_voice === 'zh-CN-YunxiNeural' ? 'selected' : ''}>Yunxi (男)</option>
                    <option value="zh-CN-XiaoxiaoNeural" ${config.tts_voice === 'zh-CN-XiaoxiaoNeural' ? 'selected' : ''}>Xiaoxiao (女)</option>
                    <option value="zh-CN-YunjianNeural" ${config.tts_voice === 'zh-CN-YunjianNeural' ? 'selected' : ''}>Yunjian (男)</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">BGM 音量</label>
                <input class="form-input" id="cfg_bgm_volume" type="number" value="${config.bgm_volume || -20}">
            </div>
            <div class="form-row">
                <label class="form-switch">
                    <input type="checkbox" id="cfg_bgm_enabled" ${config.bgm_enabled ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
                <span class="card-value" style="font-size:13px;">BGM 开启</span>
            </div>
        </div>
        <div class="card">
            <div class="card-title">🎬 项目配置</div>
            <div class="form-group">
                <label class="form-label">字体路径</label>
                <input class="form-input" id="cfg_font" value="${config.font_path || 'fonts/msyh.ttc'}">
            </div>
            <div class="form-group">
                <label class="form-label">视频时长 (秒)</label>
                <div class="form-row">
                    <input class="form-input" id="cfg_min_dur" type="number" value="${config.min_duration || 15}" style="width:45%">
                    <span style="color:#888">~</span>
                    <input class="form-input" id="cfg_max_dur" type="number" value="${config.max_duration || 20}" style="width:45%">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">分辨率</label>
                <div class="form-row">
                    <input class="form-input" id="cfg_width" type="number" value="${config.resolution_width || 1080}" style="width:45%">
                    <span style="color:#888">×</span>
                    <input class="form-input" id="cfg_height" type="number" value="${config.resolution_height || 1920}" style="width:45%">
                </div>
            </div>
            <button class="btn btn-primary" onclick="saveConfig()">💾 保存配置</button>
        </div>
    `
}

async function saveConfig() {
    const updates = {
        llm_api_key: document.getElementById('cfg_llm_key').value,
        llm_model: document.getElementById('cfg_llm_model').value,
        llm_base_url: document.getElementById('cfg_llm_url').value,
        news_sources: document.getElementById('cfg_news_sources').value.split(',').map(s => s.trim()),
        max_news_results: parseInt(document.getElementById('cfg_max_news').value) || 10,
        tts_voice: document.getElementById('cfg_tts_voice').value,
        bgm_volume: parseInt(document.getElementById('cfg_bgm_volume').value) || -20,
        bgm_enabled: document.getElementById('cfg_bgm_enabled').checked,
        font_path: document.getElementById('cfg_font').value,
        min_duration: parseInt(document.getElementById('cfg_min_dur').value) || 15,
        max_duration: parseInt(document.getElementById('cfg_max_dur').value) || 20,
        resolution_width: parseInt(document.getElementById('cfg_width').value) || 1080,
        resolution_height: parseInt(document.getElementById('cfg_height').value) || 1920,
    }
    try {
        await updateConfig(updates)
        showToast('✅ 配置已保存')
        currentConfig = await getConfig()
    } catch (e) {
        showToast('❌ 保存失败：' + e.message)
    }
}

// ==============================
// 任务管理
// ==============================
async function loadTasks() {
    try {
        const tasks = await getTasks(20)
        renderTasks(tasks)
        updateTaskStats(tasks)
    } catch (e) {
        console.error('Load tasks error:', e)
    }
}

function renderTasks(tasks) {
    // 概览面板的任务列表
    const container = document.getElementById('tasksList')
    const fullContainer = document.getElementById('tasksListFull')
    
    const html = (!tasks || tasks.length === 0) 
        ? '<div style="text-align:center;padding:20px;color:#666;">暂无任务记录</div>'
        : tasks.map(t => {
        const statusMap = {
            'pending': '<span class="tag tag-gray">待处理</span>',
            'running': '<span class="tag tag-orange">运行中</span>',
            'completed': '<span class="tag tag-green">已完成</span>',
            'failed': '<span class="tag tag-red">失败</span>'
        }
        const typeMap = {
            'fetch_news': '📰 抓取新闻',
            'generate_script': '✍️ 生成脚本',
            'make_video': '🎬 制作视频',
            'publish': '📤 发布'
        }
        const time = new Date(t.created_at).toLocaleString('zh-CN')
        return `
            <div class="card-row">
                <span>${typeMap[t.type] || t.type}</span>
                <span>${statusMap[t.status] || t.status}</span>
            </div>
            <div class="card-row" style="font-size:11px;color:#666;">
                <span>${time}</span>
                <span>${t.error_message || ''}</span>
            </div>
        `
    }).join('')
    
    // 渲染到概览面板
    if (container) container.innerHTML = html
    // 渲染到完整任务列表面板
    if (fullContainer) fullContainer.innerHTML = html
}

function updateTaskStats(tasks) {
    const total = tasks ? tasks.length : 0
    const completed = tasks ? tasks.filter(t => t.status === 'completed').length : 0
    const failed = tasks ? tasks.filter(t => t.status === 'failed').length : 0
    document.getElementById('totalTasks').textContent = total
    document.getElementById('totalTasks2').textContent = total
    document.getElementById('completedTasks').textContent = completed
    document.getElementById('completedTasks2').textContent = completed
    document.getElementById('failedTasks').textContent = failed
}

// ==============================
// 视频管理
// ==============================
async function loadVideos() {
    try {
        const videos = await getVideos(20)
        renderVideos(videos)
        updateVideoStats(videos)
    } catch (e) {
        console.error('Load videos error:', e)
    }
}

function renderVideos(videos) {
    const container = document.getElementById('videosList')
    if (!videos || videos.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">暂无视频</div>'
        return
    }
    container.innerHTML = videos.map(v => {
        const time = new Date(v.created_at).toLocaleString('zh-CN')
        const platforms = (v.published_platforms || []).join(', ')
        return `
            <div class="card-row">
                <span class="card-value">${v.title}</span>
                <span>
                    ${v.video_storage_path ? '<span class="tag tag-green">已生成</span>' : '<span class="tag tag-gray">未生成</span>'}
                </span>
            </div>
            <div class="card-row" style="font-size:11px;color:#666;">
                <span>${time}</span>
                <span>${platforms || '未发布'}</span>
            </div>
        `
    }).join('')
}

function updateVideoStats(videos) {
    const total = videos ? videos.length : 0
    const published = videos ? videos.filter(v => v.published_platforms && v.published_platforms.length > 0).length : 0
    document.getElementById('totalVideos').textContent = total
    document.getElementById('publishedVideos').textContent = published
}

// ==============================
// 触发任务
// ==============================
async function triggerTask(type) {
    const btns = {
        'fetch_news': { btn: 'btnFetchNews', msg: '📰 正在抓取新闻...' },
        'generate_script': { btn: 'btnGenScript', msg: '✍️ 正在生成脚本...' },
        'make_video': { btn: 'btnMakeVideo', msg: '🎬 正在制作视频...' },
        'publish': { btn: 'btnPublish', msg: '📤 正在发布...' },
        'batch': { btn: 'btnBatch', msg: '📦 批量模式启动...' }
    }
    const info = btns[type]
    if (!info) return
    
    const btn = document.getElementById(info.btn)
    if (btn) {
        btn.disabled = true
        btn.innerHTML = '<span class="loading"></span> 处理中...'
    }
    showToast(info.msg)
    
    try {
        const task = await createTask(type, { triggered_by: 'web' })
        showToast(`✅ 任务已创建 (${task.type})`)
        await loadTasks()
    } catch (e) {
        showToast('❌ 创建任务失败：' + e.message)
    } finally {
        if (btn) {
            btn.disabled = false
            btn.innerHTML = getBtnText(type)
        }
    }
}

function getBtnText(type) {
    const texts = {
        'fetch_news': '📰 抓取今日热点',
        'generate_script': '✍️ 生成脚本',
        'make_video': '🎬 制作视频',
        'publish': '📤 发布到全平台',
        'batch': '📦 批量模式 (×3)'
    }
    return texts[type] || type
}

// ==============================
// 实时订阅
// ==============================
function startRealtimeSubscription() {
    if (tasksSubscription) return
    tasksSubscription = subscribeToTasks((payload) => {
        loadTasks()
        showToast(`🔄 任务状态更新: ${payload.eventType}`)
    })
}

// ==============================
// 页面加载时初始化
// ==============================
document.addEventListener('DOMContentLoaded', () => {
    initApp()
})