<script setup>
import { ref, watch } from 'vue'
import { postApi } from '@/api/posts'
import { useAuthStore } from '@/stores/auth'
import { useConfirm } from '@/composables/useConfirm'
import { relativeTime } from '@/utils/time'
import AvatarImage from './AvatarImage.vue'

const { confirm: confirmDelete } = useConfirm()

const props = defineProps({
  postId: { type: Number, required: true },
  postAuthorId: { type: Number, default: null },
  comments: { type: Array, default: () => [] },
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['load-comments', 'comment-added', 'comment-deleted'])
const authStore = useAuthStore()
const newComment = ref('')
const submitting = ref(false)
const deletingIds = ref({})

async function submitComment() {
  if (!newComment.value.trim() || submitting.value) return
  submitting.value = true
  try {
    await postApi.createComment(props.postId, newComment.value.trim())
    newComment.value = ''
    emit('comment-added')
  } catch { /* ignore */ } finally {
    submitting.value = false
  }
}

function canDelete(comment) {
  const currentUserId = authStore.user?.user_id
  const commentAuthorId = comment.user?.user_id || comment.user?.id
  if (authStore.isAdmin) return true
  return currentUserId && (currentUserId === commentAuthorId || currentUserId === props.postAuthorId)
}

async function deleteComment(comment) {
  if (!canDelete(comment) || deletingIds.value[comment.id]) return
  if (!await confirmDelete({ title: '删除评论', message: '确认删除这条评论？此操作不可撤销。', variant: 'danger', confirmText: '删除' })) return
  deletingIds.value = { ...deletingIds.value, [comment.id]: true }
  try {
    await postApi.deleteComment(comment.id)
    emit('comment-deleted', comment.id)
  } catch { /* ignore */ } finally {
    const next = { ...deletingIds.value }
    delete next[comment.id]
    deletingIds.value = next
  }
}
</script>

<template>
  <div v-if="show" class="border-t border-border pt-3 mt-3 space-y-3">
    <div v-if="!comments.length" class="text-sm text-text-secondary text-center py-2">
      暂无评论
    </div>
    <div v-for="comment in comments" :key="comment.id" class="flex gap-2.5">
      <AvatarImage :user="comment.user" size="xs" />
      <div class="flex-1 min-w-0">
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-medium text-text-primary">{{ comment.user?.nickname || comment.user?.username }}</span>
          <span class="text-xs text-text-secondary">{{ relativeTime(comment.created_at) }}</span>
          <button
            v-if="canDelete(comment)"
            @click="deleteComment(comment)"
            :disabled="deletingIds[comment.id]"
            class="ml-auto text-xs text-text-secondary hover:text-red-500 transition-colors disabled:opacity-50 cursor-pointer"
          >
            删除
          </button>
        </div>
        <p class="text-sm text-text-primary mt-0.5">{{ comment.content }}</p>
      </div>
    </div>
    <div class="flex gap-2 pt-1">
      <input
        v-model="newComment"
        type="text"
        placeholder="写评论..."
        class="input-base flex-1"
        @keyup.enter="submitComment"
      />
      <button
        @click="submitComment"
        :disabled="submitting || !newComment.trim()"
        class="btn-primary px-4"
      >
        发送
      </button>
    </div>
  </div>
</template>
