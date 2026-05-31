<template>
  <div class="record-list">
    <div class="page-header">
      <h1 class="page-title">生成记录</h1>
    </div>

    <div class="filter-bar">
      <select v-model="filterUser" class="filter-select" @change="loadRecords">
        <option value="">全部用户</option>
        <option v-for="u in users" :key="u.id" :value="u.id">{{ u.username }}</option>
      </select>
      <select v-model="filterStatus" class="filter-select" @change="loadRecords">
        <option value="">全部状态</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
        <option value="pending">等待中</option>
        <option value="llm_running">LLM 生成中</option>
        <option value="cad_running">CAD 计算中</option>
      </select>
      <input
        v-model="search"
        type="text"
        placeholder="搜索描述..."
        class="search-input"
        @keyup.enter="loadRecords"
      />
      <button class="btn-primary" @click="loadRecords">搜索</button>
    </div>

    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户</th>
            <th>描述</th>
            <th>状态</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.username || r.user_id }}</td>
            <td class="prompt-cell" :title="r.prompt">{{ r.prompt }}</td>
            <td>
              <span class="status-badge" :class="r.status">{{ statusLabel(r.status) }}</span>
            </td>
            <td>{{ formatDate(r.created_at) }}</td>
            <td class="actions">
              <a v-if="r.glb_path" class="action-link" :href="`${API_BASE}/api/models/${r.model_id}/glb`" target="_blank">GLB</a>
              <a v-if="r.step_path" class="action-link" :href="`${API_BASE}/api/models/${r.model_id}/step`" target="_blank">STEP</a>
              <a v-if="r.py_path" class="action-link" :href="`${API_BASE}/api/models/${r.model_id}/code`" target="_blank">源码</a>
            </td>
          </tr>
          <tr v-if="records.length === 0">
            <td colspan="6" class="empty-cell">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button :disabled="page <= 1" @click="page--; loadRecords()">上一页</button>
      <span>第 {{ page }} 页 / 共 {{ totalPages }} 页</span>
      <button :disabled="page >= totalPages" @click="page++; loadRecords()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../stores/auth.js'

const API_BASE = 'http://127.0.0.1:8000'

const records = ref([])
const users = ref([])
const search = ref('')
const filterUser = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = ref(1)

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

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

async function loadUsers() {
  try {
    const res = await apiFetch('/api/v1/users?limit=9999')
    const data = await res.json()
    users.value = data.items || []
  } catch (err) {
    console.error('加载用户失败:', err)
  }
}

async function loadRecords() {
  try {
    const params = new URLSearchParams()
    params.set('skip', String((page.value - 1) * pageSize))
    params.set('limit', String(pageSize))
    if (filterUser.value) params.set('user_id', filterUser.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (search.value) params.set('search', search.value)

    const res = await apiFetch(`/api/admin/records?${params}`)
    const data = await res.json()
    records.value = data.items || []
    total.value = data.total || 0
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize))
  } catch (err) {
    alert('加载记录失败: ' + err.message)
  }
}

onMounted(async () => {
  await loadUsers()
  await loadRecords()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  color: #1a1a2e;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.search-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.filter-select {
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}

.btn-primary {
  padding: 10px 20px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.table-wrap {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.data-table th {
  font-weight: 500;
  color: #666;
  font-size: 14px;
  background: #fafafa;
}

.prompt-cell {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
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
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.failed {
  background: #fff1f0;
  color: #ff4d4f;
}

.status-badge.pending,
.status-badge.llm_running,
.status-badge.cad_running {
  background: #e6f7ff;
  color: #1890ff;
}

.actions {
  display: flex;
  gap: 8px;
}

.action-link {
  padding: 4px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: #1890ff;
  text-decoration: none;
  font-size: 12px;
}

.empty-cell {
  text-align: center;
  color: #999;
  padding: 60px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
