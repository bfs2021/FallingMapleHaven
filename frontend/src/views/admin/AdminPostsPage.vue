<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import TabBar from '@/components/TabBar.vue'
import Icon from '@/components/Icon.vue'
import { useConfirm } from '@/composables/useConfirm'

const { confirm: confirmDelete } = useConfirm()

const posts = ref([])
const comments = ref([])
const loading = ref(true)
const activeTab = ref('posts')
const error = ref('')

async function fetchContent() {
  loading.value = true
  error.value = ''
  try {
    const [postRes, commentRes] = await Promise.all([
      adminApi.posts(),
      adminApi.comments(),
    ])
    posts.value = postRes.data?.results || []
    comments.value = commentRes.data?.results || []
  } catch {
    error.value = '内容数据加载失败'
  } finally {
    loading.value = false
  }
}

async function deletePost(post) {
  if (!await confirmDelete({ title: '删除动态', message: '确认删除这条动态？此操作不可撤销。', variant: 'danger', confirmText: '删除' })) return
  try {
    await adminApi.deletePost(post.id)
    posts.value = posts.value.filter(item => item.id !== post.id)
  } catch {
    error.value = '动态删除失败'
  }
}

async function deleteComment(comment) {
  if (!await confirmDelete({ title: '删除评论', message: '确认删除这条评论？此操作不可撤销。', variant: 'danger', confirmText: '删除' })) return
  try {
    await adminApi.deleteComment(comment.id)
    comments.value = comments.value.filter(item => item.id !== comment.id)
  } catch {
    error.value = '评论删除失败'
  }
}

onMounted(fetchContent)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">内容管理</h2>
    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

    <TabBar
      :tabs="[{ key: 'posts', label: '动态' }, { key: 'comments', label: '评论' }]"
      :activeKey="activeTab"
      @update:activeKey="activeTab = $event"
    />

    <div v-if="loading" class="card-base overflow-hidden">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-8" />
          <div class="skeleton h-4 flex-1" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 w-24" />
          <div class="skeleton h-4 w-10 ml-auto" />
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'posts' && !posts.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="fileText" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无动态</p>
      <p class="text-xs text-text-secondary/60">用户发布动态后，他们将显示在此处</p>
    </div>

    <div v-else-if="activeTab === 'comments' && !comments.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="messageCircle" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无评论</p>
      <p class="text-xs text-text-secondary/60">用户评论动态后，他们将显示在此处</p>
    </div>

    <div v-else class="card-base overflow-hidden">
      <table v-if="activeTab === 'posts'" class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">内容</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">作者</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">时间</th>
            <th scope="col" class="text-right px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(post, i) in posts"
            :key="post.id"
            class="group border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in"
            :style="{ animationDelay: `${i * 30}ms` }"
          >
            <td class="px-4 py-3 text-text-secondary">{{ post.id }}</td>
            <td class="px-4 py-3 max-w-xs truncate text-text-primary">{{ post.content || '(无内容)' }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ post.author_nickname || '-' }}</td>
            <td class="px-4 py-3 text-text-secondary text-xs">{{ post.created_at ? new Date(post.created_at).toLocaleString() : '-' }}</td>
            <td class="px-4 py-3 text-right">
              <button
                @click="deletePost(post)"
                class="btn-ghost text-xs text-red-500 hover:text-red-600"
                aria-label="删除动态"
              >
                <Icon name="trash2" :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <table v-else class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">评论</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">动态</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">作者</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">时间</th>
            <th scope="col" class="text-right px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(comment, i) in comments"
            :key="comment.id"
            class="group border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in"
            :style="{ animationDelay: `${i * 30}ms` }"
          >
            <td class="px-4 py-3 text-text-secondary">{{ comment.id }}</td>
            <td class="px-4 py-3 max-w-xs truncate text-text-primary">{{ comment.content }}</td>
            <td class="px-4 py-3 max-w-xs truncate text-text-secondary">{{ comment.post_content || '-' }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ comment.author_nickname || '-' }}</td>
            <td class="px-4 py-3 text-text-secondary text-xs">{{ comment.created_at ? new Date(comment.created_at).toLocaleString() : '-' }}</td>
            <td class="px-4 py-3 text-right">
              <button
                @click="deleteComment(comment)"
                class="btn-ghost text-xs text-red-500 hover:text-red-600"
                aria-label="删除评论"
              >
                <Icon name="trash2" :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
