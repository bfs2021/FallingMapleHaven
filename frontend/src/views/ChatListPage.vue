<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { relativeTime } from '@/utils/time'
import AvatarImage from '@/components/AvatarImage.vue'

const router = useRouter()
const chatStore = useChatStore()
const loading = ref(true)

const sortedRooms = computed(() => {
  return [...chatStore.rooms].sort((a, b) => {
    const aTime = new Date(a.last_message_at || 0).getTime()
    const bTime = new Date(b.last_message_at || 0).getTime()
    return bTime - aTime
  })
})

onMounted(async () => {
  await chatStore.fetchRooms()
  loading.value = false
})

function enterRoom(room) {
  router.push(`/chat/${room.id}`)
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="page-title">消息</h1>

    <div v-if="loading" class="text-center text-text-secondary py-12">加载中...</div>

    <div v-else-if="!sortedRooms.length" class="text-center text-text-secondary py-12">
      <p class="mb-3">暂无聊天</p>
      <button
        @click="router.push('/friends')"
        class="btn-primary px-4"
      >
        去找好友
      </button>
    </div>

    <div v-else class="bg-white rounded-2xl border border-border shadow-card divide-y divide-border overflow-hidden">
      <div
        v-for="room in sortedRooms"
        :key="room.id"
        @click="enterRoom(room)"
        class="flex items-center gap-3 px-5 py-4 hover:bg-maple-50 transition-colors cursor-pointer"
      >
        <div class="relative flex-shrink-0">
          <AvatarImage :user="room.other_user" size="xl" />
          <span
            v-if="chatStore.unreadCounts[room.id]"
            class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1 font-medium"
          >
            {{ chatStore.unreadCounts[room.id] > 99 ? '99+' : chatStore.unreadCounts[room.id] }}
          </span>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="text-sm font-medium text-text-primary truncate">
                {{ room.room_type === 'group' ? `${room.name} (${room.member_count})` : (room.other_user?.nickname || room.name) }}
              </span>
              <span v-if="room.room_type === 'group'" class="flex-shrink-0 bg-maple-100 text-maple-700 text-[10px] px-1.5 py-0.5 rounded-full">群组</span>
            </div>
            <span v-if="room.last_message_at" class="text-[11px] text-text-secondary flex-shrink-0">
              {{ relativeTime(room.last_message_at) }}
            </span>
          </div>
          <p class="text-[13px] text-text-secondary truncate mt-0.5">
            {{ room.last_message || '暂无消息' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
