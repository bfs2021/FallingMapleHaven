import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import adminRoutes from './admin'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/profile/:userId',
    name: 'Profile',
    component: () => import('@/views/ProfilePage.vue'),
  },
  {
    path: '/profile/:userId/plugins/quiz',
    name: 'QuizPage',
    component: () => import('@/views/QuizPage.vue'),
  },
  {
    path: '/profile/:userId/plugins/quiz/tests/:testId',
    name: 'QuizTestDetail',
    component: () => import('@/views/QuizPage.vue'),
  },
  {
    path: '/profile/:userId/plugins/quiz/tests/:testId/edit',
    name: 'QuizTestEditor',
    component: () => import('@/views/QuizTestEditorPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/profile/:userId/plugins/quiz/tests/:testId/leaderboard',
    name: 'QuizTestLeaderboard',
    component: () => import('@/views/QuizPage.vue'),
  },
  {
    path: '/profile/:userId/plugins/question-box',
    name: 'QuestionBox',
    component: () => import('@/views/QuestionBoxPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/profile/:userId/guestbook',
    name: 'Guestbook',
    component: () => import('@/views/GuestbookPage.vue'),
  },
  {
    path: '/friends',
    name: 'Friends',
    component: () => import('@/views/FriendsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/plugins',
    name: 'Plugins',
    component: () => import('@/views/PluginsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat',
    name: 'ChatList',
    component: () => import('@/views/ChatListPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat/:roomId',
    name: 'ChatRoom',
    component: () => import('@/views/ChatRoomPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/groups',
    name: 'GroupList',
    component: () => import('@/views/GroupListPage.vue'),
  },
  {
    path: '/groups/:groupId',
    name: 'GroupDetail',
    component: () => import('@/views/GroupDetailPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/modules',
    name: 'SettingsModules',
    component: () => import('@/views/SettingsModulesPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/views/NotificationsPage.vue'),
    meta: { requiresAuth: true },
  },
  ...adminRoutes,
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authStore.initialized) {
    await authStore.ensureSession()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login', query: { next: to.fullPath } }
  }
  if (to.meta.guest && authStore.isAuthenticated) {
    return { name: 'Home' }
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { name: 'Home' }
  }
  return true
})

export default router
