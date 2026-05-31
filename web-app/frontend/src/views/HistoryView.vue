<template>
  <div class="history-page">
    <aside class="sidebar">
      <h1>Text to CAD</h1>
      <nav>
        <router-link to="/" class="nav-link">生成 CAD</router-link>
        <router-link to="/history" class="nav-link active">历史记录</router-link>
      </nav>
      <footer class="footer">Powered by build123d + LLM</footer>
    </aside>

    <main class="main">
      <header class="top-bar">
        <h2>历史生成记录</h2>
        <UserMenu @show-auth="showAuth = true" />
      </header>

      <div class="content">
        <div class="filters">
          <select v-model="filterStatus" class="filter-select">
            <option value="">全部状态</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
            <option value="pending">处理中</option>
            <option value="llm_running">LLM 生成中</option>
            <option value="cad_running">CAD 计算中</option>
          </select>
        </div>

        <div v-if="loading" class="loading">加载中…</div>

        <table v-else-if="records.length" class="record-table">
          <thead>
            <tr>
              <th>描述</th>
              <th>状态</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.id">
              <td class="prompt-cell" :title="r.prompt">{{ r.prompt }}</td>
              <td>
                <span class="status-badge" :class="r.status">{{ statusLabel(r.status) }}</span>
              </td>
              <td class="time-cell">{{ formatTime(r.created_at) }}</td>
              <td class="action-cell">
                <button v-if="r.status === 'completed' || r.status === 'cached'" class="action-btn" @click="preview(r.model_id)">预览</button>
                <a v-if="r.glb_path" class="action-link" :href="`/api/models/${r.model_id}/glb`" :download="`${r.model_id}.glb`">GLB</a>
                <a v-if="r.step_path" class="action-link" :href="`/api/models/${r.model_id}/step`" :download="`${r.model_id}.step`">STEP</a>
                <a v-if="r.py_path" class="action-link" :href="`/api/models/${r.model_id}/code`" :download="`${r.model_id}.py`">源码</a>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-else class="empty">暂无生成记录</div>

        <div v-if="total > limit" class="pagination">
          <button :disabled="skip === 0" @click="prevPage">上一页</button>
          <span>{{ skip + 1 }} - {{ Math.min(skip + limit, total) }} / {{ total }}</span>
          <button :disabled="skip + limit >= total" @click="nextPage">下一页</button>
        </div>
      </div>
    </main>

    <AuthModal v-if="showAuth" @close="showAuth = false" @success="onAuthSuccess" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import authStore from '../stores/auth.js'
import UserMenu from '../components/UserMenu.vue'
import AuthModal from '../components/AuthModal.vue'

const router = useRouter()
const records = ref([])
const total = ref(0)
const skip = ref(0)
const limit = ref(20)
const loading = ref(false)
const filterStatus = ref('')
const showAuth = ref(false)

function onAuthSuccess() {
  showAuth.value = false
  loadRecords()
}

const STATUS_LABELS = {
  pending: '等待中',
  llm_running: 'LLM 生成中',
  cad_running: 'CAD 计算中',
  completed: '已完成',
  cached: '已缓存',
  failed: '失败',
}

function statusLabel(s) {
  return STATUS_LABELS[s] || s
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

async function loadRecords() {
  loading.value = true
  try {
    const params = new URLSearchParams({ skip: skip.value, limit: limit.value })
    if (filterStatus.value) params.append('status', filterStatus.value)
    const res = await authStore.fetchWithAuth(`/api/records?${params}`)
    const data = await res.json()
    if (res.ok) {
      records.value = data.items || []
      total.value = data.total || 0
    } else {
      records.value = []
      total.value = 0
    }
  } catch (e) {
    console.error('Load records failed:', e)
    records.value = []
  } finally {
    loading.value = false
  }
}

function nextPage() {
  skip.value += limit.value
  loadRecords()
}

function prevPage() {
  skip.value = Math.max(0, skip.value - limit.value)
  loadRecords()
}

function preview(modelId) {
  router.push({ path: '/', query: { preview: modelId } })
}

watch(filterStatus, () => {
  skip.value = 0
  loadRecords()
})

onMounted(loadRecords)
</script>

<style scoped>
.history-page {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: #0d1117;
  color: #c9d1d9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.sidebar {
  width: 220px;
  min-width: 220px;
  background: #161b22;
  border-right: 1px solid #30363d;
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  box-sizing: border-box;
}

.sidebar h1 {
  margin: 0 0 24px 0;
  font-size: 20px;
  color: #58a6ff;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-link {
  padding: 10px 14px;
  border-radius: 8px;
  color: #8b949e;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #21262d;
  color: #c9d1d9;
}

.nav-link.active {
  background: #1f6feb22;
  color: #58a6ff;
  font-weight: 500;
}

.footer {
  margin-top: auto;
  font-size: 11px;
  color: #484f58;
  text-align: center;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  height: 56px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.top-bar h2 {
  margin: 0;
  font-size: 18px;
  color: #c9d1d9;
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.filters {
  margin-bottom: 16px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #30363d;
  border-radius: 6px;
  background: #0d1117;
  color: #c9d1d9;
  font-size: 14px;
}

.record-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.record-table th {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid #30363d;
  color: #8b949e;
  font-weight: 500;
}

.record-table td {
  padding: 12px;
  border-bottom: 1px solid #21262d;
  vertical-align: middle;
}

.prompt-cell {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-cell {
  color: #8b949e;
  font-size: 13px;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.completed,
.status-badge.cached {
  background: #23863622;
  color: #3fb950;
}

.status-badge.failed {
  background: #da363322;
  color: #f85149;
}

.status-badge.pending,
.status-badge.llm_running,
.status-badge.cad_running {
  background: #1f6feb22;
  color: #58a6ff;
}

.action-cell {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  background: #1f6feb;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.action-link {
  padding: 4px 10px;
  border: 1px solid #30363d;
  border-radius: 4px;
  color: #58a6ff;
  text-decoration: none;
  font-size: 12px;
}

.loading, .empty {
  padding: 40px;
  text-align: center;
  color: #8b949e;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding: 16px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #30363d;
  border-radius: 6px;
  background: #161b22;
  color: #c9d1d9;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination span {
  color: #8b949e;
  font-size: 14px;
}
</style>
