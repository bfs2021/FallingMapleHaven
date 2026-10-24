<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center px-4">
    <div class="text-center space-y-4">
      <p class="text-5xl font-bold text-maple-600">404</p>
      <h1 class="text-xl font-semibold text-text-primary">页面不存在</h1>
      <p class="text-sm text-text-secondary">当前地址没有对应页面。</p>
      <div class="flex items-center justify-center gap-3">
        <button
          @click="router.push(authStore.isAuthenticated ? '/' : '/login')"
          class="btn-primary px-4"
        >
          {{ authStore.isAuthenticated ? '回到首页' : '去登录' }}
        </button>
        <button
          @click="router.back()"
          class="btn-secondary px-4"
        >
          返回上一页
        </button>
      </div>
    </div>
  </div>
</template>
