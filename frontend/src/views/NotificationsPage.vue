<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { notificationApi } from '@/api/notifications'
import { relativeTime } from '@/utils/time'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const authStore = useAuthStore()

const notifications = ref([])
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)
const pollingInterval = ref(null)

const POLL_INTERVAL = 30000

onMounted(() => {
  fetchNotifications(true)
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

function startPolling() {
  pollingInterval.value = setInterval(() => {
    fetchUnreadCount()
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

async function fetchUnreadCount() {
  try {
    const countRes = await notificationApi.unreadCount()
    authStore.setUnreadCount(countRes.data?.count || 0)
  } catch { /* ignore */ }
}

async function fetchNotifications(reset = false) {
  if (loading.value) return
  loading.value = true
  try {
    if (reset) page.value = 1
    const res = await notificationApi.list({ page: page.value, page_size: 20 })
    const raw = res.data?.results ?? res.data
    const results = Array.isArray(raw) ? raw : []
    if (reset) {
      notifications.value = results
    } else {
      notifications.value.push(...results)
    }
    if (res.data) {
      hasMore.value = res.data.page * res.data.page_size < res.data.total
    } else {
      hasMore.value = false
    }
    page.value += 1
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function markRead(n) {
  if (n.is_read) return
  try {
    await notificationApi.read(n.id)
    n.is_read = true
    const current = authStore.user?.unread_count || 0
    authStore.setUnreadCount(Math.max(0, current - 1))
  } catch { /* ignore */ }
}

async function markAllRead() {
  try {
    await notificationApi.readAll()
    notifications.value.forEach(n => n.is_read = true)
    authStore.setUnreadCount(0)
  } catch { /* ignore */ }
}

function handleNotificationClick(n) {
  markRead(n)
  if (n.link && n.link !== '#') {
    router.push(n.link)
  }
}

function notificationIcon(type) {
  const icons = { like: 'heart', comment: 'messageCircle', reply: 'messageSquare', friend_request: 'userPlus', friend_accepted: 'userCheck', system: 'bell', quiz_invite: 'helpCircle', plugin_event: 'puzzle', anonymous_question: 'messageSquare', group_join_request: 'userPlus', group_request_approved: 'userCheck', group_request_rejected: 'xCircle', group_member_joined: 'users', group_new_post: 'messageCircle' }
  return icons[type] || 'bell'
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="page-title mb-0">通知</h1>
      <button
        v-if="notifications.some(n => !n.is_read)"
        @click="markAllRead"
        class="btn-ghost px-3 py-1.5 text-sm"
      >
        <Icon name="check" :size="14" /> 全部标为已读
      </button>
    </div>

    <div v-if="loading && !notifications.length" class="space-y-2">
      <div v-for="i in 5" :key="i" class="card-base p-4 flex items-center gap-3">
        <div class="w-10 h-10 rounded-full skeleton" />
        <div class="flex-1 space-y-2">
          <div class="h-3 w-3/4 skeleton" />
          <div class="h-2.5 w-1/2 skeleton" />
        </div>
      </div>
    </div>

    <div v-else-if="!notifications.length" class="text-center py-16 text-text-secondary">
      <Icon name="bell" :size="48" class="mx-auto mb-3 text-maple-300" />
      <p>暂无通知</p>
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="n in notifications"
        :key="n.id"
        @click="handleNotificationClick(n)"
        class="flex items-center gap-3 p-4 transition-all duration-200"
        :class="n.is_read
          ? 'bg-maple-50/30 border border-maple-100/50 rounded-2xl cursor-default'
          : 'card-base cursor-pointer border-l-[3px] border-l-maple-500'"
      >
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
          :class="n.is_read ? 'bg-maple-100/50' : 'bg-maple-100'"
        >
          <Icon :name="notificationIcon(n.notification_type)" :size="18" :class="n.is_read ? 'text-maple-400' : 'text-maple-600'" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm" :class="n.is_read ? 'text-text-secondary' : 'text-text-primary font-semibold'">
            {{ n.title }}
          </p>
          <p v-if="n.content" class="text-xs text-text-secondary mt-1">{{ n.content }}</p>
          <p class="text-xs text-text-tertiary mt-1">{{ relativeTime(n.created_at) }}</p>
        </div>
        <span v-if="!n.is_read" class="w-2 h-2 rounded-full bg-maple-500 flex-shrink-0" />
      </div>

      <button
        v-if="hasMore"
        @click="fetchNotifications(false)"
        :disabled="loading"
        class="btn-ghost w-full justify-center py-3"
      >
        <Icon name="chevronDown" :size="14" />
        {{ loading ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>
