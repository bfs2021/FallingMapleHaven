<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import MessageBubble from '@/components/MessageBubble.vue'
import AvatarImage from '@/components/AvatarImage.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const authStore = useAuthStore()

const roomId = computed(() => Number(route.params.roomId))
const messageInput = ref('')
const sending = ref(false)
const loading = ref(true)
const loadingMore = ref(false)
const messagePage = ref(1)
const hasMoreMessages = ref(true)
const messageListRef = ref(null)

const currentRoom = computed(() => {
  return chatStore.rooms.find(r => r.id === roomId.value)
})

const otherUser = computed(() => {
  return currentRoom.value?.other_user || {}
})

const messages = computed(() => {
  return chatStore.messages[roomId.value] || []
})

onMounted(async () => {
  await Promise.all([
    chatStore.fetchRooms(),
    chatStore.fetchMessages(roomId.value),
  ])
  messagePage.value = 1
  loading.value = false
  scrollToBottom()
})

onUnmounted(() => {
  chatStore.activeRoom = null
})

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

async function loadMore() {
  if (loadingMore.value || !hasMoreMessages.value) return
  loadingMore.value = true
  const prevHeight = messageListRef.value?.scrollHeight || 0
  try {
    const data = await chatStore.fetchMessages(roomId.value, messagePage.value + 1)
    messagePage.value += 1
    hasMoreMessages.value = data.page * data.page_size < data.total
    await nextTick()
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight - prevHeight
    }
  } catch { /* ignore */ } finally {
    loadingMore.value = false
  }
}

async function sendMessage() {
  const text = messageInput.value.trim()
  if (!text) return
  sending.value = true
  messageInput.value = ''
  try {
    await chatStore.sendMessage(roomId.value, text)
    scrollToBottom()
  } catch {
    messageInput.value = text
  } finally {
    sending.value = false
  }
}

function goBack() {
  router.push('/chat')
}
</script>

<template>
  <div class="flex flex-col h-[calc(100dvh-64px)] md:h-[calc(100dvh-56px)] max-w-4xl mx-auto">
    <div class="flex items-center gap-3 px-4 py-3 bg-white border-b border-border flex-shrink-0">
      <button
        @click="goBack"
        class="w-10 h-10 flex items-center justify-center text-text-secondary hover:text-maple-600 hover:bg-maple-50 rounded-lg transition-colors cursor-pointer"
      >
        ‹
      </button>
      <AvatarImage :user="otherUser" size="sm" />
      <span class="text-base font-medium text-text-primary truncate">{{ otherUser.nickname || otherUser.username || currentRoom?.name || '聊天' }}</span>
    </div>

    <div
      ref="messageListRef"
      class="flex-1 overflow-y-auto px-4 py-4 space-y-3 scrollbar-hide"
    >
      <div v-if="loadingMore" class="text-center text-text-secondary py-2 text-xs">加载中...</div>
      <button
        v-if="hasMoreMessages && !loadingMore"
        @click="loadMore"
        class="w-full text-center text-xs text-maple-600 hover:text-maple-700 py-2 transition-colors cursor-pointer"
      >
        加载更多消息
      </button>

      <div v-if="loading" class="text-center text-text-secondary py-8">加载中...</div>
      <div v-else-if="!messages.length" class="text-center text-text-secondary py-8">
        暂无消息，发送第一条消息吧
      </div>
      <MessageBubble
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
        :isSelf="msg.sender_id === authStore.user?.user_id"
      />
    </div>

    <div class="flex-shrink-0 bg-white border-t border-border px-4 py-3">
      <div class="flex gap-2">
        <input
          v-model="messageInput"
          type="text"
          placeholder="输入消息..."
          class="flex-1 px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-maple-600/20 focus:border-maple-600"
          @keyup.enter="sendMessage"
        />
        <button
          @click="sendMessage"
          :disabled="sending || !messageInput.trim()"
          class="px-5 py-3 bg-maple-600 text-white text-sm rounded-xl hover:bg-maple-700 transition-colors disabled:opacity-50 cursor-pointer flex-shrink-0"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>
