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
const selectedTestDetail = ref(null)
const selectedSubmissionDetail = ref(null)
const toast = useToast()

const bankCategories = [
  { value: 'all', label: '全部分类' },
  { value: 'daily_preference', label: '日常偏好' },
  { value: 'lifestyle_fun', label: '生活趣味' },
  { value: 'social_boundary', label: '社交边界' },
  { value: 'emotion_communication', label: '情绪沟通' },
  { value: 'values_future', label: '价值未来' },
  { value: 'memory_imagination', label: '回忆想象' },
]
const bankEditableCategories = bankCategories.filter((category) => category.value !== 'all')
const bankSearch = ref('')
const bankTag = ref('all')
const bankForm = ref(blankBankForm())
const editingBankQuestionId = ref(null)
const savingBankQuestion = ref(false)

const statCards = computed(() => [
  { label: '测试总数', value: stats.value?.total_tests ?? 0, icon: 'helpCircle' },
  { label: '已发布', value: stats.value?.published_tests ?? 0, icon: 'checkCircle' },
  { label: '草稿', value: stats.value?.draft_tests ?? 0, icon: 'edit' },
  { label: '已删除测试', value: stats.value?.deleted_tests ?? 0, icon: 'trash' },
  { label: '答卷总数', value: stats.value?.total_submissions ?? 0, icon: 'fileText' },
  { label: '登录用户答卷', value: stats.value?.user_submissions ?? 0, icon: 'user' },
  { label: '访客答卷', value: stats.value?.visitor_submissions ?? 0, icon: 'users' },
  { label: '题库题数', value: stats.value?.question_bank_count ?? 0, icon: 'list' },
])

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const [statsRes, testsRes, submissionsRes, bankRes] = await Promise.all([
      adminApi.quizStats(),
      adminApi.quizTests({ page_size: 50 }),
      adminApi.quizSubmissions({ page_size: 50 }),
      adminApi.quizQuestionBank(bankQueryParams()),
    ])
    stats.value = statsRes.data
    tests.value = testsRes.data?.results || []
    submissions.value = submissionsRes.data?.results || []
    bankQuestions.value = bankRes.data?.results || []
    if (selectedTestDetail.value && !tests.value.some((test) => test.id === selectedTestDetail.value.id)) {
      selectedTestDetail.value = null
    }
    if (selectedSubmissionDetail.value && !submissions.value.some((item) => item.id === selectedSubmissionDetail.value.id)) {
      selectedSubmissionDetail.value = null
    }
  } catch (error) {
    toast.error(error.response?.data?.message || '问答管理数据加载失败', 5000)
  } finally {
    loading.value = false
  }
}

function bankQueryParams() {
  const params = { page_size: 50 }
  const query = bankSearch.value.trim()
  if (query) params.q = query
  if (bankTag.value !== 'all') params.tag = bankTag.value
  return params
}

async function loadBankQuestions() {
  try {
    const res = await adminApi.quizQuestionBank(bankQueryParams())
    bankQuestions.value = res.data?.results || []
  } catch (error) {
    toast.error(error.response?.data?.message || '题库加载失败', 5000)
  }
}

function applyBankFilter() {
  loadBankQuestions()
}

function resetBankFilter() {
  bankSearch.value = ''
  bankTag.value = 'all'
  loadBankQuestions()
}

function bankCategoryLabel(tag) {
  return bankCategories.find((category) => category.value === tag)?.label || tag
}

function blankBankForm() {
  return {
    question_text: '',
    tags: [],
    options: [
      { option_text: '' },
      { option_text: '' },
    ],
  }
}

function resetBankForm() {
  bankForm.value = blankBankForm()
  editingBankQuestionId.value = null
}

function toggleBankTag(tag) {
  const tags = bankForm.value.tags
  bankForm.value.tags = tags.includes(tag)
    ? tags.filter((item) => item !== tag)
    : [...tags, tag]
}

function addBankOption() {
  if (bankForm.value.options.length >= 4) return
  bankForm.value.options.push({ option_text: '' })
}

function removeBankOption(index) {
  if (bankForm.value.options.length <= 2) return
  bankForm.value.options.splice(index, 1)
}

