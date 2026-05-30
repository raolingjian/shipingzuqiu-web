// Supabase 配置
const SUPABASE_URL = 'https://bmgfwpxqscdwrmqznhas.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJtZ2Z3cHhxc2Nkd3JtcXpuaGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4MjAzODcsImV4cCI6MjA5NTM5NjM4N30.U6bUA8d-FYW9svXwZHAImsJVcfGM1l2GQESUTYqi4Bc'

// 初始化 Supabase 客户端
const supabase = supabaseJs.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// ==============================
// 配置 API
// ==============================
async function getConfig() {
    const { data, error } = await supabase
        .from('configs')
        .select('*')
        .limit(1)
        .single()
    if (error) throw error
    return data
}

async function updateConfig(updates) {
    const { data, error } = await supabase
        .from('configs')
        .update(updates)
        .eq('id', '00000000-0000-0000-0000-000000000001')
        .select()
        .single()
    if (error) throw error
    return data
}

// ==============================
// 任务 API
// ==============================
async function createTask(type, params = {}) {
    const { data, error } = await supabase
        .from('tasks')
        .insert({
            type: type,
            status: 'pending',
            params: params
        })
        .select()
        .single()
    if (error) throw error
    return data
}

async function getTasks(limit = 20) {
    const { data, error } = await supabase
        .from('tasks')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit)
    if (error) throw error
    return data
}

async function updateTaskStatus(id, status, result = {}) {
    const { data, error } = await supabase
        .from('tasks')
        .update({ status, result })
        .eq('id', id)
        .select()
        .single()
    if (error) throw error
    return data
}

// ==============================
// 视频 API
// ==============================
async function getVideos(limit = 20) {
    const { data, error } = await supabase
        .from('videos')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit)
    if (error) throw error
    return data
}

async function createVideo(videoData) {
    const { data, error } = await supabase
        .from('videos')
        .insert(videoData)
        .select()
        .single()
    if (error) throw error
    return data
}

// ==============================
// 实时订阅
// ==============================
function subscribeToTasks(callback) {
    return supabase
        .channel('tasks-channel')
        .on('postgres_changes', 
            { event: '*', schema: 'public', table: 'tasks' },
            (payload) => callback(payload)
        )
        .subscribe()
}