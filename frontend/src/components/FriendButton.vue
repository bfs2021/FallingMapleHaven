<script setup>
import { ref } from 'vue'
import { useFriendStore } from '@/stores/friend'

const props = defineProps({
  userId: { type: [Number, String], required: true },
  friendStatus: { type: String, default: 'none' },
  requestId: { type: [Number, String], default: null },
})

const emit = defineEmits(['status-changed'])
const friendStore = useFriendStore()
const loading = ref(false)

async function sendRequest() {
  loading.value = true
  try {
    await friendStore.sendRequest(props.userId)
    emit('status-changed', 'pending_sent')
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function handleRequest(action) {
  loading.value = true
  try {
    const params = props.requestId != null ? { request_id: props.requestId } : { from_user_id: props.userId }
    await friendStore.handleRequest(params, action)
    emit('status-changed', action === 'accept' ? 'accepted' : 'none')
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function unfriend() {
  loading.value = true
  try {
    await friendStore.unfriend(props.userId)
    emit('status-changed', 'none')
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="friendStatus !== 'self'" class="flex items-center gap-2">
    <button
      v-if="friendStatus === 'none'"
      @click="sendRequest"
      :disabled="loading"
      class="btn-primary px-3 text-xs"
    >
      加好友
    </button>
    <span
      v-else-if="friendStatus === 'pending_sent'"
      class="px-3 py-1 bg-gray-200 text-text-secondary text-xs rounded-lg"
    >
      已申请
    </span>
    <template v-else-if="friendStatus === 'pending_received'">
      <button
        @click="handleRequest('accept')"
        :disabled="loading"
        class="btn-primary px-3 text-xs"
      >
        同意
      </button>
      <button
        @click="handleRequest('reject')"
        :disabled="loading"
        class="px-3 py-1 bg-gray-200 text-text-secondary text-xs rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50 cursor-pointer"
      >
        拒绝
      </button>
    </template>
    <template v-else-if="friendStatus === 'accepted'">
      <span class="px-3 py-1 bg-green-100 text-green-700 text-xs rounded-lg">好友</span>
      <button
        @click="unfriend"
        :disabled="loading"
        class="text-xs text-text-secondary hover:text-red-500 transition-colors cursor-pointer"
      >
        解除好友
      </button>
    </template>
  </div>
</template>
