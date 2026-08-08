<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { relationMatchApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'
import {
  getRelationMatchQuestionTypeLabel,
  normalizeRelationMatchQueryValue,
} from '@/utils/relationMatch'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const loading = ref(true)
const submitting = ref(false)
const test = ref(null)
const currentQuestionIndex = ref(0)
const answers = ref({})
const visitorName = ref('')
const shareCode = ref(normalizeRelationMatchQueryValue(route.query.shareCode))

const ownerId = computed(() => route.params.userId)
const questions = computed(() => test.value?.questions || [])
const totalQuestions = computed(() => test.value?.question_count || questions.value.length || 40)
const currentQuestion = computed(() => questions.value[currentQuestionIndex.value] || null)
const currentQuestionAnswer = computed(() => {
  const question = currentQuestion.value
  if (!question) return []
  const value = answers.value[question.id]
  return Array.isArray(value) ? value : value ? [value] : []
})
const answeredCount = computed(() => questions.value.filter(question => getQuestionSelection(question).length > 0).length)
const progressPercent = computed(() => Math.max(1, Math.min(100, Math.round(((currentQuestionIndex.value + 1) / Math.max(totalQuestions.value, 1)) * 100))))
const isGuest = computed(() => !authStore.isAuthenticated)
const canSubmitCurrent = computed(() => currentQuestionAnswer.value.length > 0)
const canSubmitAll = computed(() => answeredCount.value === totalQuestions.value)
const currentQuestionNumber = computed(() => currentQuestionIndex.value + 1)

watch(
  () => route.query.shareCode,
  (value) => {
    shareCode.value = normalizeRelationMatchQueryValue(value)
  },
)

watch(
  () => route.params.userId,
  () => loadTest(),
)

onMounted(loadTest)

async function loadTest() {
  loading.value = true
  currentQuestionIndex.value = 0
  answers.value = {}
  try {
    const res = await relationMatchApi.getTestDetail()
    test.value = res.data || null
  } catch (error) {
    toast.error(error.response?.data?.message || '基础测试加载失败', 5000)
  } finally {
    loading.value = false
  }
}

function getQuestionSelection(question) {
  const value = answers.value[question.id]
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

function setAnswer(question, optionId) {
  const current = getQuestionSelection(question)
  if (question.question_type === 'multi_select') {
    const next = current.includes(optionId)
      ? current.filter(id => id !== optionId)
      : [...current, optionId]
    answers.value = { ...answers.value, [question.id]: next }
    return
  }

  answers.value = { ...answers.value, [question.id]: [optionId] }
}

function goPrevious() {
  if (currentQuestionIndex.value === 0) return
  currentQuestionIndex.value -= 1
}

function goNext() {
  if (!canSubmitCurrent.value || currentQuestionIndex.value >= questions.value.length - 1) return
  currentQuestionIndex.value += 1
}

function isOptionSelected(question, optionId) {
  return getQuestionSelection(question).includes(optionId)
}

function questionOptionId(option) {
  return option.id ?? option.option_id ?? option.value ?? option.order
}

function questionOptionText(option) {
  return option.option_text ?? option.text ?? option.label ?? ''
}

function questionTag(question) {
  return question.scene_tag || getRelationMatchQuestionTypeLabel(question.question_type)
}

async function submitTest() {
  if (!test.value || !canSubmitAll.value) {
    toast.error('请先完成全部 40 题', 4000)
    return
  }

  if (!authStore.isAuthenticated && !visitorName.value.trim()) {
    toast.error('请先填写昵称', 4000)
    return
  }

  submitting.value = true
  try {
    const payload = {
      answers: questions.value.map(question => ({
        question_id: question.id,
        selected_option_ids: getQuestionSelection(question),
      })),
      share_code: shareCode.value.trim(),
    }

    if (!authStore.isAuthenticated) {
      payload.participant_name = visitorName.value.trim()
    }

    const submitRes = await relationMatchApi.submitTest(payload)
    const submittedProfile = submitRes.data || {}

    toast.success('画像已生成')

    if (submittedProfile.result_url) {
      await router.replace(submittedProfile.result_url)
      return
    }

    if (ownerId.value) {
      await router.replace({
        name: 'RelationMatchPage',
        params: { userId: ownerId.value },
      })
      return
    }

    await router.replace({ name: 'RelationMatchMyPage' })
  } catch (error) {
    const message = error.response?.data?.message || error.message || '提交失败，请稍后再试'
    toast.error(message, 5000)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-6 sm:py-8 space-y-4 sm:space-y-6">
    <div v-if="loading" class="space-y-4 animate-fade-in">
      <div class="card-base p-6 space-y-4">
        <div class="h-5 w-32 skeleton" />
        <div class="h-4 w-48 skeleton" />
        <div class="h-2.5 w-full skeleton rounded-full" />
      </div>
      <div class="card-base p-6 space-y-4">
        <div class="h-6 w-72 skeleton" />
        <div class="space-y-3">
          <div v-for="i in 4" :key="i" class="h-12 skeleton rounded-2xl" />
        </div>
      </div>
    </div>

    <template v-else>
      <section class="card-base p-5 sm:p-6 space-y-4 animate-fade-in">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="inline-flex items-center gap-2 text-xs font-medium text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full mb-2">
              <Icon name="list" :size="14" />
              基础测试
            </div>
            <h1 class="page-title">40 题基础测试</h1>
            <p class="text-sm text-text-secondary mt-1">只看总进度，不显示维度名。</p>
          </div>

          <div class="text-right text-xs text-text-secondary">
            <p>第 {{ currentQuestionNumber }} / {{ totalQuestions }} 题</p>
            <p v-if="isGuest" class="mt-1">访客答题</p>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs text-text-secondary">
            <span>总进度</span>
            <span>{{ progressPercent }}%</span>
          </div>
          <div class="h-2 rounded-full bg-maple-50 overflow-hidden">
            <div class="h-full rounded-full bg-maple-500 transition-all duration-300" :style="{ width: `${progressPercent}%` }" />
          </div>
        </div>

        <div v-if="isGuest" class="rounded-2xl border border-maple-100 bg-maple-50/50 p-4 space-y-3">
          <div class="flex items-center gap-2 text-sm font-medium text-text-primary">
            <Icon name="user" :size="16" class="text-maple-500" />
            访客昵称
          </div>
          <input
            v-model="visitorName"
            class="input-base"
            maxlength="30"
            placeholder="填写一个展示昵称"
            autocomplete="nickname"
          />
        </div>
      </section>

      <section v-if="currentQuestion" class="card-base p-5 sm:p-6 space-y-4 min-h-[420px]">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs text-text-secondary mb-2">{{ questionTag(currentQuestion) }}</p>
            <h2 class="text-xl font-semibold text-text-primary leading-8">{{ currentQuestion.question_text }}</h2>
          </div>
          <span class="text-xs text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full flex-shrink-0">
            {{ currentQuestion.question_type === 'multi_select' ? '可多选' : '单项选择' }}
          </span>
        </div>

        <div class="space-y-3">
          <button
            v-for="option in currentQuestion.options || []"
            :key="questionOptionId(option)"
            class="w-full rounded-2xl border px-4 py-3 text-left transition-all min-h-[56px]"
            :class="isOptionSelected(currentQuestion, questionOptionId(option))
              ? 'border-maple-400 bg-maple-50 shadow-card text-maple-700'
              : 'border-border bg-white hover:border-maple-200 hover:bg-maple-50/40 text-text-primary'"
            :aria-pressed="isOptionSelected(currentQuestion, questionOptionId(option))"
            @click="setAnswer(currentQuestion, questionOptionId(option))"
          >
            <div class="flex items-start gap-3">
              <div
                class="mt-0.5 w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0"
                :class="isOptionSelected(currentQuestion, questionOptionId(option)) ? 'border-maple-500 bg-maple-500' : 'border-maple-200 bg-white'"
              >
                <Icon v-if="isOptionSelected(currentQuestion, questionOptionId(option))" name="check" :size="12" class="text-white" />
              </div>
              <div class="min-w-0">
                <p class="font-medium leading-6">{{ questionOptionText(option) }}</p>
                <p v-if="option.hint" class="text-xs text-text-secondary mt-1">{{ option.hint }}</p>
              </div>
            </div>
          </button>
        </div>

        <div class="flex items-center justify-between gap-3 pt-2">
          <button class="btn-secondary px-4 min-h-[44px]" :disabled="currentQuestionIndex === 0" @click="goPrevious">
            <Icon name="chevronLeft" :size="16" />
            上一题
          </button>

          <div class="flex items-center gap-2">
            <button
              v-if="currentQuestionIndex < questions.length - 1"
              class="btn-primary px-4 min-h-[44px]"
              :disabled="!canSubmitCurrent"
              @click="goNext"
            >
              下一题
              <Icon name="chevronRight" :size="16" />
            </button>
            <button
              v-else
              class="btn-primary px-4 min-h-[44px]"
              :disabled="submitting || !canSubmitAll || (isGuest && !visitorName.trim())"
              @click="submitTest"
            >
              <Icon v-if="submitting" name="loader" :size="16" class="animate-spin" />
              <Icon v-else name="checkCircle" :size="16" />
              提交测试
            </button>
          </div>
        </div>
      </section>
    </template>
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
