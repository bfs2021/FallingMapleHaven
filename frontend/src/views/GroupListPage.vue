<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { groupApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()
const groups = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const createForm = ref({ name: '', description: '', is_public: true })
const coverFile = ref(null)
const creating = ref(false)
const createError = ref('')

onMounted(() => {
  fetchGroups()
})

async function fetchGroups() {
  loading.value = true
  try {
    const res = await groupApi.list()
    groups.value = res.data || []
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function createGroup() {
  if (!createForm.value.name.trim()) return
  creating.value = true
  createError.value = ''
  try {
    const formData = new FormData()
    formData.append('name', createForm.value.name)
    formData.append('description', createForm.value.description)
    formData.append('is_public', createForm.value.is_public)
    if (coverFile.value) {
      formData.append('cover_image', coverFile.value)
    }
    await groupApi.create(formData)
    showCreateModal.value = false
    createForm.value = { name: '', description: '', is_public: true }
    coverFile.value = null
    toast.success('小组创建成功')
    await fetchGroups()
  } catch (e) {
    createError.value = e.response?.data?.message || '创建失败'
  } finally {
    creating.value = false
  }
}

function goToDetail(id) {
  if (authStore.isAuthenticated) {
    router.push(`/groups/${id}`)
  } else {
    router.push(`/login?next=/groups/${id}`)
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="page-title !mb-0">兴趣小组</h1>
      <button
        v-if="authStore.isAuthenticated"
        @click="showCreateModal = true"
        class="btn-primary px-4"
      >
        + 创建小组
      </button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="card-base overflow-hidden">
        <div class="h-32 skeleton" />
        <div class="p-4 space-y-3">
          <div class="h-5 w-32 skeleton" />
          <div class="h-4 w-full skeleton" />
          <div class="h-4 w-24 skeleton" />
        </div>
      </div>
    </div>

    <div v-else-if="!groups.length" class="text-center text-text-secondary py-16">
      <Icon name="users" :size="48" class="mx-auto mb-3 text-maple-300" />
      <p class="text-lg mb-2">还没有小组</p>
      <p class="text-sm">创建一个吧</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="group in groups"
        :key="group.id"
        @click="goToDetail(group.id)"
        class="card-base overflow-hidden cursor-pointer"
      >
        <div class="h-32 bg-gradient-to-r from-maple-600 to-maple-400 relative">
          <img
            v-if="group.cover_url"
            :src="group.cover_url"
            class="w-full h-full object-cover"
          />
        </div>
        <div class="p-4">
          <h3 class="font-medium text-text-primary">{{ group.name }}</h3>
          <p v-if="group.description" class="text-sm text-text-secondary mt-1 line-clamp-2">{{ group.description }}</p>
          <div class="flex items-center gap-4 mt-3 text-xs text-text-secondary">
            <span class="flex items-center gap-1"><Icon name="users" :size="14" /> {{ group.member_count || 0 }} 名成员</span>
            <span v-if="!group.is_public" class="px-1.5 py-0.5 bg-gray-100 rounded">私密</span>
          </div>
        </div>
      </div>
    </div>

    <BottomSheet :show="showCreateModal" title="创建小组" @close="showCreateModal = false">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">名称</label>
          <input
            v-model="createForm.name"
            type="text"
            placeholder="输入小组名称"
            class="input-base"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">简介</label>
          <textarea
            v-model="createForm.description"
            rows="3"
            placeholder="小组简介（可选）"
            class="input-base resize-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">封面图（可选）</label>
          <label class="flex items-center gap-2 px-3 py-2.5 border border-border rounded-lg text-sm text-text-secondary cursor-pointer hover:bg-maple-50 transition-colors">
            <input type="file" accept="image/*" @change="e => coverFile = e.target.files[0] || null" class="hidden" />
            <span>{{ coverFile ? coverFile.name : '选择封面图片' }}</span>
          </label>
        </div>
        <label class="flex items-center justify-between w-full cursor-pointer select-none">
          <span class="text-sm text-text-primary">公开小组（任何人都可加入）</span>
          <ToggleSwitch v-model="createForm.is_public" />
        </label>
      </div>
      <p v-if="createError" class="text-red-500 text-sm">{{ createError }}</p>
      <div class="flex gap-3 mt-6 justify-end">
        <button
          @click="showCreateModal = false"
          class="btn-ghost"
        >
          取消
        </button>
        <button
          @click="createGroup"
          :disabled="creating || !createForm.name.trim()"
          class="btn-primary px-5"
        >
          {{ creating ? '创建中...' : '创建' }}
        </button>
      </div>
    </BottomSheet>
  </div>
</template>
