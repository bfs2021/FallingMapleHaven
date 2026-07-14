<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { quizApi } from '@/api/plugin'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { confirm } = useConfirm()

const tests = ref([])
const currentTest = ref(null)
const leaderboard = ref(null)
const answers = ref({})
const visitorName = ref('')
const loading = ref(false)
const submitting = ref(false)
const creating = ref(false)
const actingId = ref(null)
const toast = useToast()

const ownerId = computed(() => Number(route.params.userId))
const testId = computed(() => route.params.testId ? Number(route.params.testId) : null)
const isLeaderboardRoute = computed(() => route.name === 'QuizTestLeaderboard')
const isOwner = computed(() => authStore.isAuthenticated && authStore.userId === ownerId.value)
const answeredCount = computed(() => Object.keys(answers.value).length)

onMounted(loadPage)

watch(
  () => [route.params.userId, route.params.testId, route.name, route.query.answerId],
  loadPage,
)

async function loadPage() {
  answers.value = {}
  if (testId.value) {
    await loadTestDetail()
    if (isLeaderboardRoute.value) await loadLeaderboard()
  } else {
    await loadTests()
  }
}

async function loadTests() {
  loading.value = true
  try {
    const res = isOwner.value ? await quizApi.myTests() : await quizApi.publicTests(ownerId.value)
    tests.value = res.data?.results || []
  } catch (error) {
    toast.error(error.response?.data?.message || '测试列表加载失败', 5000)
  } finally {
    loading.value = false
  }
}

async function loadTestDetail() {
  loading.value = true
  currentTest.value = null
  try {
    const res = await quizApi.publicTestDetail(testId.value)
    currentTest.value = res.data
  } catch (error) {
    toast.error(error.response?.data?.message || '测试加载失败', 5000)
  } finally {
    loading.value = false
  }
}

async function loadLeaderboard() {
  try {
    const res = await quizApi.leaderboard(testId.value, { answer_id: route.query.answerId })
    leaderboard.value = res.data
  } catch (error) {
    toast.error(error.response?.data?.message || '排行榜加载失败', 5000)
  }
}

async function createDraft() {
  creating.value = true
  try {
    const res = await quizApi.createTest({ title: '你有多了解我？', questions: [] })
    await router.push({ name: 'QuizTestEditor', params: { userId: ownerId.value, testId: res.data.id } })
  } catch (error) {
    toast.error(error.response?.data?.message || '创建测试失败', 5000)
  } finally {
    creating.value = false
  }
}

async function publishDraft(test) {
  actingId.value = test.id
  try {
    await quizApi.publishTest(test.id)
    toast.success('测试已发布')
    await loadTests()
  } catch (error) {
    const errors = error.response?.data?.data?.errors || []
    toast.error(errors[0]?.message || error.response?.data?.message || '发布失败', 5000)
  } finally {
    actingId.value = null
  }
}

async function deleteTest(test) {
  const ok = await confirm({
    title: '删除测试',
    message: '删除后该测试将从前台下线，历史答卷会保留。确认删除吗？',
    confirmText: '删除',
    variant: 'danger',
  })
  if (!ok) return
  actingId.value = test.id
  try {
    await quizApi.deleteTest(test.id)
    toast.success('测试已删除')
    await loadTests()
  } catch (error) {
    toast.error(error.response?.data?.message || '删除失败', 5000)
  } finally {
    actingId.value = null
  }
}

function editTest(id) {
  router.push({ name: 'QuizTestEditor', params: { userId: ownerId.value, testId: id } })
}

function selectAnswer(questionId, optionId) {
  answers.value = { ...answers.value, [questionId]: optionId }
}

