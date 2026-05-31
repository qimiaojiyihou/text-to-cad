import { createRouter, createWebHistory } from 'vue-router'
import authStore from '../stores/auth.js'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  if (authStore.state.accessToken && !authStore.state.user) {
    await authStore.fetchUser()
  }
  if (to.meta.requiresAuth && !authStore.state.user) {
    next('/')
    return
  }
  next()
})

export default router
