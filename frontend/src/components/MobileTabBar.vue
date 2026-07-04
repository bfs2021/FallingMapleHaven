<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const authStore = useAuthStore()

const tabs = computed(() => {
  const items = [
    { name: '首页', path: '/', icon: 'home' },
    { name: '群组', path: '/groups', icon: 'users' },
    { name: '插件', path: '/plugins', icon: 'puzzle' },
    { name: '聊天', path: '/chat', icon: 'messageCircle' },
    { name: '好友', path: '/friends', icon: 'userPlus' },
    { name: '通知', path: '/notifications', icon: 'bell' },
    { name: '我的', path: authStore.user?.user_id ? `/profile/${authStore.user.user_id}` : '/login', icon: 'user' },
  ]
  if (authStore.isAdmin) {
    items.push({ name: '后台', path: '/admin', icon: 'shield' })
  }
  return items
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <nav v-if="authStore.isAuthenticated" class="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-maple-100 z-50 safe-area-bottom">
    <div class="flex items-center justify-around py-1">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="tab.path"
        class="flex flex-col items-center gap-0.5 text-xs relative py-1 min-w-[48px] min-h-[44px] justify-center"
        :class="isActive(tab.path) ? 'text-maple-600' : 'text-text-secondary'"
      >
        <Icon :name="tab.icon" :size="20" />
        <span class="text-[10px] leading-none">{{ tab.name }}</span>
        <span
          v-if="tab.name === '通知' && authStore.user?.unread_count"
          class="absolute -top-0.5 -right-1 bg-red-500 text-white text-[10px] rounded-full min-w-[16px] h-4 flex items-center justify-center px-1"
        >
          {{ authStore.user.unread_count > 99 ? '99+' : authStore.user.unread_count }}
        </span>
      </RouterLink>
    </div>
  </nav>
</template>
