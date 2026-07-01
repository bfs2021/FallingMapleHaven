<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useFeedStore } from '@/stores/feed'
import { useAuthStore } from '@/stores/auth'
import { postApi } from '@/api/posts'
import PostCard from '@/components/PostCard.vue'
import PostCreateCard from '@/components/PostCreateCard.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import AvatarImage from '@/components/AvatarImage.vue'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'

const feedStore = useFeedStore()
const authStore = useAuthStore()

const isGuest = computed(() => !authStore.isAuthenticated)
const toast = useToast()
const showCreateForm = ref(false)
const activeTag = ref('all')

const tags = [
  { key: 'all', label: '全部' },
  { key: 'chat', label: '#闲聊' },
  { key: 'share', label: '#分享' },
  { key: 'help', label: '#求助' },
  { key: 'question', label: '#提问' },
  { key: 'daily', label: '#日常' },
]

const tagParams = computed(() => {
  if (activeTag.value === 'all') return {}
  return { topic: activeTag.value }
})

onMounted(async () => {
  feedStore.currentPage = 1
  feedStore.hasMore = true
  await feedStore.fetchPosts(tagParams.value)
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})

function handleScroll() {
  if (feedStore.loading || !feedStore.hasMore) return
  const scrollBottom = window.innerHeight + window.scrollY
  const threshold = document.documentElement.scrollHeight - 200
  if (scrollBottom >= threshold) {
    feedStore.currentPage++
    feedStore.fetchPosts(tagParams.value)
  }
}

const leftPosts = computed(() => feedStore.posts.filter((_, i) => i % 2 === 0))
const rightPosts = computed(() => feedStore.posts.filter((_, i) => i % 2 === 1))

function switchTag(tag) {
  if (activeTag.value === tag) return
  activeTag.value = tag
  feedStore.currentPage = 1
  feedStore.hasMore = true
  feedStore.posts = []
  feedStore.fetchPosts(tagParams.value)
}
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">广场</h1>

    <div v-if="isGuest" class="card-base p-6 mb-6 text-center animate-fade-in">
      <Icon name="globe" :size="40" class="text-maple-300 mx-auto mb-3" />
      <p class="text-text-secondary mb-4">登录后即可发布动态、点赞和评论</p>
      <div class="flex items-center justify-center gap-3">
        <RouterLink to="/login?next=/" class="btn-primary px-6 py-2 inline-flex items-center gap-1.5">
          <Icon name="logIn" :size="16" /> 登录
        </RouterLink>
        <RouterLink to="/register?next=/" class="btn-secondary px-6 py-2 inline-flex items-center gap-1.5">
          <Icon name="userPlus" :size="16" /> 注册
        </RouterLink>
      </div>
    </div>

    <div v-else class="card-base p-5 mb-6 animate-fade-in">
      <div class="flex items-center gap-3">
        <AvatarImage :user="authStore.user" size="md" />
        <button
          @click="showCreateForm = true"
          class="flex-1 text-left px-4 py-2.5 border border-border rounded-full text-sm text-text-secondary hover:border-maple-300 hover:text-maple-600 transition-colors cursor-pointer min-h-[44px]"
        >
          分享你的想法...
        </button>
      </div>

      <Transition name="form-expand">
        <div v-if="showCreateForm" class="hidden md:block">
          <PostCreateCard @close="showCreateForm = false" />
        </div>
      </Transition>

      <BottomSheet :show="showCreateForm" title="发布动态" @close="showCreateForm = false">
        <PostCreateCard @close="showCreateForm = false" />
      </BottomSheet>
    </div>

    <div class="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-hide">
      <button
        v-for="tag in tags"
        :key="tag.key"
        @click="switchTag(tag.key)"
        class="px-4 py-1.5 text-sm rounded-full whitespace-nowrap transition-all duration-150 ease-out cursor-pointer min-h-[44px]"
        :class="activeTag === tag.key ? 'bg-maple-600 text-white shadow-sm' : 'bg-white text-text-secondary border border-border hover:border-maple-300 hover:text-maple-600'"
      >
        {{ tag.label }}
      </button>
    </div>

    <Transition name="list" mode="out-in">
      <div v-if="feedStore.loading && !feedStore.posts.length" key="loading" class="space-y-4 md:grid md:grid-cols-2 md:gap-4 md:space-y-0">
        <div v-for="i in 3" :key="i" class="card-base p-5 space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full skeleton" />
            <div class="space-y-2 flex-1">
              <div class="h-3 w-24 skeleton" />
              <div class="h-2.5 w-16 skeleton" />
            </div>
          </div>
          <div class="h-3 w-full skeleton" />
          <div class="h-3 w-3/4 skeleton" />
        </div>
      </div>
      <div v-else-if="!feedStore.posts.length" key="empty" class="text-center py-16 animate-fade-in">
        <Icon name="fileText" :size="48" class="text-maple-300 mx-auto mb-3" />
        <p class="text-text-secondary">{{ isGuest ? '暂无公开动态' : '暂无动态，快来发布第一条吧' }}</p>
      </div>
      <div v-else key="list">
        <!-- Mobile: single column -->
        <div class="md:hidden space-y-4">
          <div
            v-for="(post, i) in feedStore.posts"
            :key="post.id"
            :style="{ animationDelay: i * 40 + 'ms' }"
            class="animate-stagger-fade-in"
          >
            <PostCard :post="post" />
          </div>
        </div>

        <!-- Desktop: two balanced flex columns -- interleaved distribution -->
        <div class="hidden md:flex md:gap-6">
          <div class="flex-1 flex flex-col gap-5">
            <div
              v-for="(post, i) in leftPosts"
              :key="post.id"
              :style="{ animationDelay: i * 60 + 'ms' }"
              class="animate-stagger-fade-in"
            >
              <PostCard :post="post" />
            </div>
          </div>
          <div class="flex-1 flex flex-col gap-5">
            <div
              v-for="(post, i) in rightPosts"
              :key="post.id"
              :style="{ animationDelay: i * 60 + 'ms' }"
              class="animate-stagger-fade-in"
            >
              <PostCard :post="post" />
            </div>
          </div>
        </div>

        <div v-if="feedStore.loading && feedStore.posts.length" class="flex items-center justify-center gap-2 py-6 text-text-secondary animate-fade-in">
          <Icon name="loader" :size="16" class="animate-spin" /> 加载更多...
        </div>
        <div v-if="!feedStore.hasMore && feedStore.posts.length" class="relative my-6">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-border" />
          </div>
          <div class="relative flex justify-center">
            <span class="px-4 bg-[#F5F0EB] text-xs text-text-secondary">没有更多动态了</span>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.form-expand-enter-active,
.form-expand-leave-active {
  transition: all 0.25s ease-out;
  overflow: hidden;
}
.form-expand-enter-from,
.form-expand-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  max-height: 0;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.2s ease-out;
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
