<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="logo">
        <h2>Text-to-CAD</h2>
        <span>后台管理</span>
      </div>
      <nav class="menu">
        <router-link to="/dashboard" class="menu-item" active-class="active">
          <span class="icon">📊</span>
          <span>概览</span>
        </router-link>
        <router-link to="/users" class="menu-item" active-class="active">
          <span class="icon">👥</span>
          <span>用户管理</span>
        </router-link>
        <router-link to="/records" class="menu-item" active-class="active">
          <span class="icon">📁</span>
          <span>生成记录</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="admin-info">
          <span class="admin-name">{{ auth.state.user?.username }}</span>
          <span class="admin-role">管理员</span>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: #001529;
  color: #fff;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
}

.logo {
  padding: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo h2 {
  font-size: 18px;
  margin-bottom: 4px;
}

.logo span {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
}

.menu {
  flex: 1;
  padding: 16px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
}

.menu-item:hover {
  color: #fff;
  background: rgba(255,255,255,0.05);
}

.menu-item.active {
  color: #fff;
  background: #1890ff;
}

.menu-item .icon {
  margin-right: 12px;
  font-size: 16px;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.admin-info {
  margin-bottom: 12px;
}

.admin-name {
  display: block;
  font-size: 14px;
  font-weight: 500;
}

.admin-role {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

.logout-btn {
  width: 100%;
  padding: 8px;
  background: rgba(255,255,255,0.1);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255,255,255,0.2);
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 24px;
  background: #f0f2f5;
  min-height: 100vh;
}
</style>
