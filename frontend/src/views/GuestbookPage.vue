<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { profileApi } from '@/api/profiles'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import AvatarImage from '@/components/AvatarImage.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()
const { confirm: confirmDelete } = useConfirm()

const entries = ref([])
const loading = ref(true)
const newContent = ref('')
const submitting = ref(false)
const replyTexts = ref({})
const targetUserId = computed(() => route.params.userId)
const isOwner = computed(() => authStore.user?.user_id === Number(targetUserId.value))
const isGuest = computed(() => !authStore.isAuthenticated)

onMounted(async () => {
  if (!targetUserId.value) return
  try {
    const res = await profileApi.guestbook(targetUserId.value, { page: 1, page_size: 20 })
    entries.value = res.data?.results || []
  } catch {
    toast.error('留言加载失败')
  } finally {
    loading.value = false
  }
})

async function submitEntry() {
  if (!newContent.value.trim() || !targetUserId.value) return
  submitting.value = true
  try {
    const res = await profileApi.createGuestbook(targetUserId.value, newContent.value.trim())
    entries.value.unshift(res.data)
    newContent.value = ''
  } catch {
    toast.error('留言发布失败')
  } finally {
    submitting.value = false
  }
}

async function replyEntry(entryId) {
  const text = replyTexts.value[entryId]
  if (!text?.trim()) return
  try {
    const res = await profileApi.replyGuestbook(entryId, text.trim())
    entries.value = entries.value.map(e =>
      e.id === entryId ? { ...e, reply: res.data?.reply || text.trim() } : e
    )
    replyTexts.value[entryId] = ''
  } catch {
    toast.error('回复失败')
  }
}

async function deleteEntry(entryId) {
  if (!await confirmDelete({ title: '删除留言', message: '确认删除这条留言？', variant: 'danger', confirmText: '删除' })) return
  try {
    await profileApi.deleteGuestbook(entryId)
    entries.value = entries.value.filter(e => e.id !== entryId)
  } catch {
    toast.error('删除失败')
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="page-title mb-6">留言板</h1>

    <div v-if="isGuest" class="card-base p-6 mb-6 text-center">
      <p class="text-text-secondary mb-4">登录后即可留言</p>
      <RouterLink :to="`/login?next=/profile/${targetUserId}/guestbook`" class="btn-primary inline-block px-6 py-2">
        登录
      </RouterLink>
    </div>

    <div v-else-if="!isOwner" class="card-base p-4 mb-6">
      <textarea
        v-model="newContent"
        rows="3"
        placeholder="留下你的留言..."
        class="input-base resize-none"
      />
      <div class="flex justify-end mt-2">
        <button
          @click="submitEntry"
          :disabled="submitting || !newContent.trim()"
          class="btn-primary px-5 py-1.5"
        >
          {{ submitting ? '发布中...' : '发布' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center text-text-secondary py-12">加载中...</div>

    <EmptyState v-else-if="!entries.length" icon="mail" title="暂无留言" description="来留下第一条留言吧" />

    <div v-else class="space-y-3">
      <div
        v-for="entry in entries"
        :key="entry.id"
        class="card-base p-4"
      >
        <div class="flex items-start gap-3">
          <AvatarImage :user="entry.user" size="sm" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-text-primary">{{ entry.user?.nickname }}</span>
              <span class="text-xs text-text-secondary">{{ relativeTime(entry.created_at) }}</span>
            </div>
            <p class="text-sm text-text-primary mt-1 whitespace-pre-wrap break-words">{{ entry.content }}</p>

            <div v-if="entry.reply" class="mt-2 pl-3 border-l-2 border-maple-400">
              <span class="text-tag font-medium text-maple-600">主人回复: </span>
              <span class="text-sm text-text-primary">{{ entry.reply }}</span>
            </div>

            <div v-if="isOwner && !entry.reply" class="mt-2 flex gap-2">
              <input
                v-model="replyTexts[entry.id]"
                type="text"
                placeholder="回复..."
                class="input-base !w-48 !py-1.5 !text-sm"
                @keyup.enter="replyEntry(entry.id)"
              />
              <button @click="replyEntry(entry.id)" class="btn-ghost px-3 py-1 text-xs">回复</button>
            </div>

            <button
              v-if="isOwner"
              @click="deleteEntry(entry.id)"
              class="mt-1 text-xs text-error-400 hover:text-error-500 transition-colors cursor-pointer"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