async function submitAnswers() {
  if (!currentTest.value || answeredCount.value !== currentTest.value.question_count) return
  submitting.value = true
  try {
    const payload = {
      answers: currentTest.value.questions.map((question) => ({
        question_id: question.id,
        selected_option_id: answers.value[question.id],
      })),
    }
    if (!authStore.isAuthenticated) payload.participant_name = visitorName.value.trim()
    const res = await quizApi.submitTest(currentTest.value.id, payload)
    const answerId = res.data?.submission?.id
    await router.push({
      name: 'QuizTestLeaderboard',
      params: { userId: ownerId.value, testId: currentTest.value.id },
      query: answerId ? { answerId } : {},
    })
  } catch (error) {
    toast.error(error.response?.data?.message || '提交失败，请稍后再试', 5000)
  } finally {
    submitting.value = false
  }
}

function goToTest(id) {
  router.push({ name: 'QuizTestDetail', params: { userId: ownerId.value, testId: id } })
}

function goToLeaderboard(id, answerId = null) {
  router.push({
    name: 'QuizTestLeaderboard',
    params: { userId: ownerId.value, testId: id },
    query: answerId ? { answerId } : {},
  })
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8 space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="page-title mb-0">默契问答</h1>
      </div>
      <button
        v-if="testId"
        class="btn-secondary px-4 py-2"
        @click="router.push({ name: 'QuizPage', params: { userId: ownerId } })"
      >
        返回测试列表
      </button>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card-base p-5 space-y-3">
        <div class="h-5 w-1/2 skeleton" />
        <div class="h-4 w-3/4 skeleton" />
        <div class="h-10 w-full skeleton" />
      </div>
    </div>

    <template v-else-if="!testId">
      <div v-if="isOwner" class="card-base p-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-base font-semibold text-text-primary">管理我的测试</h2>
          <p class="text-sm text-text-secondary mt-1">最多保留 3 套未删除测试，草稿可继续编辑后发布。</p>
        </div>
        <button class="btn-primary px-4 py-2" type="button" :disabled="creating" @click="createDraft">
          {{ creating ? '创建中...' : '创建测试' }}
        </button>
      </div>

      <div v-if="!tests.length" class="card-base py-14 px-6 text-center">
        <Icon name="helpCircle" :size="44" class="mx-auto mb-3 text-maple-300" />
        <h2 class="text-lg font-semibold text-text-primary">还没有可参与的测试</h2>
        <p class="text-sm text-text-secondary mt-2">主页主人发布测试后，登录用户和访客都可以在这里答题。</p>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2">
        <article v-for="test in tests" :key="test.id" class="card-base p-5 flex flex-col gap-4">
          <div class="space-y-2">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-semibold text-text-primary truncate">{{ test.title }}</h2>
              <span class="text-xs text-maple-700 bg-maple-50 rounded-full px-2 py-1">
                {{ test.status === 'draft' ? '草稿' : '已发布' }} · {{ test.question_count }} 题
              </span>
            </div>
            <p class="text-sm text-text-secondary">已有 {{ test.submission_count }} 人提交</p>
          </div>
          <div v-if="isOwner" class="mt-auto grid grid-cols-2 gap-2">
            <button class="btn-secondary px-4 py-2" @click="editTest(test.id)">
              {{ test.status === 'draft' ? '编辑' : '查看' }}
            </button>
            <button
              v-if="test.status === 'draft'"
              class="btn-primary px-4 py-2"
              :disabled="actingId === test.id"
              @click="publishDraft(test)"
            >
              {{ actingId === test.id ? '处理中...' : '发布' }}
            </button>
            <button v-else class="btn-secondary px-4 py-2" @click="goToLeaderboard(test.id)">
              榜单
            </button>
            <button class="btn-ghost col-span-2 px-4 py-2 text-red-600" :disabled="actingId === test.id" @click="deleteTest(test)">
              删除测试
            </button>
          </div>
          <div v-else class="mt-auto flex gap-2">
            <button
              class="btn-primary flex-1 px-4 py-2"
              :disabled="test.has_submitted || isOwner"
              @click="goToTest(test.id)"
            >
              {{ test.has_submitted ? '已提交' : (isOwner ? '我的测试' : '开始答题') }}
            </button>
            <button class="btn-secondary px-4 py-2" @click="goToLeaderboard(test.id, test.my_submission_id)">
              榜单
            </button>
          </div>
        </article>
      </div>
    </template>

    <template v-else-if="currentTest && !isLeaderboardRoute">
      <div class="card-base p-5 space-y-2">
        <h2 class="text-xl font-semibold text-text-primary">{{ currentTest.title }}</h2>
        <p class="text-sm text-text-secondary">共 {{ currentTest.question_count }} 道单选题，提交后将进入答卷榜。</p>
      </div>

      <div v-if="currentTest.has_submitted" class="card-base p-5 text-center space-y-3">
        <Icon name="checkCircle" :size="44" class="mx-auto text-maple-400" />
        <p class="font-medium text-text-primary">你已经提交过这套测试</p>
        <button class="btn-primary px-4 py-2" @click="goToLeaderboard(currentTest.id, currentTest.my_submission_id)">
          查看答卷榜
        </button>
      </div>

      <div v-else-if="isOwner" class="card-base p-5 text-center text-text-secondary">
        主页主人不能参与自己的测试。
      </div>

      <form v-else class="space-y-4" @submit.prevent="submitAnswers">
        <div v-if="!authStore.isAuthenticated" class="card-base p-5 space-y-2">
          <label class="block text-sm font-medium text-text-primary">访客昵称</label>
          <input v-model="visitorName" maxlength="12" class="input-base" placeholder="请输入 12 字以内昵称" />
        </div>

        <section v-for="question in currentTest.questions" :key="question.id" class="card-base p-5 space-y-4">
          <div class="flex gap-3">
            <span class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-maple-100 text-sm font-semibold text-maple-700">
              {{ question.order }}
            </span>
            <h3 class="font-medium text-text-primary leading-7">{{ question.question_text }}</h3>
          </div>
          <div class="grid gap-2 sm:grid-cols-2">
            <button
              v-for="option in question.options"
              :key="option.id"
              type="button"
              class="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
              :class="answers[question.id] === option.id ? 'border-maple-500 bg-maple-50 text-maple-800' : 'border-border bg-white text-text-primary hover:border-maple-300'"
              @click="selectAnswer(question.id, option.id)"
            >
              {{ option.option_text }}
            </button>
          </div>
        </section>

        <button
          type="submit"
          class="btn-primary w-full justify-center py-2.5"
          :disabled="submitting || answeredCount !== currentTest.question_count || (!authStore.isAuthenticated && !visitorName.trim())"
        >
          {{ submitting ? '提交中...' : `提交答案 (${answeredCount}/${currentTest.question_count})` }}
        </button>
      </form>
    </template>

    <template v-else-if="currentTest && isLeaderboardRoute">
      <div class="card-base p-5 space-y-1">
        <p class="text-sm text-maple-600">答卷榜</p>
        <h2 class="text-xl font-semibold text-text-primary">{{ currentTest.title }}</h2>
      </div>

      <div v-if="!leaderboard?.leaderboard?.results?.length" class="card-base py-12 text-center text-text-secondary">
        暂无答卷记录
      </div>
      <div v-else class="card-base divide-y divide-border overflow-hidden">
        <div
          v-for="item in leaderboard.leaderboard.results"
          :key="item.id"
          class="flex items-center gap-3 px-4 py-4 bg-white"
        >
          <div class="w-10 text-center text-sm font-bold text-maple-700">#{{ item.rank }}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <p class="font-medium text-text-primary truncate">{{ item.participant_name }}</p>
              <span v-if="item.is_tied" class="text-xs text-maple-600 bg-maple-100 rounded-full px-2 py-0.5">并列</span>
              <span v-if="item.is_current" class="text-xs text-green-700 bg-green-50 rounded-full px-2 py-0.5">我的答卷</span>
            </div>
            <p class="text-xs text-text-secondary mt-1">{{ item.title }}</p>
          </div>
          <div class="text-right">
            <p class="font-semibold text-maple-700">{{ item.score_percent }}%</p>
            <p class="text-xs text-text-secondary">{{ item.correct_count }}/{{ item.total_count }}</p>
          </div>
        </div>
      </div>
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
