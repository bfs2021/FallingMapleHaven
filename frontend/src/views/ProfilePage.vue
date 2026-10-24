<script setup>
import { ref, onMounted, computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { profileApi } from '@/api/profiles'
import { pluginApi } from '@/api/plugin'
import { useConfirm } from '@/composables/useConfirm'
import { relativeTime } from '@/utils/time'
import PostCard from '@/components/PostCard.vue'
import FriendButton from '@/components/FriendButton.vue'
import PluginEntryGrid from '@/components/PluginEntryGrid.vue'
import AvatarImage from '@/components/AvatarImage.vue'
import Icon from '@/components/Icon.vue'
import TabBar from '@/components/TabBar.vue'

const { confirm: confirmAction } = useConfirm()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const profile = ref(null)
const loading = ref(true)
const activeTab = ref('posts')
const posts = ref([])
const visitors = ref([])
const postsLoading = ref(false)

const userId = computed(() => {
  const raw = route.params.userId
  const num = Number(raw)
  return isNaN(num) ? raw : num
})
const isGuest = computed(() => !authStore.isAuthenticated)
const isOwner = computed(() => authStore.user?.user_id === userId.value)

const layoutConfig = computed(() => {
  if (!authStore.isAuthenticated) {
    return { show_plugin_area: true, show_visitors: true }
  }
  return {
    show_plugin_area: true,
    show_visitors: true,
    ...(authStore.user?.layout_config || {}),
  }
})

const tabs = computed(() => {
  const items = [
    { key: 'posts', label: '动态' },
  ]
  if (!isGuest.value && layoutConfig.value.show_visitors) {
    items.push({ key: 'visitors', label: '访客' })
  }
  return items
})

const pluginCards = ref([])

onMounted(async () => {
  await Promise.all([fetchProfile(), fetchPosts(), fetchPluginCards()])
})

async function fetchProfile() {
  loading.value = true
  try {
    const res = await profileApi.get(userId.value)
    profile.value = res.data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function fetchPosts() {
  postsLoading.value = true
  try {
    const res = await profileApi.posts(userId.value, { page: 1, page_size: 20 })
    posts.value = res.data?.results || []
  } catch { /* ignore */ } finally {
    postsLoading.value = false
  }
}

async function fetchVisitors() {
  if (visitors.value.length) return
  try {
    const res = await profileApi.visitors(userId.value, { page: 1, page_size: 20 })
    visitors.value = res.data?.results || []
  } catch { /* ignore */ }
}

async function fetchPluginCards() {
  try {
    const res = await pluginApi.getProfileCards(userId.value)
    pluginCards.value = res.data || []
  } catch {
    const cards = (profile.value?.plugins || []).map(p => ({
      type: p.type,
      name: p.name,
      icon: p.icon || 'helpCircle',
      desc: p.description,
      data: p.data,
      route: p.route,
    }))
    cards.push({
      type: 'guestbook',
      name: '留言板',
      icon: 'messageSquare',
      desc: '给我留言',
      data: { total_messages: 0 },
      route: `/profile/${userId.value}/guestbook`,
    })
    pluginCards.value = cards
  }
}

function onTabChange(tab) {
  activeTab.value = tab
}

function goToPlugin(plugin) {
  const publicPlugins = new Set(['quiz', 'relation_match', 'guestbook'])
  router.push(authStore.isAuthenticated || publicPlugins.has(plugin.type) ? plugin.route : `/login?next=${plugin.route}`)
}

const showAdminPanel = ref(false)
const adminInfo = ref(null)

async function toggleAdminPanel() {
  if (showAdminPanel.value) {
    showAdminPanel.value = false
    return
  }
  try {
    const res = await profileApi.getAdminInfo(userId.value)
    adminInfo.value = res.data
    showAdminPanel.value = true
  } catch { /* ignore */ }
}

async function toggleUserBan() {
  if (!adminInfo.value) return
  const action = adminInfo.value.is_active ? '封禁' : '解封'
  if (!await confirmAction({ title: `${action}用户`, message: `确认${action}此用户？此操作${action === '封禁' ? '后用户将无法登录' : '后用户可正常登录'}。`, variant: action === '封禁' ? 'danger' : 'default', confirmText: action })) return
  try {
    const res = await profileApi.banUser(userId.value, !adminInfo.value.is_active)
    adminInfo.value = res.data
  } catch { /* ignore */ }
}

function onFriendStatusChanged(status) {
  if (profile.value) profile.value.friend_status = status
}

async function handleLogout() {
  await authStore.logout()
  router.push('/')
}
</script>

<template>
  <div v-if="loading" class="page-container">
    <div class="space-y-4 animate-fade-in">
      <div class="h-48 skeleton rounded-b-2xl" />
      <div class="flex items-end gap-4 px-4 -mt-16">
        <div class="w-24 h-24 rounded-full border-4 border-white skeleton" />
        <div class="flex-1 space-y-2 pb-2">
          <div class="h-5 w-32 skeleton" />
          <div class="h-3 w-48 skeleton" />
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="profile" class="max-w-4xl mx-auto px-4 pb-8">
    <div class="relative w-full rounded-b-2xl overflow-hidden" style="aspect-ratio: 3/1">
      <img v-if="profile.cover_url" :src="profile.cover_url" class="w-full h-full object-cover" />
      <div v-else class="w-full h-full bg-gradient-to-r from-maple-600 to-maple-400" />
    </div>

    <div class="relative px-4 -mt-12 z-10">
      <div class="flex items-end gap-4">
        <div class="rounded-full border-4 border-white flex-shrink-0 shadow-float overflow-hidden">
          <AvatarImage :user="profile" size="2xl" />
        </div>
        <div class="flex-1 min-w-0 pb-1">
          <h1 class="text-lg font-bold text-text-primary truncate">{{ profile.nickname || profile.username }}</h1>
          <p v-if="profile.bio" class="text-aux text-text-secondary mt-0.5 truncate">{{ profile.bio }}</p>
          <p v-if="profile.show_real_name && profile.real_name" class="text-aux text-text-secondary mt-0.5">真实姓名: {{ profile.real_name }}</p>
        </div>
      </div>

      <div class="flex items-center gap-4 mt-3">
        <span class="text-sm text-text-secondary flex items-center gap-1.5">
          <Icon name="user" :size="14" /> {{ profile.visitor_count || 0 }} 次访问
        </span>
          <FriendButton
            v-if="!isGuest"
            :userId="userId"
            :friendStatus="profile.friend_status || 'none'"
            @status-changed="onFriendStatusChanged"
          />
          <div v-if="isOwner" class="flex items-center gap-2 ml-auto">
            <RouterLink
              to="/settings"
              class="flex items-center justify-center w-10 h-10 rounded-lg border border-border text-text-secondary hover:bg-maple-50 hover:text-maple-600 transition-colors active:scale-[0.97]"
              title="个人设置"
            >
              <Icon name="settings" :size="18" />
            </RouterLink>
            <button
              @click="handleLogout"
              class="flex items-center justify-center w-10 h-10 rounded-lg border border-border text-red-400 hover:bg-red-50 hover:text-red-500 transition-colors active:scale-[0.97]"
              title="退出登录"
            >
              <Icon name="logOut" :size="18" />
            </button>
          </div>
        </div>
      </div>

    <div v-if="authStore.isAdmin && userId !== authStore.user?.user_id" class="px-4 mt-4">
      <button
        @click="toggleAdminPanel"
        class="text-sm text-red-600 border border-red-300 px-3 py-2 rounded hover:bg-red-50"
      >
        {{ showAdminPanel ? '收起管理面板' : '⚙ 管理用户' }}
      </button>

      <div v-if="showAdminPanel && adminInfo" class="mt-2 p-3 bg-red-50 rounded border border-red-200 text-sm">
        <h4 class="font-medium text-red-800 mb-2">用户管理</h4>
        <div class="grid grid-cols-2 gap-2 text-gray-700">
          <div>用户名: {{ adminInfo.username }}</div>
          <div>昵称: {{ adminInfo.nickname }}</div>
          <div>邮箱: {{ adminInfo.email || '(未设置)' }}</div>
          <div>状态: {{ adminInfo.is_active ? '正常' : '已封禁' }}</div>
          <div>注册时间: {{ adminInfo.date_joined }}</div>
          <div>最后登录: {{ adminInfo.last_login || '(从未)' }}</div>
        </div>
        <button
          @click="toggleUserBan"
          class="mt-2 px-3 py-2 rounded text-white text-xs"
          :class="adminInfo.is_active ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'"
        >
          {{ adminInfo.is_active ? '封禁此用户' : '解封此用户' }}
        </button>
      </div>
    </div>

    <div v-if="layoutConfig.show_plugin_area" class="px-4 mt-6">
      <PluginEntryGrid :plugins="pluginCards" @navigate="goToPlugin" />
    </div>

    <div class="px-4 mt-6">
      <TabBar :tabs="tabs" :activeKey="activeTab" @update:activeKey="onTabChange" />

      <div v-if="activeTab === 'posts'" class="mt-4 space-y-4 animate-fade-in">
        <div v-if="postsLoading" class="space-y-4">
          <div v-for="i in 2" :key="i" class="card-base p-5 space-y-3">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full skeleton" />
              <div class="space-y-2 flex-1">
                <div class="h-3 w-24 skeleton" />
                <div class="h-2.5 w-16 skeleton" />
              </div>
            </div>
            <div class="h-3 w-full skeleton" />
            <div class="h-3 w-2/3 skeleton" />
          </div>
        </div>
        <template v-else-if="posts.length">
          <PostCard v-for="post in posts" :key="post.id" :post="post" :showActions="false" />
        </template>
        <div v-else class="text-center py-12 text-text-secondary">
          <Icon name="fileText" :size="40" class="mx-auto mb-2 text-maple-300" />
          <p>暂无动态</p>
        </div>
      </div>

      <div v-if="activeTab === 'visitors'" class="mt-4 space-y-3 animate-fade-in">
        <div v-if="!visitors.length" class="text-center py-12 text-text-secondary">
          <Icon name="users" :size="40" class="mx-auto mb-2 text-maple-300" />
          <p>暂无访客记录</p>
        </div>
        <div
          v-for="visitor in visitors"
          :key="visitor.id || visitor.user_id"
          class="flex items-center gap-3 py-2.5 border-b border-border last:border-0"
        >
          <AvatarImage :user="visitor" size="md" clickable @click="router.push(`/profile/${visitor.user_id}`)" />
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium text-text-primary truncate cursor-pointer hover:text-maple-600 transition-colors" @click="router.push(`/profile/${visitor.user_id}`)">
              {{ visitor.nickname || visitor.username }}
            </span>
          </div>
          <span class="text-xs text-text-secondary flex-shrink-0">{{ relativeTime(visitor.visited_at) }}</span>
        </div>
      </div>

    </div>
  </div>

  <div v-else class="page-container text-center">
    <Icon name="alertCircle" :size="48" class="mx-auto mb-3 text-maple-300" />
    <p class="text-text-secondary">用户不存在</p>
  </div>
</template>

<style scoped>
</style>
