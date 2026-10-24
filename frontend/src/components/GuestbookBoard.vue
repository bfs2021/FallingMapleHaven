<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { profileApi } from '@/api/profiles'
import { useConfirm } from '@/composables/useConfirm'
import { relativeTime } from '@/utils/time'
import AvatarImage from './AvatarImage.vue'
import Icon from './Icon.vue'

const { confirm: confirmDelete } = useConfirm()

const props = defineProps({
  userId: { type: [Number, String], required: true },
  entries: { type: Array, default: () => [] },
  isOwner: { type: Boolean, default: false },
  isGuest: { type: Boolean, default: false },
})

const emit = defineEmits(['update:entries'])

const router = useRouter()
const guestbookContent = ref('')
const submittingGuestbook = ref(false)
const replyTexts = ref({})

async function submitEntry() {
  if (!guestbookContent.value.trim()) return
  submittingGuestbook.value = true
  try {
    const res = await profileApi.createGuestbook(props.userId, guestbookContent.value.trim())
    emit('update:entries', [res.data, ...props.entries])
    guestbookContent.value = ''
  } catch { /* ignore */ } finally {
    submittingGuestbook.value = false
  }
}

async function replyEntry(entryId) {
  const text = replyTexts.value[entryId]
  if (!text?.trim()) return
  try {
    const res = await profileApi.replyGuestbook(entryId, text.trim())
    const updated = props.entries.map(e =>
      e.id === entryId ? { ...e, reply: res.data.reply } : e
    )
    emit('update:entries', updated)
    replyTexts.value[entryId] = ''
  } catch { /* ignore */ }
}

async function deleteEntry(entryId) {
  if (!await confirmDelete({ title: '删除留言', message: '确认删除这条留言？此操作不可撤销。', variant: 'danger', confirmText: '删除' })) return
  try {
    await profileApi.deleteGuestbook(entryId)
    emit('update:entries', props.entries.filter(e => e.id !== entryId))
  } catch { /* ignore */ }
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="!isOwner && !isGuest" class="flex gap-2">
      <input
        v-model="guestbookContent"
        type="text"
        placeholder="写点什么..."
        class="input-base flex-1"
        @keyup.enter="submitEntry"
      />
      <button
        @click="submitEntry"
        :disabled="submittingGuestbook || !guestbookContent.trim()"
        class="btn-primary px-5 flex items-center gap-1.5"
      >
        <Icon name="send" :size="16" /> 发送
      </button>
    </div>

    <div v-if="isGuest" class="text-center py-8">
      <Icon name="messageSquare" :size="40" class="mx-auto mb-2 text-maple-300" />
      <RouterLink
        :to="`/login?next=/profile/${userId}`"
        class="text-maple-600 hover:text-maple-700 font-medium text-sm transition-colors"
      >
        登录后留言
      </RouterLink>
    </div>

    <div v-if="!entries.length && !isGuest" class="text-center py-12 text-text-secondary">
      <Icon name="messageSquare" :size="40" class="mx-auto mb-2 text-maple-300" />
      <p>暂无留言</p>
    </div>

    <TransitionGroup name="list" tag="div" class="space-y-0">
      <div
        v-for="entry in entries"
        :key="entry.id"
        class="flex gap-3 py-4 border-b border-border last:border-0"
      >
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
            class="mt-1 text-xs text-error-400 hover:text-error-500 transition-colors cursor-pointer flex items-center gap-1"
          >
            <Icon name="trash" :size="12" /> 删除
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease-out;
}
.list-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.list-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