function editBankQuestion(question) {
  editingBankQuestionId.value = question.id
  bankForm.value = {
    question_text: question.question_text || '',
    tags: [...(question.tags || [])],
    options: (question.options || []).slice(0, 4).map((option) => ({
      option_text: optionLabel(option),
    })),
  }
  while (bankForm.value.options.length < 2) {
    bankForm.value.options.push({ option_text: '' })
  }
}

function bankQuestionPayload() {
  return {
    question_text: bankForm.value.question_text.trim(),
    tags: bankForm.value.tags,
    options: bankForm.value.options.map((option, index) => ({
      option_text: option.option_text.trim(),
      order: index + 1,
    })),
  }
}

async function saveBankQuestion() {
  const payload = bankQuestionPayload()
  if (!payload.question_text) {
    toast.error('请填写题目内容')
    return
  }
  if (payload.options.some((option) => !option.option_text)) {
    toast.error('请填写所有选项')
    return
  }
  if (payload.options.length < 2 || payload.options.length > 4) {
    toast.error('题库题目需要 2-4 个选项')
    return
  }

  savingBankQuestion.value = true
  try {
    if (editingBankQuestionId.value) {
      await adminApi.updateQuizQuestionBank(editingBankQuestionId.value, payload)
      toast.success('题库题目已更新')
    } else {
      await adminApi.createQuizQuestionBank(payload)
      toast.success('题库题目已创建')
    }
    resetBankForm()
    await loadAll()
  } catch (error) {
    toast.error(error.response?.data?.message || '题库题目保存失败', 5000)
  } finally {
    savingBankQuestion.value = false
  }
}

