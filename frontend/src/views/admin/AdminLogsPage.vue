<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'
import SelectField from '@/components/SelectField.vue'

const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const loading = ref(true)
const error = ref('')

const filterAction = ref('')
const filterUserId = ref('')
const actions = ref([])

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function fetchLogs() {
  loading.value = true
  error.value = ''
  try {
    const params = { page: page.value }
    if (filterAction.value) params.action = filterAction.value
    if (filterUserId.value) params.user_id = filterUserId.value
    const res = await adminApi.logs(params)
    logs.value = res.data.results
    total.value = res.data.total
  } catch {
    error.value = '操作日志加载失败'
  } finally {
    loading.value = false
  }
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    fetchLogs()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    fetchLogs()
  }
}

function applyFilter() {
  page.value = 1
  fetchLogs()
}

onMounted(async () => {
  try {
    const [logRes, actionsRes] = await Promise.all([
      adminApi.logs({ page: 1 }),
      adminApi.logActions(),
    ])
    logs.value = logRes.data.results
    total.value = logRes.data.total
    actions.value = actionsRes.data || []
  } catch {
    error.value = '操作日志加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">操作日志</h2>
    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

    <div class="card-base p-4 flex items-center gap-4 flex-wrap">
      <div class="flex items-center gap-2">
        <label class="text-sm text-text-secondary">操作类型</label>
        <SelectField
          v-model="filterAction"
          :options="[{ value: '', label: '全部' }, ...actions.map(a => ({ value: a, label: a }))]"
          placeholder="操作类型"
        />
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-text-secondary">用户 ID</label>
        <input
          v-model="filterUserId"
          type="text"
          placeholder="输入用户 ID"
          class="input-base w-32"
        />
      </div>
      <button @click="applyFilter" class="btn-primary text-sm cursor-pointer">
        <Icon name="search" :size="14" /> 筛选
      </button>
    </div>

    <div v-if="loading" class="card-base overflow-hidden overflow-x-auto">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-32" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 flex-1" />
        </div>
      </div>
    </div>

    <div v-else-if="!logs.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="scrollText" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无日志</p>
      <p class="text-xs text-text-secondary/60">管理员的操作记录将显示在此处</p>
    </div>

    <div v-else class="card-base overflow-hidden overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">时间</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">操作人</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">操作内容</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(log, i) in logs"
            :key="log.id"
            class="border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in"
            :style="{ animationDelay: `${i * 30}ms` }"
          >
            <td class="px-4 py-3 text-text-secondary whitespace-nowrap text-xs">{{ log.created_at ? new Date(log.created_at).toLocaleString() : '-' }}</td>
            <td class="px-4 py-3 font-medium text-text-primary">{{ log.admin_nickname || '-' }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ log.action }} {{ log.detail ? JSON.stringify(log.detail) : '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="total > pageSize" class="flex items-center justify-between text-sm text-text-secondary animate-fade-in">
      <div>第 {{ page }} 页 / 共 {{ totalPages }} 页 (共 {{ total }} 条)</div>
      <div class="flex gap-2">
        <button
          @click="prevPage"
          :disabled="page <= 1"
          class="btn-secondary text-xs disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <Icon name="chevronLeft" :size="14" /> 上一页
        </button>
        <button
          @click="nextPage"
          :disabled="page >= totalPages"
          class="btn-secondary text-xs disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          下一页 <Icon name="chevronRight" :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>
