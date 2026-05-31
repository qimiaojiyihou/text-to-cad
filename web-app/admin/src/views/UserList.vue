<template>
  <div class="user-list">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <button class="btn-success" @click="showAddModal = true">+ 新增用户</button>
    </div>

    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal">
        <h3>新增用户</h3>
        <div class="form-row">
          <label>用户名</label>
          <input v-model="addForm.username" placeholder="3-50位字母数字" />
        </div>
        <div class="form-row">
          <label>邮箱</label>
          <input v-model="addForm.email" type="email" placeholder="user@example.com" />
        </div>
        <div class="form-row">
          <label>密码</label>
          <input v-model="addForm.password" type="password" placeholder="至少6位" />
        </div>
        <div class="form-row">
          <label>昵称</label>
          <input v-model="addForm.full_name" placeholder="可选" />
        </div>
        <div v-if="addError" class="error-text">{{ addError }}</div>
        <div class="modal-actions">
          <button class="btn-primary" @click="addUser" :disabled="addLoading">
            {{ addLoading ? '创建中...' : '创建' }}
          </button>
          <button class="btn-default" @click="showAddModal = false">取消</button>
        </div>
      </div>
    </div>

    <div class="filter-bar">
      <input
        v-model="search"
        type="text"
        placeholder="搜索用户名、邮箱、昵称..."
        class="search-input"
        @keyup.enter="loadUsers"
      />
      <select v-model="filterActive" class="filter-select" @change="loadUsers">
        <option value="">全部状态</option>
        <option value="true">已启用</option>
        <option value="false">已禁用</option>
      </select>
      <select v-model="filterSuper" class="filter-select" @change="loadUsers">
        <option value="">全部权限</option>
        <option value="true">管理员</option>
        <option value="false">普通用户</option>
      </select>
      <button class="btn-primary" @click="loadUsers">搜索</button>
    </div>

    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>邮箱</th>
            <th>昵称</th>
            <th>状态</th>
            <th>权限</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.full_name || '-' }}</td>
            <td>
              <span :class="['badge', u.is_active ? 'badge-success' : 'badge-danger']">
                {{ u.is_active ? '正常' : '已禁用' }}
              </span>
            </td>
            <td>
              <span :class="['badge', u.is_superuser ? 'badge-warning' : 'badge-default']">
                {{ u.is_superuser ? '管理员' : '普通用户' }}
              </span>
            </td>
            <td>{{ formatDate(u.created_at) }}</td>
            <td>
              <div class="actions">
                <button class="action-btn" @click="$router.push(`/users/${u.id}`)">编辑</button>
                <button
                  class="action-btn"
                  :class="u.is_active ? 'btn-danger' : 'btn-success'"
                  @click="toggleActive(u)"
                >
                  {{ u.is_active ? '禁用' : '启用' }}
                </button>
                <button class="action-btn btn-danger" @click="deleteUser(u)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="8" class="empty-cell">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button :disabled="page <= 1" @click="page--; loadUsers()">上一页</button>
      <span>第 {{ page }} 页 / 共 {{ totalPages }} 页</span>
      <button :disabled="page >= totalPages" @click="page++; loadUsers()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../stores/auth.js'

const users = ref([])
const search = ref('')
const filterActive = ref('')
const filterSuper = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)
const totalPages = ref(1)

const showAddModal = ref(false)
const addLoading = ref(false)
const addError = ref('')
const addForm = ref({ username: '', email: '', password: '', full_name: '' })

onMounted(loadUsers)

async function addUser() {
  addError.value = ''
  if (!addForm.value.username || !addForm.value.email || !addForm.value.password) {
    addError.value = '用户名、邮箱、密码不能为空'
    return
  }
  addLoading.value = true
  try {
    const res = await apiFetch('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: addForm.value.username,
        email: addForm.value.email,
        password: addForm.value.password,
        full_name: addForm.value.full_name || null,
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      addError.value = data.detail || '创建失败'
      return
    }
    addForm.value = { username: '', email: '', password: '', full_name: '' }
    showAddModal.value = false
    page.value = 1
    loadUsers()
  } catch (err) {
    addError.value = err.message || '网络错误'
  } finally {
    addLoading.value = false
  }
}

async function loadUsers() {
  try {
    const params = new URLSearchParams()
    params.set('skip', String((page.value - 1) * pageSize))
    params.set('limit', String(pageSize))
    if (search.value) params.set('search', search.value)
    if (filterActive.value !== '') params.set('is_active', filterActive.value)
    if (filterSuper.value !== '') params.set('is_superuser', filterSuper.value)

    const res = await apiFetch(`/api/v1/users?${params}`)
    const data = await res.json()
    users.value = data.items || []
    total.value = data.total || 0
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize))
  } catch (err) {
    alert('加载用户列表失败: ' + err.message)
  }
}

async function toggleActive(u) {
  if (!confirm(`确定要${u.is_active ? '禁用' : '启用'}用户 "${u.username}" 吗？`)) return
  try {
    const res = await apiFetch(`/api/v1/users/${u.id}/toggle-active`, { method: 'POST' })
    if (!res.ok) throw new Error((await res.json()).detail)
    loadUsers()
  } catch (err) {
    alert('操作失败: ' + err.message)
  }
}

async function deleteUser(u) {
  if (!confirm(`确定要删除用户 "${u.username}" 吗？此操作不可恢复！`)) return
  try {
    const res = await apiFetch(`/api/v1/users/${u.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error((await res.json()).detail)
    loadUsers()
  } catch (err) {
    alert('删除失败: ' + err.message)
  }
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.btn-success {
  padding: 10px 20px;
  background: #52c41a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}

.modal h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #1a1a2e;
}

.modal .form-row {
  margin-bottom: 16px;
}

.modal .form-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #666;
}

.modal .form-row input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.error-text {
  color: #ff4d4f;
  font-size: 13px;
  margin-bottom: 12px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 8px;
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

.data-table td {
  font-size: 14px;
  color: #333;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.badge-success { background: #f6ffed; color: #52c41a; }
.badge-danger { background: #fff1f0; color: #ff4d4f; }
.badge-warning { background: #fff7e6; color: #fa8c16; }
.badge-default { background: #f5f5f5; color: #666; }

.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.action-btn.btn-success {
  border-color: #52c41a;
  color: #52c41a;
}

.action-btn.btn-danger {
  border-color: #ff4d4f;
  color: #ff4d4f;
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
