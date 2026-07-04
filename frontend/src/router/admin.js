import { pluginRegistry } from '@/plugins/registry'

const builtinChildren = [
  { path: '', name: 'AdminStats', component: () => import('@/views/admin/AdminStatsPage.vue') },
  { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/AdminUsersPage.vue') },
  { path: 'posts', name: 'AdminPosts', component: () => import('@/views/admin/AdminPostsPage.vue') },
  { path: 'groups', name: 'AdminGroups', component: () => import('@/views/admin/AdminGroupsPage.vue') },
  { path: 'plugins', name: 'AdminPlugins', component: () => import('@/views/admin/AdminPluginsPage.vue') },
  { path: 'settings', name: 'AdminSettings', component: () => import('@/views/admin/AdminSettingsPage.vue') },
  { path: 'logs', name: 'AdminLogs', component: () => import('@/views/admin/AdminLogsPage.vue') },
]

const pluginChildren = pluginRegistry.getAdminRoutes()

export default [
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [...builtinChildren, ...pluginChildren],
  },
]
