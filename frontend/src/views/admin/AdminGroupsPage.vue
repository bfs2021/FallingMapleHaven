<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { relativeTime } from '@/utils/time'

const toast = useToast()
const { confirm } = useConfirm()

const groups = ref([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')
const expandedGroupId = ref(null)
const expandedPosts = ref([])
const loadingPosts = ref(false)
const deletingId = ref(null)

const filteredGroups = computed(() => {
  if (!searchQuery.value.trim()) return groups.value
  const q = searchQuery.value.trim().toLowerCase()
  return groups.value.filter(g => g.name.toLowerCase().includes(q))
})

async function fetchGroups() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.groups()
    groups.value = res.data?.results || []
  } catch {
    error.value = '群组列表加载失败'
  } finally {
    loading.value = false
  }
}

async function deleteGroup(group) {
  const ok = await confirm({
    title: '删除群组',
    message: `确定要删除群组「${group.name}」？此操作不可撤销。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!ok) return
  deletingId.value = group.id
  try {
    await adminApi.deleteGroup(group.id)
    toast.success('群组已删除')
    groups.value = groups.value.filter(g => g.id !== group.id)
  } catch {
    error.value = '群组删除失败'
  } finally {
    deletingId.value = null
  }
}

async function toggleExpand(group) {
  if (expandedGroupId.value === group.id) {
    expandedGroupId.value = null
    expandedPosts.value = []
    return
  }
  expandedGroupId.value = group.id
  loadingPosts.value = true
  try {
    const res = await adminApi.groupPosts(group.id)
    expandedPosts.value = res.data?.results || []
  } catch {
    expandedPosts.value = []
  } finally {
    loadingPosts.value = false
  }
}

onMounted(fetchGroups)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">群组管理</h2>

    <div class="flex items-center gap-3">
      <div class="relative flex-1 max-w-sm">
        <Icon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索群组名称..."
          class="input-base pl-9"
        />
      </div>
    </div>

    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

    <div v-if="loading" class="card-base overflow-hidden">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-8" />
          <div class="skeleton h-4 w-32" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 w-10" />
          <div class="skeleton h-5 w-10 rounded-full" />
          <div class="skeleton h-4 w-20" />
          <div class="skeleton h-4 w-10 ml-auto" />
        </div>
      </div>
    </div>

    <div v-else-if="!filteredGroups.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="hash" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">{{ searchQuery.trim() ? '未找到匹配的群组' : '暂无群组' }}</p>
      <p class="text-xs text-text-secondary/60">{{ searchQuery.trim() ? '尝试使用其他关键词搜索' : '当用户创建群组后，他们将显示在此处' }}</p>
    </div>

    <div v-else class="card-base overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">名称</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">创建者</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">成员数</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">是否公开</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">创建时间</th>
            <th scope="col" class="text-right px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(g, i) in filteredGroups" :key="g.id">
            <tr
              class="group border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in cursor-pointer"
              :style="{ animationDelay: `${i * 30}ms` }"
              @click="toggleExpand(g)"
            >
              <td class="px-4 py-3 text-text-secondary">{{ g.id }}</td>
              <td class="px-4 py-3 font-medium text-text-primary">{{ g.name }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ g.creator_name || '-' }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ g.member_count || 0 }}</td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="g.is_public ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="g.is_public ? 'bg-green-500' : 'bg-red-400'" />
                  {{ g.is_public ? '公开' : '私密' }}
                </span>
              </td>
              <td class="px-4 py-3 text-text-secondary text-xs">{{ relativeTime(g.created_at) }}</td>
              <td class="px-4 py-3 text-right">
                <button
                  @click.stop="deleteGroup(g)"
                  :disabled="deletingId === g.id"
                  class="btn-ghost text-xs text-red-500 hover:text-red-600"
                  aria-label="删除群组"
                >
                  {{ deletingId === g.id ? '删除中...' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="expandedGroupId === g.id" :key="'expanded-' + g.id">
              <td colspan="7" class="px-4 py-3 bg-maple-50/30 border-t border-border">
                <div class="flex items-center gap-2 mb-3">
                  <Icon name="fileText" :size="14" class="text-maple-600" />
                  <span class="text-xs font-medium text-text-secondary">小组动态</span>
                  <Icon v-if="loadingPosts" name="loader" :size="12" class="animate-spin text-maple-600" />
                </div>
                <div v-if="loadingPosts && !expandedPosts.length" class="text-xs text-text-secondary/60 py-2">加载中...</div>
                <div v-else-if="!expandedPosts.length" class="text-xs text-text-secondary/60 py-2">暂无动态</div>
                <div v-else class="space-y-2">
                  <div
                    v-for="post in expandedPosts"
                    :key="post.id"
                    class="flex items-start gap-3 bg-white rounded-lg p-3 border border-border"
                  >
                    <div class="flex-1 min-w-0">
                      <p class="text-xs text-text-primary line-clamp-2">{{ post.content || '(无内容)' }}</p>
                      <p class="text-xs text-text-secondary mt-1">
                        {{ post.author_name || '未知' }} · {{ relativeTime(post.created_at) }}
                      </p>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
