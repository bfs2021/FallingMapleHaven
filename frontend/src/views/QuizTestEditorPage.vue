<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { quizApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const publishing = ref(false)
const publishErrors = ref([])
const bankQuestions = ref([])
const bankLoading = ref(false)
const bankQuery = ref('')
const bankPanelOpen = ref(false)
const selectedBankCategory = ref('')

const bankCategories = [
  { value: '', label: '全部' },
  { value: 'daily_preference', label: '日常偏好' },
  { value: 'lifestyle_fun', label: '生活趣味' },
  { value: 'social_boundary', label: '社交边界' },
  { value: 'emotion_communication', label: '情绪沟通' },
  { value: 'values_future', label: '价值未来' },
  { value: 'memory_imagination', label: '回忆想象' },
]

const form = reactive({
  id: null,
  title: '',
  status: 'draft',
  questions: [],
})

const ownerId = computed(() => Number(route.params.userId))
const testId = computed(() => Number(route.params.testId))
const isPublished = computed(() => form.status === 'published')
const canAddQuestion = computed(() => !isPublished.value && form.questions.length < 10)
const filteredBankQuestions = computed(() => {
  if (!selectedBankCategory.value) return bankQuestions.value
  return bankQuestions.value.filter((question) => question.tags?.includes(selectedBankCategory.value))
})
const normalizedPublishErrors = computed(() => publishErrors.value.map((error) => ({
  field: typeof error?.field === 'string' ? error.field : '',
  message: error?.message || '校验失败',
})))
const globalPublishErrors = computed(() => normalizedPublishErrors.value.filter((error) => {
  return !/^questions\.\d+(?:\.|$)/.test(error.field)
}))
const questionPublishErrorMap = computed(() => {
  const buckets = new Map()

  normalizedPublishErrors.value.forEach((error) => {
    const match = /^questions\.(\d+)(?:\.(.+))?$/.exec(error.field)
    if (!match) return

    const questionIndex = Number(match[1])
    const field = (match[2] || '').toLowerCase()
    const bucket = buckets.get(questionIndex) || {
      general: [],
      questionText: [],
      options: [],
      correctOption: [],
    }

    if (!field || field === 'question_text' || field === 'question') {
      bucket.questionText.push(error.message)
    } else if (field === 'correct_option' || field === 'correct_option_order') {
      bucket.correctOption.push(error.message)
    } else if (field.startsWith('options')) {
      bucket.options.push(error.message)
    } else {
      bucket.general.push(error.message)
    }

    buckets.set(questionIndex, bucket)
  })

  return buckets
})



onMounted(async () => {
  await loadTest()
  await loadQuestionBank()
})

function newLocalId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeQuestion(question, index) {
  return {
    localId: question.localId || newLocalId(),
    id: question.id || null,
    question_text: question.question_text || '',
    order: index + 1,
    correct_option_order: question.correct_option_order || null,
    source_bank_question_id: question.source_bank_question_id || null,
    options: (question.options || []).map((option, optionIndex) => ({
      localId: option.localId || newLocalId(),
      id: option.id || null,
      option_text: option.option_text || '',
      order: optionIndex + 1,
    })),
  }
}

function loadForm(data) {
  form.id = data.id
  form.title = data.title || ''
  form.status = data.status || 'draft'
  form.questions = (data.questions || []).map((question, index) => normalizeQuestion({
    ...question,
    correct_option_order: question.options?.find((option) => option.id === question.correct_option_id)?.order || null,
  }, index))
}

async function loadTest() {
  loading.value = true
  try {
    const res = await quizApi.myTestDetail(testId.value)
    loadForm(res.data)
  } catch (error) {
    toast.error(error.response?.data?.message || '测试加载失败', 5000)
  } finally {
    loading.value = false
  }
}

async function loadQuestionBank() {
  bankLoading.value = true
  try {
    const res = await quizApi.questionBank({ q: bankQuery.value, page_size: 100 })
    bankQuestions.value = res.data?.results || []
  } catch {
    bankQuestions.value = []
  } finally {
    bankLoading.value = false
  }
}

function addQuestion(seed = null) {
  if (!canAddQuestion.value) return
  const nextOrder = form.questions.length + 1
  form.questions.push(normalizeQuestion(seed || {
    question_text: '',
    order: nextOrder,
    correct_option_order: null,
    options: [
      { option_text: '', order: 1 },
      { option_text: '', order: 2 },
    ],
  }, nextOrder - 1))
}

function addBankQuestion(question) {
  addQuestion({
    question_text: question.question_text,
    source_bank_question_id: question.id,
    correct_option_order: null,
    options: (question.options || []).map((option) => ({ option_text: option.option_text, order: option.order })),
  })
}

function removeQuestion(index) {
  if (isPublished.value) return
  form.questions.splice(index, 1)
  reorderQuestions()
}

function reorderQuestions() {
  form.questions = form.questions.map((question, index) => normalizeQuestion(question, index))
}

function addOption(question) {
  if (isPublished.value || question.options.length >= 4) return
  question.options.push({ localId: newLocalId(), option_text: '', order: question.options.length + 1 })
}

function removeOption(question, optionIndex) {
  if (isPublished.value) return
  const removedOrder = question.options[optionIndex]?.order
  question.options.splice(optionIndex, 1)
  question.options = question.options.map((option, index) => ({ ...option, order: index + 1 }))
  if (question.correct_option_order === removedOrder) question.correct_option_order = null
}

function buildPayload() {
  reorderQuestions()
  return {
    title: form.title.trim(),
    questions: form.questions.map((question) => ({
      question_text: question.question_text.trim(),
      order: question.order,
      correct_option_order: question.correct_option_order,
      source_bank_question_id: question.source_bank_question_id,
      options: question.options.map((option) => ({
        option_text: option.option_text.trim(),
        order: option.order,
      })),
    })),
  }
}

function validateForPublish() {
  const errors = []
  if (!form.title.trim() || form.title.trim().length > 30) errors.push({ message: '测试标题不能为空且不超过 30 个字符' })
  if (form.questions.length !== 10) errors.push({ message: '发布时必须正好 10 道题' })
  form.questions.forEach((question, index) => {
    if (!question.question_text.trim()) errors.push({ message: `第 ${index + 1} 题题目不能为空` })
    if (question.question_text.trim().length > 80) errors.push({ message: `第 ${index + 1} 题题目不能超过 80 个字符` })
    const filledOptions = question.options.filter((option) => option.option_text.trim())
    if (filledOptions.length < 2 || question.options.length > 4) errors.push({ message: `第 ${index + 1} 题必须有 2-4 个选项` })
    if (!question.correct_option_order) errors.push({ message: `第 ${index + 1} 题必须设置标准答案` })
  })
  publishErrors.value = errors
  if (errors.length) {
    errors.forEach(err => toast.error(err.message, 5000))
  }
  return errors.length === 0
}

async function saveDraft({ quiet = false } = {}) {
  if (isPublished.value) return true
  saving.value = true
  try {
    const res = await quizApi.updateDraftTest(testId.value, buildPayload())
    loadForm(res.data)
    publishErrors.value = []
    if (!quiet) toast.success('草稿已保存')
    return true
  } catch (error) {
    toast.error(error.response?.data?.message || '保存失败', 5000)
    publishErrors.value = error.response?.data?.data?.errors || []
    return false
  } finally {
    saving.value = false
  }
}

async function publishTest() {
  if (!validateForPublish()) return
  publishing.value = true
  try {
    const saved = await saveDraft({ quiet: true })
    if (!saved) return
    const res = await quizApi.publishTest(testId.value)
    loadForm(res.data)
    publishErrors.value = []
    toast.success('发布成功')
  } catch (error) {
    toast.error(error.response?.data?.message || '发布失败', 5000)
    publishErrors.value = error.response?.data?.data?.errors || []
  } finally {
    publishing.value = false
  }
}

function backToList() {
  router.push({ name: 'QuizPage', params: { userId: ownerId.value } })
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8 space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-medium text-maple-600">默契问答</p>
        <h1 class="page-title mb-0">测试编辑器</h1>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button class="btn-secondary px-4 py-2" @click="backToList">返回列表</button>
        <button v-if="!isPublished" class="btn-secondary px-4 py-2" :disabled="saving" @click="saveDraft()">
          {{ saving ? '保存中...' : '保存草稿' }}
        </button>
        <button v-if="!isPublished" class="btn-primary px-4 py-2" :disabled="publishing" @click="publishTest">
          {{ publishing ? '发布中...' : '发布测试' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="card-base p-5 space-y-3">
        <div class="h-5 w-1/2 skeleton" />
        <div class="h-10 w-full skeleton" />
      </div>
    </div>

    <template v-else>
      <div v-if="publishErrors.length" class="card-base border border-red-200 bg-red-50/70 p-4">
        <div class="flex items-start gap-3">
          <Icon name="alertCircle" :size="18" class="mt-0.5 shrink-0 text-red-600" />
          <div class="min-w-0 space-y-2">
            <p class="text-sm font-semibold text-red-700">提交前校验未通过</p>
            <div v-if="globalPublishErrors.length" class="space-y-1 text-sm text-red-700">
              <p v-for="(error, index) in globalPublishErrors" :key="`${error.message}-${index}`" class="leading-5">
                {{ error.message }}
              </p>
            </div>
            <p v-if="Array.from(questionPublishErrorMap.keys()).length" class="text-xs text-red-600">
              第 {{ Array.from(questionPublishErrorMap.keys()).map((index) => index + 1).join('、') }} 题存在字段错误
            </p>
          </div>
        </div>
      </div>

      <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
        <main class="space-y-5">
          <section class="card-base p-5 space-y-3">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <label class="text-sm font-medium text-text-primary" for="quiz-title">测试标题</label>
              <span class="text-xs text-text-secondary">{{ form.status === 'published' ? '已发布，不可编辑' : `${form.title.length}/30` }}</span>
            </div>
            <input id="quiz-title" v-model="form.title" maxlength="30" class="input-base" :disabled="isPublished" />
          </section>

          <section v-if="!isPublished" class="card-base overflow-hidden lg:hidden">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
              :aria-expanded="bankPanelOpen"
              @click="bankPanelOpen = !bankPanelOpen"
            >
              <span>
                <span class="block text-base font-semibold text-text-primary">系统题库</span>
                <span class="mt-1 block text-sm text-text-secondary">从题库复制题目，不占用编辑区。</span>
              </span>
              <Icon name="chevronDown" :size="18" class="text-maple-600 transition-transform duration-150" :class="bankPanelOpen ? 'rotate-180' : ''" />
            </button>
            <div v-if="bankPanelOpen" class="border-t border-border bg-white p-4 space-y-3">
              <div class="flex flex-col gap-2 sm:flex-row">
                <label class="relative flex-1">
                  <Icon name="search" :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                  <input v-model="bankQuery" class="input-base pl-9" placeholder="搜索题库" @keyup.enter="loadQuestionBank" />
                </label>
                <button class="btn-secondary justify-center px-4 py-2" :disabled="bankLoading" @click="loadQuestionBank">搜索</button>
              </div>
              <div class="flex gap-2 overflow-x-auto pb-1">
                <button
                  v-for="category in bankCategories"
                  :key="category.value || 'all'"
                  type="button"
                  class="shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                  :class="selectedBankCategory === category.value ? 'border-maple-300 bg-maple-100 text-maple-700' : 'border-border bg-white text-text-secondary hover:border-maple-200 hover:text-maple-600'"
                  @click="selectedBankCategory = category.value"
                >
                  {{ category.label }}
                </button>
              </div>
              <div v-if="filteredBankQuestions.length" class="grid gap-2 sm:grid-cols-2">
                <button
                  v-for="question in filteredBankQuestions"
                  :key="question.id"
                  type="button"
                  class="rounded-xl border border-border bg-white p-3 text-left transition-colors hover:border-maple-300 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!canAddQuestion"
                  @click="addBankQuestion(question)"
                >
                  <p class="text-sm font-medium leading-5 text-text-primary line-clamp-2">{{ question.question_text }}</p>
                  <div class="mt-2 grid gap-1 text-xs text-text-secondary">
                    <span v-for="option in question.options" :key="option.id" class="line-clamp-1">{{ option.order }}. {{ option.option_text }}</span>
                  </div>
                </button>
              </div>
              <p v-else class="rounded-xl border border-border bg-white px-4 py-5 text-center text-sm text-text-secondary">暂无可用题库题目</p>
            </div>
          </section>

          <section class="space-y-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="flex items-center gap-2">
                <h2 class="text-lg font-semibold text-text-primary">题目 {{ form.questions.length }}/10</h2>
              </div>
              <button v-if="!isPublished" class="btn-primary justify-center px-4 py-2" :disabled="!canAddQuestion" @click="addQuestion()">添加题目</button>
            </div>

            <div v-if="!form.questions.length" class="card-base py-12 text-center text-text-secondary">
              <Icon name="helpCircle" :size="40" class="mx-auto mb-3 text-maple-300" />
              还没有题目
            </div>

            <article v-for="(question, questionIndex) in form.questions" :key="question.localId" class="card-base p-5 space-y-4">
              <div class="flex items-center justify-between gap-3">
                <h3 class="font-semibold text-text-primary">第 {{ questionIndex + 1 }} 题</h3>
                <button v-if="!isPublished" class="btn-ghost px-3 py-1 text-red-600" @click="removeQuestion(questionIndex)">删除</button>
              </div>

              <div v-if="questionPublishErrorMap.get(questionIndex)" class="space-y-2 rounded-xl border border-red-200 bg-red-50/70 px-3 py-2 text-sm text-red-700">
                <p v-for="(message, index) in questionPublishErrorMap.get(questionIndex).general" :key="`q-${questionIndex}-general-${index}`" class="leading-5">
                  {{ message }}
                </p>
                <p v-for="(message, index) in questionPublishErrorMap.get(questionIndex).questionText" :key="`q-${questionIndex}-text-${index}`" class="leading-5">
                  {{ message }}
                </p>
                <p v-for="(message, index) in questionPublishErrorMap.get(questionIndex).correctOption" :key="`q-${questionIndex}-correct-${index}`" class="leading-5">
                  {{ message }}
                </p>
                <p v-for="(message, index) in questionPublishErrorMap.get(questionIndex).options" :key="`q-${questionIndex}-options-${index}`" class="leading-5">
                  {{ message }}
                </p>
              </div>

              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <label class="text-sm font-medium text-text-primary">题目</label>
                  <span class="text-xs text-text-secondary">{{ question.question_text.length }}/80</span>
                </div>
                <input v-model="question.question_text" maxlength="80" class="input-base" :disabled="isPublished" placeholder="输入题目" />
                <p v-if="questionPublishErrorMap.get(questionIndex)?.questionText?.length" class="text-xs leading-5 text-red-600">
                  {{ questionPublishErrorMap.get(questionIndex).questionText[0] }}
                </p>
              </div>

              <div class="space-y-3">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <label class="text-sm font-medium text-text-primary">选项与标准答案</label>
                  <button v-if="!isPublished" class="btn-secondary justify-center px-3 py-1" :disabled="question.options.length >= 4" @click="addOption(question)">添加选项</button>
                </div>

                <div v-for="(option, optionIndex) in question.options" :key="option.localId" class="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <label class="flex cursor-pointer items-center gap-2 text-sm text-text-secondary sm:w-24">
                    <input v-model="question.correct_option_order" type="radio" :value="option.order" :disabled="isPublished" class="sr-only" />
                    <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors"
                      :class="question.correct_option_order === option.order ? 'border-maple-600' : 'border-border'">
                      <span v-if="question.correct_option_order === option.order" class="h-2 w-2 rounded-full bg-maple-600" />
                    </span>
                    答案
                  </label>
                  <input v-model="option.option_text" maxlength="30" class="input-base flex-1" :disabled="isPublished" :placeholder="`选项 ${optionIndex + 1}`" />
                  <button v-if="!isPublished" class="btn-ghost justify-center px-3 py-1 text-red-600" :disabled="question.options.length <= 1" @click="removeOption(question, optionIndex)">移除</button>
                </div>
                <p v-if="questionPublishErrorMap.get(questionIndex)?.correctOption?.length" class="text-xs leading-5 text-red-600">
                  {{ questionPublishErrorMap.get(questionIndex).correctOption[0] }}
                </p>
                <p v-if="questionPublishErrorMap.get(questionIndex)?.options?.length" class="text-xs leading-5 text-red-600">
                  {{ questionPublishErrorMap.get(questionIndex).options[0] }}
                </p>
              </div>
            </article>
          </section>
        </main>

        <aside v-if="!isPublished" class="hidden lg:block lg:sticky lg:top-6">
          <section class="card-base overflow-hidden">
            <div class="border-b border-border bg-white p-4">
              <h2 class="text-base font-semibold text-text-primary">系统题库</h2>
              <p class="mt-1 text-sm text-text-secondary">复制到当前测试后，再设置标准答案。</p>
            </div>
            <div class="p-4 space-y-3">
              <div class="flex gap-2">
                <label class="relative min-w-0 flex-1">
                  <Icon name="search" :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                  <input v-model="bankQuery" class="input-base pl-9" placeholder="搜索题库" @keyup.enter="loadQuestionBank" />
                </label>
                <button class="btn-secondary shrink-0 px-3 py-2" :disabled="bankLoading" @click="loadQuestionBank">搜索</button>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="category in bankCategories"
                  :key="category.value || 'all'"
                  type="button"
                  class="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                  :class="selectedBankCategory === category.value ? 'border-maple-300 bg-maple-100 text-maple-700' : 'border-border bg-white text-text-secondary hover:border-maple-200 hover:text-maple-600'"
                  @click="selectedBankCategory = category.value"
                >
                  {{ category.label }}
                </button>
              </div>
              <div v-if="filteredBankQuestions.length" class="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
                <button
                  v-for="question in filteredBankQuestions"
                  :key="question.id"
                  type="button"
                  class="w-full rounded-xl border border-border bg-white p-3 text-left transition-colors hover:border-maple-300 hover:bg-maple-50/40 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!canAddQuestion"
                  @click="addBankQuestion(question)"
                >
                  <p class="text-sm font-medium leading-5 text-text-primary line-clamp-2">{{ question.question_text }}</p>
                  <div class="mt-2 grid gap-1 text-xs text-text-secondary">
                    <span v-for="option in question.options" :key="option.id" class="line-clamp-1">{{ option.order }}. {{ option.option_text }}</span>
                  </div>
                </button>
              </div>
              <p v-else class="rounded-xl border border-border bg-white px-4 py-6 text-center text-sm text-text-secondary">暂无可用题库题目</p>
            </div>
          </section>
        </aside>
      </div>

    </template>
  </div>
</template>

<style scoped>
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
