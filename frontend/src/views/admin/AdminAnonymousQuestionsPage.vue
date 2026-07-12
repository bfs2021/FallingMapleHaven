<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'

const questions = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await adminApi.anonymousQuestions()
    questions.value = res.data?.results || []
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">匿名提问追溯</h2>

    <div v-if="loading" class="card-base overflow-hidden">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-8" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 flex-1" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-5 w-12 rounded-full" />
          <div class="skeleton h-4 w-20" />
        </div>
      </div>
    </div>

    <div v-else-if="!questions.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="helpCircle" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无数据</p>
      <p class="text-xs text-text-secondary/60">用户提交的匿名提问将显示在此处</p>
    </div>

    <div v-else class="card-base overflow-hidden overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">提问者</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">接收者</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">内容</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">回答</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">状态</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(q, i) in questions"
            :key="q.id"
            class="group border-t border-border hover:bg-maple-50/40 transition-colors duration-150 animate-fade-in"
            :style="{ animationDelay: `${i * 30}ms` }"
          >
            <td class="px-4 py-3 text-text-secondary">{{ q.id }}</td>
            <td class="px-4 py-3">
              <span class="text-maple-600 font-medium">{{ q.real_sender?.nickname || '未知' }}</span>
              <span class="text-text-secondary text-xs ml-1">(#{{ q.real_sender?.user_id }})</span>
            </td>
            <td class="px-4 py-3">{{ q.recipient_nickname || q.recipient }}</td>
            <td class="px-4 py-3 max-w-xs truncate">{{ q.content }}</td>
            <td class="px-4 py-3 max-w-xs truncate text-text-secondary">{{ q.answer || '-' }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="q.is_answered
                  ? 'bg-green-50 text-green-600'
                  : 'bg-yellow-50 text-yellow-600'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="q.is_answered ? 'bg-green-500' : 'bg-yellow-500'" />
                {{ q.is_answered ? '已回答' : '未回答' }}
              </span>
            </td>
            <td class="px-4 py-3 text-text-secondary whitespace-nowrap">{{ new Date(q.created_at).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
