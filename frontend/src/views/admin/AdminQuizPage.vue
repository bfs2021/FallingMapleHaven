<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'

const questions = ref([])
const loading = ref(true)

const total = computed(() => questions.value.length)
const answeredCount = computed(() => questions.value.filter(q => q.has_answer).length)
const accuracy = computed(() => {
  if (!answeredCount.value) return 0
  const correct = questions.value.filter(q => q.is_correct === true).length
  return Math.round((correct / answeredCount.value) * 100)
})

onMounted(async () => {
  try {
    const res = await adminApi.quizQuestions()
    questions.value = res.data?.results || []
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">问答管理</h2>

    <div class="flex gap-4">
      <div class="card-base flex-1 p-4 flex items-center gap-3">
        <Icon name="helpCircle" :size="24" class="text-maple-400" />
        <div>
          <p class="text-xs text-text-secondary">总题数</p>
          <p class="text-xl font-bold text-text-primary">{{ total }}</p>
        </div>
      </div>
      <div class="card-base flex-1 p-4 flex items-center gap-3">
        <Icon name="checkCircle" :size="24" class="text-green-400" />
        <div>
          <p class="text-xs text-text-secondary">已答数</p>
          <p class="text-xl font-bold text-text-primary">{{ answeredCount }}</p>
        </div>
      </div>
      <div class="card-base flex-1 p-4 flex items-center gap-3">
        <Icon name="target" :size="24" class="text-blue-400" />
        <div>
          <p class="text-xs text-text-secondary">正确率</p>
          <p class="text-xl font-bold text-text-primary">{{ accuracy }}%</p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="card-base overflow-hidden">
      <div class="space-y-0">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4 px-4 py-3" :class="i > 1 ? 'border-t border-border' : ''">
          <div class="skeleton h-4 w-8" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 w-16" />
          <div class="skeleton h-4 flex-1" />
          <div class="skeleton h-4 w-12" />
          <div class="skeleton h-4 w-12" />
          <div class="skeleton h-4 w-20" />
        </div>
      </div>
    </div>

    <div v-else-if="!questions.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="helpCircle" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无数据</p>
      <p class="text-xs text-text-secondary/60">用户创建的默契问答将显示在此处</p>
    </div>

    <div v-else class="card-base overflow-hidden overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th scope="col" class="text-left px-4 py-3 font-medium">ID</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">出题人</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">目标人</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">题目内容</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">已答</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">是否正确</th>
            <th scope="col" class="text-left px-4 py-3 font-medium">创建时间</th>
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
              <span class="text-maple-600 font-medium">{{ q.creator?.nickname || '未知' }}</span>
              <span class="text-text-secondary text-xs ml-1">(#{{ q.creator?.user_id }})</span>
            </td>
            <td class="px-4 py-3">
              <span class="text-maple-600 font-medium">{{ q.target_user?.nickname || '未知' }}</span>
              <span class="text-text-secondary text-xs ml-1">(#{{ q.target_user?.user_id }})</span>
            </td>
            <td class="px-4 py-3 max-w-xs truncate">{{ q.question }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="q.has_answer
                  ? 'bg-green-50 text-green-600'
                  : 'bg-yellow-50 text-yellow-600'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="q.has_answer ? 'bg-green-500' : 'bg-yellow-500'" />
                {{ q.has_answer ? '是' : '否' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                v-if="!q.has_answer"
                class="text-text-secondary text-xs"
              >-</span>
              <span
                v-else
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="q.is_correct
                  ? 'bg-green-50 text-green-600'
                  : 'bg-red-50 text-red-600'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="q.is_correct ? 'bg-green-500' : 'bg-red-500'" />
                {{ q.is_correct ? '正确' : '错误' }}
              </span>
            </td>
            <td class="px-4 py-3 text-text-secondary whitespace-nowrap">{{ new Date(q.created_at).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
