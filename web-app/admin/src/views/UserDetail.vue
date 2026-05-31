<template>
  <div class="user-detail">
    <div class="page-header">
      <h1 class="page-title">用户详情</h1>
      <button class="btn-default" @click="$router.push('/users')">返回列表</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!user" class="empty">用户不存在</div>
    <div v-else class="detail-card">
      <div class="detail-section">
        <h3>基本信息</h3>
        <div class="form-row">
          <label>用户名</label>
          <input v-model="form.username" disabled />
        </div>
        <div class="form-row">
          <label>邮箱</label>
          <input v-model="form.email" type="email" />
        </div>
        <div class="form-row">
          <label>昵称</label>
          <input v-model="form.full_name" placeholder="未设置" />
        </div>
        <div class="form-row">
          <label>新密码</label>
          <input v-model="form.password" type="password" placeholder="留空则不修改" />
        </div>
        <button class="btn-primary" @click="saveUser">保存修改</button>
      </div>

      <div class="detail-section">
        <h3>账号状态</h3>
        <div class="status-row">
          <span>当前状态:</span>
          <span :class="['badge', user.is_active ? 'badge-success' : 'badge-danger']">
            {{ user.is_active ? '正常' : '已禁用' }}
          </span>
          <button
            class="action-btn"
            :class="user.is_active ? 'btn-danger' : 'btn-success'"
            @click="toggleActive"
          >
            {{ user.is_active ? '禁用账号' : '启用账号' }}
          </button>
        </div>
        <div class="status-row">
          <span>用户权限:</span>
          <span :class="['badge', user.is_superuser ? 'badge-warning' : 'badge-default']">
            {{ user.is_superuser ? '管理员' : '普通用户' }}
          </span>
          <button
            class="action-btn"
            :class="user.is_superuser ? 'btn-default' : 'btn-warning'"
            @click="toggleSuperuser"
          >
            {{ user.is_superuser ? '取消管理员' : '设为管理员' }}
          </button>
        </div>
      </div>

      <div class="detail-section danger-zone">
        <h3>危险操作</h3>
        <button class="btn-danger" @click="deleteUser">删除此用户</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const user = ref(null)
const loading = ref(true)
const form = ref({ username: '', email: '', full_name: '', password: '' })

onMounted(async () => {
  await loadUser()
})

async function loadUser() {
  try {
    const res = await apiFetch(`/api/v1/users/${route.params.id}`)
    if (!res.ok) throw new Error('用户不存在')
    user.value = await res.json()
    form.value = {
      username: user.value.username,
      email: user.value.email,
      full_name: user.value.full_name || '',
      password: '',
    }
  } catch (err) {
    alert(err.message)
  } finally {
    loading.value = false
  }
}

async function saveUser() {
  try {
    const body = {}
    if (form.value.email !== user.value.email) body.email = form.value.email
    if (form.value.full_name !== (user.value.full_name || '')) body.full_name = form.value.full_name || null
    if (form.value.password) body.password = form.value.password

    if (Object.keys(body).length === 0) {
      alert('没有需要保存的修改')
      return
    }

    const res = await apiFetch(`/api/v1/users/${route.params.id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error((await res.json()).detail)
    alert('保存成功')
    await loadUser()
  } catch (err) {
    alert('保存失败: ' + err.message)
  }
}

async function toggleActive() {
  if (!confirm(`确定要${user.value.is_active ? '禁用' : '启用'}此用户吗？`)) return
  try {
    const res = await apiFetch(`/api/v1/users/${route.params.id}/toggle-active`, { method: 'POST' })
    if (!res.ok) throw new Error((await res.json()).detail)
    await loadUser()
  } catch (err) {
    alert('操作失败: ' + err.message)
  }
}

async function toggleSuperuser() {
  if (!confirm(`确定要${user.value.is_superuser ? '取消' : '授予'}管理员权限吗？`)) return
  try {
    const res = await apiFetch(`/api/v1/users/${route.params.id}/toggle-superuser`, { method: 'POST' })
    if (!res.ok) throw new Error((await res.json()).detail)
    await loadUser()
  } catch (err) {
    alert('操作失败: ' + err.message)
  }
}

async function deleteUser() {
  if (!confirm('确定要删除此用户吗？此操作不可恢复！')) return
  try {
    const res = await apiFetch(`/api/v1/users/${route.params.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error((await res.json()).detail)
    alert('删除成功')
    router.push('/users')
  } catch (err) {
    alert('删除失败: ' + err.message)
  }
}
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

.btn-default {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #999;
}

.detail-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
}

.detail-section {
  padding: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-section h3 {
  font-size: 16px;
  margin-bottom: 16px;
  color: #1a1a2e;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.form-row label {
  width: 80px;
  font-size: 14px;
  color: #666;
}

.form-row input {
  flex: 1;
  max-width: 400px;
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.form-row input:disabled {
  background: #f5f5f5;
  color: #999;
}

.btn-primary {
  padding: 10px 24px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.status-row span:first-child {
  font-size: 14px;
  color: #666;
  width: 80px;
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

.action-btn {
  padding: 6px 14px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.action-btn.btn-success {
  border-color: #52c41a;
  color: #52c41a;
}

.action-btn.btn-danger {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

.action-btn.btn-warning {
  border-color: #fa8c16;
  color: #fa8c16;
}

.danger-zone {
  border-bottom: none;
}

.danger-zone .btn-danger {
  padding: 10px 24px;
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
</style>
