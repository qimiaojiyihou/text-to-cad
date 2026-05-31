<template>
  <div class="dashboard">
    <h1 class="page-title">管理概览</h1>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e6f7ff; color: #1890ff;">👥</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_users }}</div>
          <div class="stat-label">总用户</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f6ffed; color: #52c41a;">📦</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_records }}</div>
          <div class="stat-label">生成总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6; color: #fa8c16;">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.completed_records }}</div>
          <div class="stat-label">成功</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0; color: #ff4d4f;">❌</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.failed_records }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f9f0ff; color: #722ed1;">📅</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.today_records }}</div>
          <div class="stat-label">今日生成</div>
        </div>
      </div>
    </div>

    <div class="recent-section">
      <h2>最近注册用户</h2>
      <div class="recent-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>邮箱</th>
              <th>注册时间</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in recentUsers" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.email }}</td>
              <td>{{ formatDate(u.created_at) }}</td>
              <td>
                <span :class="['badge', u.is_active ? 'badge-success' : 'badge-danger']">
                  {{ u.is_active ? '正常' : '已禁用' }}
                </span>
              </td>
            </tr>
            <tr v-if="recentUsers.length === 0">
              <td colspan="5" class="empty-cell">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../stores/auth.js'

const stats = ref({ total_users: 0, total_records: 0, completed_records: 0, failed_records: 0, today_records: 0 })
const recentUsers = ref([])

onMounted(async () => {
  try {
    const res = await apiFetch('/api/v1/users?limit=5')
    const data = await res.json()
    recentUsers.value = data.items || []

    const statsRes = await apiFetch('/api/admin/stats')
    const statsData = await statsRes.json()
    stats.value = {
      total_users: statsData.total_users || 0,
      total_records: statsData.total_records || 0,
      completed_records: statsData.completed_records || 0,
      failed_records: statsData.failed_records || 0,
      today_records: statsData.today_records || 0,
    }
  } catch (err) {
    console.error('加载仪表盘数据失败:', err)
  }
})

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.page-title {
  font-size: 24px;
  margin-bottom: 24px;
  color: #1a1a2e;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-right: 16px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.recent-section {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.recent-section h2 {
  font-size: 18px;
  margin-bottom: 16px;
  color: #1a1a2e;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.data-table th {
  font-weight: 500;
  color: #666;
  font-size: 14px;
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

.badge-success {
  background: #f6ffed;
  color: #52c41a;
}

.badge-danger {
  background: #fff1f0;
  color: #ff4d4f;
}

.empty-cell {
  text-align: center;
  color: #999;
  padding: 40px;
}
</style>