async function deleteBankQuestion(question) {
  const ok = await confirm({
    title: '删除题库题目',
    message: `确认删除「${question.question_text}」？`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!ok) return
  actingId.value = `bank-${question.id}`
  try {
    await adminApi.deleteQuizQuestionBank(question.id)
    if (editingBankQuestionId.value === question.id) resetBankForm()
    await loadAll()
  } catch (error) {
    toast.error(error.response?.data?.message || '题库题目删除失败', 5000)
  } finally {
    actingId.value = null
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

async function viewTestDetail(test) {
  actingId.value = `test-detail-${test.id}`
  try {
    const res = await adminApi.quizTestDetail(test.id)
    selectedTestDetail.value = res.data
  } catch (error) {
    toast.error(error.response?.data?.message || '测试详情加载失败', 5000)
  } finally {
    actingId.value = null
  }
}

async function viewSubmissionDetail(submission) {
  actingId.value = `submission-detail-${submission.id}`
  try {
    const res = await adminApi.quizSubmissionDetail(submission.id)
    selectedSubmissionDetail.value = res.data
  } catch (error) {
    toast.error(error.response?.data?.message || '答卷详情加载失败', 5000)
  } finally {
    actingId.value = null
  }
}

function optionLabel(option) {
  return option?.label || option?.text || option?.option_text || option?.content || `选项 ${option?.id ?? '-'}`
}

function findOption(options, id) {
  return options?.find((option) => String(option.id) === String(id))
}

function selectedOptionLabel(answer) {
  return answer?.selected_option_label || optionLabel(findOption(answer?.options, answer?.selected_option_id))
}

function correctOptionLabel(answer) {
  return answer?.correct_option_label || optionLabel(findOption(answer?.options, answer?.correct_option_id))
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

    <div v-else-if="activeTab === 'tests'" class="space-y-4">
      <div class="card-base overflow-hidden overflow-x-auto">
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
                <div class="flex items-center gap-2 whitespace-nowrap">
                  <button class="btn-ghost px-3 py-1 text-maple-600" :disabled="actingId === `test-detail-${test.id}`" @click="viewTestDetail(test)">查看</button>
                  <button class="btn-ghost px-3 py-1 text-red-600" :disabled="actingId === `test-${test.id}` || test.status === 'deleted'" @click="deleteTest(test)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <section v-if="selectedTestDetail" class="card-base p-5 space-y-4">
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 class="font-semibold text-text-primary">测试详情：{{ selectedTestDetail.title }}</h3>
            <p class="text-sm text-text-secondary">状态 {{ selectedTestDetail.status }} · {{ selectedTestDetail.questions?.length || 0 }} 道题</p>
          </div>
          <button class="btn-ghost px-3 py-1 text-text-secondary" @click="selectedTestDetail = null">收起</button>
        </div>

        <div class="divide-y divide-border rounded-lg border border-border overflow-hidden">
          <article v-for="(question, index) in selectedTestDetail.questions || []" :key="question.id" class="p-4 space-y-3 bg-surface">
            <div class="flex items-start gap-3">
              <span class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-maple-100 text-xs font-medium text-maple-700">{{ index + 1 }}</span>
              <div class="min-w-0 flex-1">
                <h4 class="font-medium text-text-primary">{{ question.question_text }}</h4>
                <div class="mt-3 grid gap-2 sm:grid-cols-2">
                  <div
                    v-for="option in question.options || []"
                    :key="option.id"
                    class="rounded-lg border px-3 py-2 text-sm"
                    :class="String(option.id) === String(question.correct_option_id) ? 'border-maple-300 bg-maple-50 text-maple-700' : 'border-border text-text-secondary'"
                  >
                    <span class="font-medium">{{ optionLabel(option) }}</span>
                    <span v-if="String(option.id) === String(question.correct_option_id)" class="ml-2 text-xs text-maple-600">标准答案</span>
                  </div>
                </div>
              </div>
            </div>
          </article>
          <p v-if="!(selectedTestDetail.questions || []).length" class="p-4 text-sm text-text-secondary">暂无题目详情</p>
        </div>
      </section>
    </div>

    <div v-else-if="activeTab === 'submissions'" class="space-y-4">
      <div class="card-base overflow-hidden overflow-x-auto">
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
                <div class="flex items-center gap-2 whitespace-nowrap">
                  <button class="btn-ghost px-3 py-1 text-maple-600" :disabled="actingId === `submission-detail-${item.id}`" @click="viewSubmissionDetail(item)">查看</button>
                  <button class="btn-ghost px-3 py-1 text-red-600" :disabled="actingId === `submission-${item.id}` || item.is_deleted" @click="deleteSubmission(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <section v-if="selectedSubmissionDetail" class="card-base p-5 space-y-4">
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 class="font-semibold text-text-primary">答卷详情：{{ selectedSubmissionDetail.test_title || selectedSubmissionDetail.test?.title }}</h3>
            <p class="text-sm text-text-secondary">
              {{ selectedSubmissionDetail.participant_name }} · {{ selectedSubmissionDetail.participant_type }} ·
              {{ selectedSubmissionDetail.score_percent }}% ({{ selectedSubmissionDetail.correct_count }}/{{ selectedSubmissionDetail.total_count }})
            </p>
          </div>
          <button class="btn-ghost px-3 py-1 text-text-secondary" @click="selectedSubmissionDetail = null">收起</button>
        </div>

        <div class="overflow-hidden rounded-lg border border-border">
          <table class="w-full text-sm">
            <thead class="table-header">
              <tr class="bg-maple-50/60 text-text-secondary">
                <th class="text-left px-4 py-3 font-medium">题目</th>
                <th class="text-left px-4 py-3 font-medium">选择</th>
                <th class="text-left px-4 py-3 font-medium">标准答案</th>
                <th class="text-left px-4 py-3 font-medium">结果</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="answer in selectedSubmissionDetail.answers || []" :key="answer.id || answer.question_id" class="border-t border-border">
                <td class="px-4 py-3 font-medium text-text-primary">{{ answer.question_text }}</td>
                <td class="px-4 py-3 text-text-secondary">{{ selectedOptionLabel(answer) }} <span class="text-xs">#{{ answer.selected_option_id }}</span></td>
                <td class="px-4 py-3 text-maple-600">{{ correctOptionLabel(answer) }} <span class="text-xs">#{{ answer.correct_option_id }}</span></td>
                <td class="px-4 py-3">
                  <span :class="answer.is_correct ? 'text-maple-600' : 'text-red-600'">{{ answer.is_correct ? '正确' : '错误' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!(selectedSubmissionDetail.answers || []).length" class="p-4 text-sm text-text-secondary">暂无答题详情</p>
        </div>
      </section>
    </div>

    <div v-else class="space-y-4">
      <section class="card-base p-4 space-y-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div class="flex flex-1 flex-col gap-3 sm:flex-row">
            <label class="min-w-0 flex-1 space-y-1">
              <span class="text-xs text-text-secondary">搜索题目</span>
              <input v-model="bankSearch" class="input-base" placeholder="输入题目关键词" @keyup.enter="applyBankFilter" />
            </label>
            <label class="space-y-1 sm:w-48">
              <span class="text-xs text-text-secondary">分类</span>
              <select v-model="bankTag" class="input-base" @change="applyBankFilter">
                <option v-for="category in bankCategories" :key="category.value" :value="category.value">{{ category.label }}</option>
              </select>
            </label>
          </div>
          <div class="flex gap-2">
            <button class="btn-secondary px-4 py-2" @click="applyBankFilter">筛选</button>
            <button class="btn-ghost px-4 py-2 text-text-secondary" @click="resetBankFilter">重置</button>
          </div>
        </div>

        <div class="border-t border-border pt-4 space-y-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-semibold text-text-primary">{{ editingBankQuestionId ? '编辑题库题目' : '新增题库题目' }}</h3>
            <button v-if="editingBankQuestionId" class="btn-ghost px-3 py-1 text-text-secondary" @click="resetBankForm">取消编辑</button>
          </div>

          <label class="block space-y-1">
            <span class="text-xs text-text-secondary">题目内容</span>
            <textarea v-model="bankForm.question_text" class="input-base min-h-20 resize-y" placeholder="填写题目内容" />
          </label>

          <div class="space-y-2">
            <span class="text-xs text-text-secondary">分类标签</span>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="category in bankEditableCategories"
                :key="category.value"
                type="button"
                class="rounded-full border px-3 py-1 text-xs transition-colors"
                :class="bankForm.tags.includes(category.value) ? 'border-maple-300 bg-maple-50 text-maple-700' : 'border-border text-text-secondary hover:bg-maple-50/50'"
                @click="toggleBankTag(category.value)"
              >
                {{ category.label }}
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between gap-3">
              <span class="text-xs text-text-secondary">选项（2-4 个）</span>
              <button class="btn-ghost px-3 py-1 text-maple-600" :disabled="bankForm.options.length >= 4" @click="addBankOption">添加选项</button>
            </div>
            <div class="grid gap-2 md:grid-cols-2">
              <div v-for="(option, index) in bankForm.options" :key="index" class="flex items-center gap-2">
                <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-maple-100 text-xs font-medium text-maple-700">{{ index + 1 }}</span>
                <input v-model="option.option_text" class="input-base min-w-0" :placeholder="`选项 ${index + 1}`" />
                <button class="btn-ghost px-2 py-1 text-red-600" :disabled="bankForm.options.length <= 2" @click="removeBankOption(index)">移除</button>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <button class="btn-secondary px-4 py-2" @click="resetBankForm">清空</button>
            <button class="btn-primary px-4 py-2" :disabled="savingBankQuestion" @click="saveBankQuestion">
              {{ savingBankQuestion ? '保存中...' : (editingBankQuestionId ? '保存修改' : '创建题目') }}
            </button>
          </div>
        </div>
      </section>

      <section class="card-base overflow-hidden">
        <div class="border-b border-border bg-maple-50/60 px-4 py-3 text-sm font-medium text-text-secondary">题库列表</div>
        <div v-if="bankQuestions.length" class="divide-y divide-border">
          <article v-for="question in bankQuestions" :key="question.id" class="p-4 hover:bg-maple-50/40">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div class="min-w-0 space-y-2">
                <h3 class="font-medium text-text-primary">{{ question.question_text }}</h3>
                <div class="flex flex-wrap gap-2 text-xs">
                  <span v-for="tag in question.tags || []" :key="tag" class="rounded-full bg-maple-50 px-2 py-0.5 text-maple-700">{{ bankCategoryLabel(tag) }}</span>
                  <span class="text-text-secondary">{{ question.options?.length || 0 }} 个选项</span>
                </div>
                <div class="flex flex-wrap gap-2 text-sm text-text-secondary">
                  <span v-for="option in question.options || []" :key="option.id || option.order || optionLabel(option)" class="rounded-lg border border-border px-2 py-1">{{ optionLabel(option) }}</span>
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <button class="btn-ghost px-3 py-1 text-maple-600" @click="editBankQuestion(question)">编辑</button>
                <button class="btn-ghost px-3 py-1 text-red-600" :disabled="actingId === `bank-${question.id}`" @click="deleteBankQuestion(question)">删除</button>
              </div>
            </div>
          </article>
        </div>
        <div v-else class="p-10 text-center text-text-secondary">暂无题库题目</div>
      </section>
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
