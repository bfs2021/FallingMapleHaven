<script setup>
import { useFeedStore } from '@/stores/feed'
import Icon from './Icon.vue'

const props = defineProps({
  postId: { type: Number, required: true },
  isLiked: { type: Boolean, default: false },
  likeCount: { type: Number, default: 0 },
  commentCount: { type: Number, default: 0 },
})

const emit = defineEmits(['toggle-comments', 'like-updated'])
const feedStore = useFeedStore()

async function handleLike() {
  const res = await feedStore.toggleLike(props.postId)
  emit('like-updated', res.data)
}
</script>

<template>
  <div class="post-actions flex items-center gap-6 text-text-secondary text-sm">
    <button
      @click="handleLike"
      class="flex items-center gap-1.5 hover:text-maple-600 transition-colors cursor-pointer select-none"
      :class="{ 'text-red-500': isLiked }"
    >
      <Icon :name="'heart'" :size="18" :fill="isLiked ? 'currentColor' : 'none'" />
      <span>{{ likeCount || '' }}</span>
    </button>
    <button
      @click="emit('toggle-comments')"
      class="flex items-center gap-1.5 hover:text-maple-600 transition-colors cursor-pointer select-none"
    >
      <Icon name="messageCircle" :size="18" />
      <span>{{ commentCount || '' }}</span>
    </button>
  </div>
</template>
