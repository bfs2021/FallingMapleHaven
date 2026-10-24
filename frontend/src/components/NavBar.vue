<script setup>
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Icon from '@/components/Icon.vue'

const authStore = useAuthStore()
</script>

<template>
  <nav class="hidden md:flex bg-maple-600 text-white px-6 py-3 items-center justify-between shadow-float">
    <div class="flex items-center gap-8">
      <RouterLink to="/" class="flex items-center justify-center w-9 h-9 bg-white/20 rounded-lg text-lg font-bold tracking-wide hover:bg-white/30 transition-colors">枫</RouterLink>
      <div v-if="authStore.isAuthenticated" class="flex gap-6 text-sm font-medium">
        <RouterLink to="/" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="home" :size="16" /> 首页
        </RouterLink>
        <RouterLink to="/groups" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="users" :size="16" /> 群组
        </RouterLink>
        <RouterLink to="/plugins" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="puzzle" :size="16" /> 插件
        </RouterLink>
        <RouterLink to="/friends" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="userPlus" :size="16" /> 好友
        </RouterLink>
        <RouterLink to="/chat" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="messageCircle" :size="16" /> 聊天
        </RouterLink>
        <RouterLink to="/notifications" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors relative">
          <Icon name="bell" :size="16" /> 通知
          <span v-if="authStore.user?.unread_count" class="absolute -top-1.5 -right-4 bg-error-500 text-white text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {{ authStore.user.unread_count > 99 ? '99+' : authStore.user.unread_count }}
          </span>
        </RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="shield" :size="16" /> 管理
        </RouterLink>
      </div>
      <div v-else class="flex gap-6 text-sm font-medium">
        <RouterLink to="/" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="globe" :size="16" /> 广场
        </RouterLink>
        <RouterLink to="/groups" class="flex items-center gap-1.5 hover:text-maple-200 transition-colors">
          <Icon name="users" :size="16" /> 群组
        </RouterLink>
      </div>
    </div>
    <RouterLink
      v-if="authStore.isAuthenticated"
      :to="`/profile/${authStore.user?.user_id}`"
      class="flex items-center gap-2 hover:text-maple-200 transition-all duration-150 active:scale-[0.97] min-h-[44px]"
    >
      <div class="w-8 h-8 rounded-full bg-maple-400 overflow-hidden flex items-center justify-center text-sm font-bold flex-shrink-0">
        <img v-if="authStore.user?.avatar_url" :src="authStore.user.avatar_url" class="w-full h-full object-cover" />
        <span v-else>{{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}</span>
      </div>
      <span class="text-sm max-w-[120px] truncate">{{ authStore.user?.nickname || authStore.user?.username }}</span>
    </RouterLink>
    <div v-else class="flex items-center gap-3">
      <RouterLink to="/login" class="flex items-center gap-1.5 text-sm hover:text-maple-200 transition-colors px-3 py-1.5 min-h-[44px]">登录</RouterLink>
      <RouterLink to="/register" class="flex items-center gap-1.5 text-sm bg-white text-maple-600 px-4 py-1.5 rounded-lg font-medium hover:bg-maple-50 transition-colors min-h-[44px]">注册</RouterLink>
    </div>
  </nav>
</template>

