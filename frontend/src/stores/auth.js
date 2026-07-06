import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

let sessionInitPromise = null

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    loading: false,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => !!state.user,
    isAdmin: (state) => state.user?.is_admin || false,
    userId: (state) => state.user?.user_id,
  },
  actions: {
    async login(username, password) {
      this.loading = true
      try {
        const res = await authApi.login({ username, password })
        this.user = res.data
        this.initialized = true
      } finally { this.loading = false }
    },
    async fetchMe() {
      this.loading = true
      try {
        const res = await authApi.me()
        this.user = res.data
      } catch { this.user = null }
      finally {
        this.initialized = true
        this.loading = false
      }
    },
    async ensureSession() {
      if (this.initialized) return
      if (!sessionInitPromise) {
        sessionInitPromise = this.fetchMe()
      }
      try {
        await sessionInitPromise
      } catch {
      } finally {
        sessionInitPromise = null
      }
    },
    async logout() {
      try {
        await authApi.logout()
      } catch {
        // 即使 API 调用失败也清除本地状态，避免 401 死循环
      }
      this.user = null
      this.initialized = true
    },
    async register(data) {
      this.loading = true
      try {
        const res = await authApi.register(data)
        this.user = res.data
        this.initialized = true
      } finally {
        this.loading = false
      }
    },
    async updateProfile(data) {
      const res = await authApi.updateMe(data)
      this.user = { ...this.user, ...res.data }
    },
    setUnreadCount(count) {
      if (!this.user) return
      this.user = { ...this.user, unread_count: count }
    },
  },
})
