<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '@/api/admin'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'

const { confirm } = useConfirm()

const activeTab = ref('tests')
const tests = ref([])
const submissions = ref([])
const bankQuestions = ref([])
const stats = ref(null)
const loading = ref(true)
const actingId = ref(null)
const toast = useToast()

const statCards = computed(() => [
  { label: '测试总数', value: stats.value?.total_tests ?? 0, icon: 'helpCircle' },
  { label: '已发布', value: stats.value?.published_tests ?? 0, icon: 'checkCircle' },
  { label: '答卷总数', value: stats.value?.total_submissions ?? 0, icon: 'clipboardList' },
  { label: '题库题数', value: stats.value?.question_bank_count ?? 0, icon: 'library' },
])

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const [statsRes, testsRes, submissionsRes, bankRes] = await Promise.all([
      adminApi.quizStats(),
      adminApi.quizTests({ page_size: 50 }),
      adminApi.quizSubmissions({ page_size: 50 }),
      adminApi.quizQuestionBank({ page_size: 50 }),
    ])
    stats.value = statsRes.data
    tests.value = testsRes.data?.results || []
    submissions.value = submissionsRes.data?.results || []
    bankQuestions.value = bankRes.data?.results || []
  } catch (error) {
    toast.error(error.response?.data?.message || '问答管理数据加载失败', 5000)
  } finally {
    loading.value = false
  }
}

async function deleteTest(test) {
  const ok = await confirm({
    title: '删除测试',
    message: `确认删除《${test.title}》？该操作会将测试软删除。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!ok) return
  actingId.value = `test-${test.id}`
  try {
    await adminApi.deleteQuizTest(test.id)
    await loadAll()
  } finally {
    actingId.value = null
  }
}

async function deleteSubmission(submission) {
  const ok = await confirm({
    title: '删除答卷',
    message: `确认删除 ${submission.participant_name} 的答卷？该操作会软删除答卷。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!ok) return
  actingId.value = `submission-${submission.id}`
  try {
    await adminApi.deleteQuizSubmission(submission.id)
    await loadAll()
  } finally {
    actingId.value = null
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : '-'
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="page-title mb-0">问答管理</h2>
        <p class="text-sm text-text-secondary mt-1">管理主页测试、答卷和系统题库。</p>
      </div>
      <button class="btn-secondary px-4 py-2" :disabled="loading" @click="loadAll">刷新</button>
    </div>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="card in statCards" :key="card.label" class="card-base p-4 flex items-center gap-3">
        <Icon :name="card.icon" :size="24" class="text-maple-400" />
        <div>
          <p class="text-xs text-text-secondary">{{ card.label }}</p>
          <p class="text-xl font-bold text-text-primary">{{ card.value }}</p>
        </div>
      </div>
    </div>

    <div class="card-base p-1 flex gap-1">
      <button class="flex-1 rounded-lg px-4 py-2 text-sm" :class="activeTab === 'tests' ? 'bg-maple-100 text-maple-700 font-medium' : 'text-text-secondary'" @click="activeTab = 'tests'">测试</button>
      <button class="flex-1 rounded-lg px-4 py-2 text-sm" :class="activeTab === 'submissions' ? 'bg-maple-100 text-maple-700 font-medium' : 'text-text-secondary'" @click="activeTab = 'submissions'">答卷</button>
      <button class="flex-1 rounded-lg px-4 py-2 text-sm" :class="activeTab === 'bank' ? 'bg-maple-100 text-maple-700 font-medium' : 'text-text-secondary'" @click="activeTab = 'bank'">题库</button>
    </div>

    <div v-if="loading" class="card-base p-5 space-y-3">
      <div v-for="i in 5" :key="i" class="h-10 skeleton" />
    </div>

    <div v-else-if="activeTab === 'tests'" class="card-base overflow-hidden overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th class="text-left px-4 py-3 font-medium">ID</th>
            <th class="text-left px-4 py-3 font-medium">标题</th>
            <th class="text-left px-4 py-3 font-medium">主人</th>
            <th class="text-left px-4 py-3 font-medium">状态</th>
            <th class="text-left px-4 py-3 font-medium">题目/答卷</th>
            <th class="text-left px-4 py-3 font-medium">创建时间</th>
            <th class="text-left px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="test in tests" :key="test.id" class="border-t border-border hover:bg-maple-50/40">
            <td class="px-4 py-3 text-text-secondary">{{ test.id }}</td>
            <td class="px-4 py-3 font-medium text-text-primary">{{ test.title }}</td>
            <td class="px-4 py-3 text-maple-600">{{ test.owner?.nickname || test.owner?.username }}</td>
            <td class="px-4 py-3">{{ test.status }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ test.question_count }} / {{ test.submission_count }}</td>
            <td class="px-4 py-3 text-text-secondary whitespace-nowrap">{{ formatDate(test.created_at) }}</td>
            <td class="px-4 py-3">
              <button class="btn-ghost px-3 py-1 text-red-600" :disabled="actingId === `test-${test.id}` || test.status === 'deleted'" @click="deleteTest(test)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="activeTab === 'submissions'" class="card-base overflow-hidden overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="table-header">
          <tr class="bg-maple-50/60 text-text-secondary">
            <th class="text-left px-4 py-3 font-medium">ID</th>
            <th class="text-left px-4 py-3 font-medium">测试</th>
            <th class="text-left px-4 py-3 font-medium">参与者</th>
            <th class="text-left px-4 py-3 font-medium">得分</th>
            <th class="text-left px-4 py-3 font-medium">提交时间</th>
            <th class="text-left px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in submissions" :key="item.id" class="border-t border-border hover:bg-maple-50/40">
            <td class="px-4 py-3 text-text-secondary">{{ item.id }}</td>
            <td class="px-4 py-3 font-medium text-text-primary">{{ item.test_title }}</td>
            <td class="px-4 py-3 text-maple-600">{{ item.participant_name }} · {{ item.participant_type }}</td>
            <td class="px-4 py-3 text-text-secondary">{{ item.score_percent }}% ({{ item.correct_count }}/{{ item.total_count }})</td>
            <td class="px-4 py-3 text-text-secondary whitespace-nowrap">{{ formatDate(item.created_at) }}</td>
            <td class="px-4 py-3">
              <button class="btn-ghost px-3 py-1 text-red-600" :disabled="actingId === `submission-${item.id}` || item.is_deleted" @click="deleteSubmission(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2">
      <article v-for="question in bankQuestions" :key="question.id" class="card-base p-4 space-y-2">
        <h3 class="font-medium text-text-primary">{{ question.question_text }}</h3>
        <p class="text-sm text-text-secondary">{{ question.options?.length || 0 }} 个选项</p>
      </article>
      <div v-if="!bankQuestions.length" class="card-base p-10 text-center text-text-secondary md:col-span-2">暂无题库题目</div>
    </div>
  </div>
</template>

<style scoped>
/* Kill all elastic/scale animations on interactive elements */
button:active,
input:active,
select:active,
textarea:active,
a:active,
.card-base:active,
.btn-primary:active,
.btn-secondary:active,
.btn-ghost:active {
  --tw-scale-x: 1 !important;
  --tw-scale-y: 1 !important;
  transform: none !important;
}
</style>
