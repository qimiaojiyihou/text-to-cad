import { reactive, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const state = reactive({
  token: localStorage.getItem('admin_token') || null,
  refreshToken: localStorage.getItem('admin_refresh_token') || null,
  user: JSON.parse(localStorage.getItem('admin_user') || 'null'),
})

export function useAuthStore() {
  const isLoggedIn = computed(() => !!state.token)
  const isAdmin = computed(() => state.user?.is_superuser === true)

  async function login(username, password) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login/json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '登录失败')

    state.token = data.access_token
    state.refreshToken = data.refresh_token
    localStorage.setItem('admin_token', data.access_token)
    localStorage.setItem('admin_refresh_token', data.refresh_token)

    await fetchUser()
    return true
  }

  async function fetchUser() {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${state.token}` },
    })
    if (!res.ok) {
      logout()
      throw new Error('获取用户信息失败')
    }
    state.user = await res.json()
    localStorage.setItem('admin_user', JSON.stringify(state.user))
  }

  async function refreshAccessToken() {
    if (!state.refreshToken) {
      logout()
      throw new Error('无刷新令牌')
    }
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    })
    const data = await res.json()
    if (!res.ok) {
      logout()
      throw new Error(data.detail || '刷新令牌失败')
    }
    state.token = data.access_token
    localStorage.setItem('admin_token', data.access_token)
    return data.access_token
  }

  function logout() {
    state.token = null
    state.refreshToken = null
    state.user = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    localStorage.removeItem('admin_user')
  }

  return {
    state,
    isLoggedIn,
    isAdmin,
    login,
    logout,
    fetchUser,
    refreshAccessToken,
  }
}

export async function apiFetch(path, options = {}) {
  const token = state.token
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  }
  if (options.body && typeof options.body === 'string') {
    headers['Content-Type'] = 'application/json'
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401 && state.refreshToken) {
    try {
      const newToken = await useAuthStore().refreshAccessToken()
      headers.Authorization = `Bearer ${newToken}`
      res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    } catch {
      window.location.href = '/admin-static/login'
      throw new Error('登录已过期')
    }
  }

  return res
}
