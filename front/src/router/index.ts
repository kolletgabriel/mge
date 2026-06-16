import { createRouter, createWebHistory } from 'vue-router'

import { ensureCurrentUser } from '@/auth'
import AuthView from '@/views/AuthView.vue'
import DashboardView from '@/views/DashboardView.vue'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/entrar',
      name: 'auth',
      component: AuthView,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboards',
      name: 'dashboards',
      component: DashboardView,
      meta: { requiresAuth: true, requiresDashboardAccess: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const user = await ensureCurrentUser()

  if (to.meta.requiresAuth && !user) {
    return { name: 'auth' }
  }

  if (to.meta.guestOnly && user) {
    return { name: 'home' }
  }

  if (to.meta.requiresDashboardAccess && user?.role_id === 1) {
    return { name: 'home' }
  }

  return true
})

export default router
