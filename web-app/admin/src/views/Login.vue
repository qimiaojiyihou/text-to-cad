<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-header">
        <h1>Text-to-CAD</h1>
        <p>后台管理系统</p>
      </div>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="form.username"
            type="text"
            placeholder="请输入用户名"
            required
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            required
          />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <div class="login-tip">
        <p>默认账号: admin / 123456</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const error = ref('')

const form = reactive({
  username: '',
  password: '',
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    if (!auth.isAdmin.value) {
      error.value = '您没有管理员权限'
      auth.logout()
      return
    }
    router.push('/dashboard')
  } catch (err) {
    error.value = err.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-box {
  width: 400px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 28px;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.login-header p {
  color: #666;
  font-size: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #1890ff;
}

.error-msg {
  color: #ff4d4f;
  font-size: 14px;
  margin-bottom: 16px;
  text-align: center;
}

.login-btn {
  width: 100%;
  padding: 14px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.login-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-tip {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}

.login-tip p {
  color: #999;
  font-size: 13px;
}
</style>
