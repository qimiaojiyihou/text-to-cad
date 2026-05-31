import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../views/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
      },
      {
        path: 'users',
        name: 'UserList',
        component: () => import('../views/UserList.vue'),
      },
      {
        path: 'users/:id',
        name: 'UserDetail',
        component: () => import('../views/UserDetail.vue'),
      },
      {
        path: 'records',
        name: 'RecordList',
        component: () => import('../views/RecordList.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory('/admin-static/'),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    next()
    return
  }

  if (!auth.isLoggedIn) {
    next('/login')
    return
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    next('/login')
    return
  }

  next()
})

export default router
