<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'

const users = ref([])
const loading = ref(true)
const error = ref('')

async function fetchUsers() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.users()
    users.value = res.data?.results || []
  } catch {
    error.value = '用户列表加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleUserActive(user) {
  const nextActive = !user.is_active
  try {
    const res = await adminApi.updateUser(user.id, { is_active: nextActive })
    Object.assign(user, res.data)
  } catch {
    error.value = '用户状态更新失败'
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">用户管理</h2>
    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

    <div v-if="loading" class="card-base overflow-hidden">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-8" />
          <div class="skeleton h-4 w-20" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-5 w-10 rounded-full" />
          <div class="skeleton h-4 w-8 ml-auto" />
        </div>
      </div>
    </div>

    <div v-else-if="!users.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="users" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无用户数据</p>
      <p class="text-xs text-text-secondary/60">当有新用户注册时，他们将显示在此处</p>
    </div>

    <div v-else class="card-base overflow-hidden">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">用户名</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">昵称</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">状态</th>
            <th scope="col" class="text-right px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(user, i) in users"
            :key="user.id"
            class="group border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in"
            :style="{ animationDelay: `${i * 30}ms` }"
          >
            <td class="px-4 py-3 text-text-secondary">{{ user.id }}</td>
            <td class="px-4 py-3 font-medium text-text-primary">{{ user.username }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ user.nickname || '-' }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="user.is_active
                  ? 'bg-green-50 text-green-600'
                  : 'bg-red-50 text-red-500'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="user.is_active ? 'bg-green-500' : 'bg-red-400'" />
                {{ user.is_active ? '正常' : '禁用' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                @click="toggleUserActive(user)"
                class="btn-ghost text-xs"
              >
                {{ user.is_active ? '禁用' : '启用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
