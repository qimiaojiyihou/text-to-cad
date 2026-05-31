<template>
  <div class="auth-overlay" @click.self="emit('close')">
    <div class="auth-modal">
      <div class="auth-header">
        <h2>{{ isLogin ? '登录' : '注册' }}</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="form.username"
            type="text"
            placeholder="3-50位字母数字"
            required
            minlength="3"
            maxlength="50"
            pattern="[a-zA-Z0-9_-]+"
          />
        </div>

        <div v-if="!isLogin" class="form-group">
          <label>邮箱</label>
          <input v-model="form.email" type="email" placeholder="your@email.com" required />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="至少6位"
            required
            minlength="6"
          />
        </div>

        <div v-if="!isLogin" class="form-group">
          <label>昵称（可选）</label>
          <input v-model="form.full_name" type="text" placeholder="你的名字" />
        </div>

        <div v-if="authStore.state.error" class="error-msg">
          {{ authStore.state.error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="authStore.state.isLoading">
          {{ authStore.state.isLoading ? '处理中…' : (isLogin ? '登录' : '注册') }}
        </button>
      </form>

      <div class="auth-switch">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <a href="#" @click.prevent="isLogin = !isLogin">
          {{ isLogin ? '立即注册' : '去登录' }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import authStore from '../stores/auth.js'

const emit = defineEmits(['close', 'success'])

const isLogin = ref(true)
const form = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
})

async function handleSubmit() {
  authStore.state.error = null
  let success = false

  if (isLogin.value) {
    success = await authStore.login(form.username, form.password)
  } else {
    success = await authStore.register(
      form.username,
      form.email,
      form.password,
      form.full_name
    )
  }

  if (success) {
    emit('success')
    emit('close')
  }
}
</script>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.auth-modal {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  width: 380px;
  max-width: 90vw;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.auth-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.auth-header h2 {
  margin: 0;
  color: #c9d1d9;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  color: #8b949e;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}
.close-btn:hover {
  color: #f85149;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #8b949e;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #30363d;
  border-radius: 6px;
  background: #0d1117;
  color: #c9d1d9;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
}
.form-group input:focus {
  border-color: #58a6ff;
}

.error-msg {
  padding: 10px 12px;
  background: #da363322;
  border: 1px solid #da3633;
  border-radius: 6px;
  color: #f85149;
  font-size: 13px;
  margin-bottom: 16px;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: #238636;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.submit-btn:hover:not(:disabled) {
  background: #2ea043;
}
.submit-btn:disabled {
  background: #30363d;
  cursor: not-allowed;
}

.auth-switch {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: #8b949e;
}
.auth-switch a {
  color: #58a6ff;
  text-decoration: none;
}
.auth-switch a:hover {
  text-decoration: underline;
}
</style>
