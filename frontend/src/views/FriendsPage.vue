<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useFriendStore } from '@/stores/friend'
import { friendApi } from '@/api/friends'
import { chatApi } from '@/api/chat'
import FriendButton from '@/components/FriendButton.vue'
import AvatarImage from '@/components/AvatarImage.vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const friendStore = useFriendStore()
const toast = useToast()

const activeTab = ref('list')
const searchQuery = ref('')
const debouncedQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const friendStatuses = ref({})
let searchTimer = null

const tabs = [
  { key: 'list', label: '好友列表' },
  { key: 'requests', label: '收到的申请' },
  { key: 'search', label: '搜索用户' },
]

onMounted(async () => {
  friendStore.loading = true
  try {
    await Promise.all([friendStore.fetchFriends(), friendStore.fetchRequests()])
  } finally {
    friendStore.loading = false
  }
})

watch(searchQuery, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!val.trim()) {
    debouncedQuery.value = ''
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(() => {
    debouncedQuery.value = val.trim()
  }, 350)
})

watch(debouncedQuery, async (val) => {
  if (!val) return
  searchLoading.value = true
  try {
    const res = await friendApi.search(val)
    searchResults.value = res.data || []
  } catch {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

function onStatusChanged(userId, newStatus) {
  friendStatuses.value[userId] = newStatus
  if (activeTab.value === 'requests') {
    friendStore.fetchRequests()
  }
  if (activeTab.value === 'list') {
    friendStore.fetchFriends()
  }
}

function getStatus(user) {
  return friendStatuses.value[user.user_id || user.id] || user.friend_status || 'none'
}

async function goToChat(friend) {
  const friendId = friend.user_id || friend.id
  if (!friendId) return
  const res = await chatApi.createRoom({ type: 'private', member_ids: [friendId] })
  if (res.data?.id) {
    router.push(`/chat/${res.data.id}`)
  }
}

function goToProfile(user) {
  router.push(`/profile/${user.user_id || user.id}`)
}
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">好友</h1>

    <div class="tab-nav mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="activeTab = tab.key"
        class="tab-btn min-h-[40px]"
        :class="activeTab === tab.key ? 'tab-btn-active' : 'tab-btn-inactive'"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="friendStore.loading" class="text-center text-text-secondary py-12">加载中...</div>

    <template v-if="!friendStore.loading && activeTab === 'list'">
      <EmptyState v-if="!friendStore.friends.length" icon="userPlus" title="还没有好友" description="搜索用户名或昵称，发出第一份好友申请">
        <button
          @click="activeTab = 'search'"
          class="btn-primary px-4"
        >
          去搜索添加
        </button>
      </EmptyState>
      <div v-else class="space-y-3">
        <div
          v-for="friend in friendStore.friends"
          :key="friend.id"
          class="card-base p-4 flex items-center gap-4"
        >
          <AvatarImage :user="friend" size="lg" clickable @click="goToProfile(friend)" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary truncate cursor-pointer hover:text-maple-600" @click="goToProfile(friend)">
              {{ friend.nickname || friend.username }}
            </p>
          </div>
          <button
            @click="goToChat(friend)"
            class="px-3 py-1 bg-maple-50 text-maple-600 text-xs rounded-lg hover:bg-maple-100 transition-colors cursor-pointer"
          >
            发消息
          </button>
        </div>
      </div>
    </template>

    <template v-if="!friendStore.loading && activeTab === 'requests'">
      <EmptyState v-if="!friendStore.requests.length" icon="mail" title="暂无好友申请" />
      <div v-else class="space-y-3">
        <div
          v-for="req in friendStore.requests"
          :key="req.id"
          class="card-base p-4 flex items-center gap-4"
        >
          <AvatarImage :user="req.from_user" size="lg" clickable @click="goToProfile(req.from_user)" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary truncate cursor-pointer hover:text-maple-600" @click="goToProfile(req.from_user)">
              {{ req.from_user?.nickname || req.from_user?.username }}
            </p>
          </div>
          <div class="flex gap-2">
            <button
              @click="friendStore.handleRequest(req.id, 'accept').then(() => friendStore.fetchRequests())"
              class="btn-primary px-3 text-xs"
            >
              同意
            </button>
            <button
              @click="friendStore.handleRequest(req.id, 'reject').then(() => friendStore.fetchRequests())"
              class="px-3 py-1 bg-gray-200 text-text-secondary text-xs rounded-lg hover:bg-gray-300 transition-colors cursor-pointer"
            >
              拒绝
            </button>
          </div>
        </div>
      </div>
    </template>

    <template v-if="activeTab === 'search'">
      <div class="relative mb-4">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索用户..."
          class="input-base"
        />
        <span v-if="searchLoading" class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-secondary">搜索中...</span>
      </div>
      <EmptyState v-if="!searchQuery.trim()" icon="search" title="搜索用户" description="输入用户名或昵称" />
      <EmptyState v-else-if="!searchResults.length && !searchLoading" icon="search" title="未找到相关用户" description="换个关键词试试" />
      <div v-else class="space-y-3">
        <div
          v-for="user in searchResults"
          :key="user.user_id || user.id"
          class="card-base p-4 flex items-center gap-4"
        >
          <AvatarImage :user="user" size="lg" clickable @click="goToProfile(user)" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary truncate cursor-pointer hover:text-maple-600" @click="goToProfile(user)">
              {{ user.nickname || user.username }}
            </p>
          </div>
          <FriendButton
            :userId="user.user_id || user.id"
            :friendStatus="getStatus(user)"
            @status-changed="(s) => onStatusChanged(user.user_id || user.id, s)"
          />
        </div>
      </div>
    </template>
  </div>
</template>
