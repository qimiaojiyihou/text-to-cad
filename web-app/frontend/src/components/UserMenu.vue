<template>
  <div class="user-menu">
    <button v-if="!auth.state.user" class="login-btn" @click="emit('show-auth')">
      登录 / 注册
    </button>
    <template v-else>
      <div class="user-info">
        <span class="username">{{ auth.state.user?.username }}</span>
        <button class="logout-btn" @click="auth.logout">退出</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import authStore from '../stores/auth.js'

const auth = authStore
const emit = defineEmits(['show-auth'])
</script>

<style scoped>
.user-menu {
  display: flex;
  align-items: center;
  gap: 12px;
}

.login-btn {
  padding: 6px 16px;
  background: #238636;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.login-btn:hover {
  background: #2ea043;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  color: #c9d1d9;
  font-size: 13px;
}

.logout-btn {
  padding: 4px 10px;
  background: transparent;
  color: #8b949e;
  border: 1px solid #30363d;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.logout-btn:hover {
  color: #f85149;
  border-color: #f85149;
}
</style>
