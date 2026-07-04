<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { friendApi } from '@/api/friends'
import { quizApi, pluginApi } from '@/api/plugin'
import TabBar from '@/components/TabBar.vue'
import Icon from '@/components/Icon.vue'
import SelectField from '@/components/SelectField.vue'

const route = useRoute()
const authStore = useAuthStore()
const activeTab = ref('create')

const friends = ref([])
const selectedFriendId = ref(null)
const questionText = ref('')
const correctAnswer = ref('')
const createMessage = ref('')
const submitting = ref(false)

const receivedQuestions = ref([])
const loadingReceived = ref(false)
const answerText = ref({})

const matchFriendId = ref(null)
const matchResult = ref(null)
const loadingMatch = ref(false)

const leaderboard = ref({ rankings: [], avg_match_rate: 0, total_friends: 0 })
const loadingLeaderboard = ref(false)

onMounted(() => {
  fetchFriends()
  fetchReceived()
  fetchLeaderboard()
})

async function fetchFriends() {
  try {
    const res = await friendApi.list()
    friends.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchReceived() {
  loadingReceived.value = true
  try {
    const res = await quizApi.received()
    receivedQuestions.value = res.data || []
  } catch { /* ignore */ } finally {
    loadingReceived.value = false
  }
}

async function submitQuestion() {
  if (!selectedFriendId.value || !questionText.value.trim() || !correctAnswer.value.trim()) return
  submitting.value = true
  createMessage.value = ''
  try {
    await quizApi.create({
      target_user_id: selectedFriendId.value,
      question: questionText.value.trim(),
      correct_answer: correctAnswer.value.trim(),
    })
    createMessage.value = '出题成功!'
    questionText.value = ''
    correctAnswer.value = ''
    selectedFriendId.value = null
  } catch (e) {
    createMessage.value = e.response?.data?.detail || '出题失败'
  } finally {
    submitting.value = false
  }
}

async function submitAnswer(question) {
  const answer = answerText.value[question.id]
  if (!answer?.trim()) return
  try {
    const res = await quizApi.answer(question.id, answer.trim())
    question.has_answered = true
    question.is_correct = res.data?.is_correct
    question.result = res.data
  } catch { /* ignore */ }
}

async function fetchResult() {
  if (!matchFriendId.value) return
  loadingMatch.value = true
  try {
    const res = await quizApi.result(matchFriendId.value)
    matchResult.value = res.data
  } catch { /* ignore */ } finally {
    loadingMatch.value = false
  }
}

async function fetchLeaderboard() {
  loadingLeaderboard.value = true
  try {
    const res = await pluginApi.getQuizLeaderboard()
    leaderboard.value = res.data || { rankings: [], avg_match_rate: 0, total_friends: 0 }
  } catch { /* ignore */ } finally {
    loadingLeaderboard.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="page-title">默契问答</h1>

    <TabBar
      :tabs="[
        { key: 'create', label: '出题' },
        { key: 'answer', label: '答题' },
        { key: 'leaderboard', label: '好友排行' },
        { key: 'match', label: '匹配度' },
      ]"
      :activeKey="activeTab"
      @update:activeKey="activeTab = $event"
      class="mb-6"
    />

    <div v-if="activeTab === 'create'" class="space-y-4 max-w-lg">
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1">选择好友</label>
        <SelectField
          v-model="selectedFriendId"
          :options="friends.map(f => ({ value: f.id || f.user_id, label: f.nickname || f.username }))"
          placeholder="请选择好友"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1">题目</label>
        <input
          v-model="questionText"
          type="text"
          placeholder="输入题目..."
          class="input-base"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1">正确答案</label>
        <input
          v-model="correctAnswer"
          type="text"
          placeholder="输入正确答案..."
          class="input-base"
        />
      </div>
      <button
        @click="submitQuestion"
        :disabled="submitting || !selectedFriendId || !questionText.trim() || !correctAnswer.trim()"
        class="btn-primary px-5 py-2.5"
      >
        {{ submitting ? '提交中...' : '提交题目' }}
      </button>
      <p v-if="createMessage" class="text-sm" :class="createMessage.includes('成功') ? 'text-green-600' : 'text-red-500'">
        {{ createMessage }}
      </p>
    </div>

    <div v-if="activeTab === 'answer'" class="space-y-4">
      <div v-if="loadingReceived" class="space-y-4">
        <div v-for="i in 2" :key="i" class="card-base p-4 space-y-3">
          <div class="h-3 w-24 skeleton" />
          <div class="h-4 w-3/4 skeleton" />
          <div class="flex gap-2">
            <div class="flex-1 h-10 skeleton" />
            <div class="w-16 h-10 skeleton" />
          </div>
        </div>
      </div>
      <div v-else-if="!receivedQuestions.length" class="text-center py-12 text-text-secondary">
        <Icon name="helpCircle" :size="40" class="mx-auto mb-2 text-maple-300" />
        <p>暂未收到题目</p>
      </div>
      <div
        v-for="q in receivedQuestions"
        :key="q.id"
        class="card-base p-4 space-y-3"
      >
        <div class="text-sm text-text-secondary">来自: {{ q.from_user?.nickname || q.from_user?.username || '匿名' }}</div>
        <p class="text-sm font-medium text-text-primary">{{ q.question }}</p>
        <div v-if="!q.has_answered" class="flex gap-2">
          <input
            v-model="answerText[q.id]"
            type="text"
            placeholder="输入答案..."
            class="flex-1 input-base"
            @keyup.enter="submitAnswer(q)"
          />
          <button
            @click="submitAnswer(q)"
            class="btn-primary"
          >
            提交
          </button>
        </div>
        <div v-else class="text-sm font-medium" :class="q.is_correct ? 'text-green-600' : 'text-red-500'">
          {{ q.is_correct ? '回答正确!' : '回答错误' }}
          <span v-if="q.result?.correct_answer" class="text-text-secondary ml-2">正确答案: {{ q.result.correct_answer }}</span>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'leaderboard'" class="space-y-4">
      <div v-if="loadingLeaderboard" class="space-y-3">
        <div v-for="i in 4" :key="i" class="card-base px-4 py-3 flex items-center gap-3">
          <div class="w-7 h-5 skeleton" />
          <div class="w-8 h-8 rounded-full skeleton" />
          <div class="flex-1 h-4 skeleton" />
          <div class="w-16 h-4 skeleton" />
        </div>
      </div>
      <div v-else-if="!leaderboard.rankings?.length" class="text-center py-12">
        <Icon name="trophy" :size="48" class="mx-auto mb-3 text-maple-300" />
        <p class="text-text-secondary mb-4">还没有答题记录</p>
        <button @click="activeTab = 'create'" class="btn-primary px-5 py-2.5">去出题</button>
      </div>
      <template v-else>
        <div class="card-base divide-y divide-border overflow-hidden">
          <div
            v-for="item in leaderboard.rankings"
            :key="item.friend_id"
            class="flex items-center gap-3 px-4 py-3 hover:bg-maple-50/40 transition-colors"
          >
            <div class="w-7 text-center">
              <span v-if="item.rank === 1" class="text-lg">🥇</span>
              <span v-else-if="item.rank === 2" class="text-lg">🥈</span>
              <span v-else-if="item.rank === 3" class="text-lg">🥉</span>
              <span v-else class="text-sm font-medium text-text-secondary">{{ item.rank }}</span>
            </div>
            <div class="w-8 h-8 rounded-full bg-maple-100 overflow-hidden flex items-center justify-center text-xs font-bold flex-shrink-0">
              <img v-if="item.avatar_url" :src="item.avatar_url" class="w-full h-full object-cover" />
              <span v-else class="text-maple-600">{{ item.nickname?.[0]?.toUpperCase() || '?' }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <span class="text-sm font-medium text-text-primary truncate">{{ item.nickname }}</span>
            </div>
            <div class="text-right">
              <div class="text-sm font-bold text-maple-600">{{ item.match_score }}%</div>
              <div class="text-tag text-text-secondary">共 {{ item.total_questions }} 题</div>
            </div>
          </div>
        </div>
        <div class="text-center text-sm text-text-secondary py-3 card-base">
          平均匹配度：<span class="font-medium text-maple-600">{{ leaderboard.avg_match_rate }}%</span>
          ｜已与 <span class="font-medium">{{ leaderboard.total_friends }}</span> 位好友答题
        </div>
      </template>
    </div>

    <div v-if="activeTab === 'match'" class="space-y-4 max-w-lg">
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1">选择好友查看匹配度</label>
        <SelectField
          v-model="matchFriendId"
          :options="friends.map(f => ({ value: f.id || f.user_id, label: f.nickname || f.username }))"
          placeholder="请选择好友"
          @update:model-value="fetchResult"
        />
      </div>
      <div v-if="loadingMatch" class="card-base p-6 flex items-center justify-center">
        <div class="h-4 w-32 skeleton" />
      </div>
      <div v-else-if="matchResult" class="card-base p-6 text-center space-y-3">
        <div class="text-4xl font-bold text-maple-600">{{ matchResult.match_score || 0 }}%</div>
        <div class="text-sm text-text-secondary">匹配度</div>
        <div class="flex justify-center gap-6 text-sm text-text-secondary">
          <span>总题数: {{ matchResult.total_questions || 0 }}</span>
          <span>正确数: {{ matchResult.correct_count || 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
