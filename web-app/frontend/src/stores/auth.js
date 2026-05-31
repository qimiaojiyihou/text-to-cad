import { reactive, readonly } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const state = reactive({
  user: null,
  accessToken: localStorage.getItem('access_token') || null,
  refreshToken: localStorage.getItem('refresh_token') || null,
  isLoading: false,
  error: null,
})

function setTokens(access, refresh) {
  state.accessToken = access
  state.refreshToken = refresh
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

function clearTokens() {
  state.accessToken = null
  state.refreshToken = null
  state.user = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

async function fetchWithAuth(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
  }
  if (state.accessToken) {
    headers['Authorization'] = `Bearer ${state.accessToken}`
  }

  let res = await fetch(url, { ...options, headers })

  // Token 过期，尝试刷新
  if (res.status === 401 && state.refreshToken) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${state.accessToken}`
      res = await fetch(url, { ...options, headers })
    }
  }

  return res
}

async function refreshAccessToken() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    })
    if (res.ok) {
      const data = await res.json()
      setTokens(data.access_token, data.refresh_token)
      return true
    }
  } catch (e) {
    console.error('Refresh token failed:', e)
  }
  clearTokens()
  return false
}

async function login(username, password) {
  state.isLoading = true
  state.error = null
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login/json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await res.json()
    if (!res.ok) {
      state.error = data.detail || '登录失败'
      return false
    }
    setTokens(data.access_token, data.refresh_token)
    await fetchUser()
    return true
  } catch (e) {
    state.error = '网络错误: ' + e.message
    return false
  } finally {
    state.isLoading = false
  }
}

async function register(username, email, password, fullName = '') {
  state.isLoading = true
  state.error = null
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        email,
        password,
        full_name: fullName || null,
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      state.error = data.detail || '注册失败'
      return false
    }
    // 注册成功后自动登录
    return await login(username, password)
  } catch (e) {
    state.error = '网络错误: ' + e.message
    return false
  } finally {
    state.isLoading = false
  }
}

async function fetchUser() {
  if (!state.accessToken) return
  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/auth/me`)
    if (res.ok) {
      state.user = await res.json()
    } else if (res.status === 401) {
      clearTokens()
    }
  } catch (e) {
    console.error('Fetch user failed:', e)
  }
}

function logout() {
  clearTokens()
}

// 初始化时尝试获取用户信息
fetchUser()

export default {
  state: readonly(state),
  login,
  register,
  logout,
  fetchUser,
  fetchWithAuth,
}
