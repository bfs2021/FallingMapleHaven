<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'
import { RELATION_MATCH_DIMENSIONS } from '@/utils/relationMatch'

const loading = ref(true)
const error = ref('')
const activeTab = ref('tests')
const tests = ref([])
const submissions = ref([])
const profiles = ref([])
const pairs = ref([])
const stats = ref(null)
const selectedSubmission = ref(null)
const submissionDetail = ref(null)
const detailLoading = ref(false)

const DIMENSION_LABELS = Object.fromEntries(
  RELATION_MATCH_DIMENSIONS.map(dimension => [dimension.key, dimension.label]),
)
const QUESTION_TYPE_LABELS = {
  single_choice: '单选',
  scale: '量表',
  multi_select: '多选',
  either_or: '二选一',
}

function questionTypeLabel(type) {
  return QUESTION_TYPE_LABELS[type] || type || '未知'
}

function formatDimensionPayload(payload) {
  if (!payload || typeof payload !== 'object') return ''
  return Object.entries(payload)
    .filter(([, value]) => Number(value) > 0)
    .map(([key, value]) => `${DIMENSION_LABELS[key] || key} +${value}`)
    .join('、')
}

async function openSubmission(item) {
  selectedSubmission.value = item
  detailLoading.value = true
  submissionDetail.value = null
  try {
    const res = await adminApi.relationMatchSubmissionDetail(item.id)
    submissionDetail.value = res.data || null
  } catch {
    error.value = '答卷详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

function closeSubmission() {
  selectedSubmission.value = null
  submissionDetail.value = null
  detailLoading.value = false
}

const tabList = [
  { key: 'tests', label: '测试' },
  { key: 'submissions', label: '答卷' },
  { key: 'profiles', label: '画像' },
  { key: 'pairs', label: '关系结果' },
  { key: 'stats', label: '统计' },
]

const statCards = computed(() => [
  { label: '测试总数', value: stats.value?.total_tests || 0 },
  { label: '已发布测试', value: stats.value?.published_tests || 0 },
  { label: '画像数', value: stats.value?.total_profiles || 0 },
  { label: '关系结果', value: stats.value?.total_pairs || 0 },
])

async function fetchAll() {
  loading.value = true
  error.value = ''
  try {
    const [testsRes, submissionsRes, profilesRes, pairsRes, statsRes] = await Promise.all([
      adminApi.relationMatchTests(),
      adminApi.relationMatchSubmissions(),
      adminApi.relationMatchProfiles(),
      adminApi.relationMatchPairs(),
      adminApi.relationMatchStats(),
    ])
    tests.value = testsRes.data?.results || []
    submissions.value = submissionsRes.data?.results || []
    profiles.value = profilesRes.data?.results || []
    pairs.value = pairsRes.data?.results || []
    stats.value = statsRes.data || null
  } catch {
    error.value = '关系匹配后台数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between gap-3">
      <h2 class="page-title">关系匹配管理</h2>
      <button class="btn-ghost px-3 py-2 min-h-[44px]" @click="fetchAll">
        <Icon name="refreshCw" :size="16" />
        刷新
      </button>
    </div>

    <p v-if="error" class="text-sm text-error-500">{{ error }}</p>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="card in statCards" :key="card.label" class="card-base p-4 space-y-1">
        <p class="text-xs text-text-secondary">{{ card.label }}</p>
        <p class="text-2xl font-semibold text-text-primary">{{ card.value }}</p>
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="tab in tabList"
        :key="tab.key"
        class="px-4 py-2 min-h-[44px] rounded-xl border text-sm transition-colors"
        :class="activeTab === tab.key ? 'border-maple-500 bg-maple-50 text-maple-700' : 'border-border bg-white text-text-secondary'"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="card-base p-6 space-y-3">
      <div class="skeleton h-6 w-40" />
      <div v-for="i in 4" :key="i" class="skeleton h-12 w-full rounded-2xl" />
    </div>

    <div v-else>
      <div v-if="activeTab === 'tests'" class="card-base overflow-hidden overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="table-header bg-maple-50/60 text-text-secondary">
            <tr>
              <th class="text-left px-4 py-3 font-medium">ID</th>
              <th class="text-left px-4 py-3 font-medium">标题</th>
              <th class="text-left px-4 py-3 font-medium">状态</th>
              <th class="text-left px-4 py-3 font-medium">题数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in tests" :key="item.id" class="border-t border-border">
              <td class="px-4 py-3 text-text-secondary">{{ item.id }}</td>
              <td class="px-4 py-3 font-medium text-text-primary">{{ item.title }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.status }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.question_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activeTab === 'submissions'">
        <div v-if="selectedSubmission" class="card-base p-5 sm:p-6 space-y-4">
          <div class="flex items-center justify-between gap-3">
            <div class="space-y-1">
              <p class="page-title">{{ selectedSubmission.participant_name }} 的答卷</p>
              <p class="text-sm text-text-secondary">
                参与者类型：{{ selectedSubmission.participant_type }} · 提交时间：{{ selectedSubmission.created_at }}
              </p>
            </div>
            <button class="btn-secondary px-3 py-2 min-h-[44px] text-sm" @click="closeSubmission">
              <Icon name="arrowLeft" :size="16" />
              返回列表
            </button>
          </div>

          <div v-if="detailLoading" class="space-y-3">
            <div class="skeleton h-5 w-48" />
            <div v-for="i in 4" :key="i" class="skeleton h-16 w-full rounded-2xl" />
          </div>

          <div v-else-if="submissionDetail" class="space-y-3">
            <div
              v-for="(answer, index) in submissionDetail.answers"
              :key="answer.id"
              class="rounded-2xl border border-border bg-white p-4 space-y-2"
            >
              <div class="flex items-start justify-between gap-3">
                <p class="text-sm font-medium text-text-primary leading-6">
                  <span class="text-maple-700 mr-1">{{ index + 1 }}.</span>{{ answer.question_text }}
                </p>
                <span class="text-xs text-maple-700 bg-maple-50 px-2 py-0.5 rounded-full flex-shrink-0">
                  {{ questionTypeLabel(answer.question_type) }}
                </span>
              </div>
              <p class="text-sm text-maple-700">
                选择：{{ (answer.selected_option_texts || []).join('、') || '—' }}
              </p>
              <p v-if="formatDimensionPayload(answer.dimension_payload)" class="text-xs text-text-secondary">
                八维贡献：{{ formatDimensionPayload(answer.dimension_payload) }}
              </p>
            </div>
          </div>
        </div>

        <div v-else class="card-base overflow-hidden overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="table-header bg-maple-50/60 text-text-secondary">
              <tr>
                <th class="text-left px-4 py-3 font-medium">ID</th>
                <th class="text-left px-4 py-3 font-medium">参与者</th>
                <th class="text-left px-4 py-3 font-medium">类型</th>
                <th class="text-left px-4 py-3 font-medium">时间</th>
                <th class="text-left px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in submissions" :key="item.id" class="border-t border-border">
                <td class="px-4 py-3 text-text-secondary">{{ item.id }}</td>
                <td class="px-4 py-3 font-medium text-text-primary">{{ item.participant_name }}</td>
                <td class="px-4 py-3 text-text-secondary">{{ item.participant_type }}</td>
                <td class="px-4 py-3 text-text-secondary">{{ item.created_at }}</td>
                <td class="px-4 py-3">
                  <button class="btn-ghost px-3 py-1.5 text-sm min-h-[36px]" @click="openSubmission(item)">
                    查看
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="activeTab === 'profiles'" class="card-base overflow-hidden overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="table-header bg-maple-50/60 text-text-secondary">
            <tr>
              <th class="text-left px-4 py-3 font-medium">ID</th>
              <th class="text-left px-4 py-3 font-medium">参与者</th>
              <th class="text-left px-4 py-3 font-medium">短码</th>
              <th class="text-left px-4 py-3 font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in profiles" :key="item.id" class="border-t border-border">
              <td class="px-4 py-3 text-text-secondary">{{ item.id }}</td>
              <td class="px-4 py-3 font-medium text-text-primary">{{ item.participant_name }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.share_code }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.created_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activeTab === 'pairs'" class="card-base overflow-hidden overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="table-header bg-maple-50/60 text-text-secondary">
            <tr>
              <th class="text-left px-4 py-3 font-medium">ID</th>
              <th class="text-left px-4 py-3 font-medium">类型</th>
              <th class="text-left px-4 py-3 font-medium">副标题</th>
              <th class="text-left px-4 py-3 font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pairs" :key="item.id" class="border-t border-border">
              <td class="px-4 py-3 text-text-secondary">{{ item.id }}</td>
              <td class="px-4 py-3 font-medium text-text-primary">{{ item.relation_type }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.subtitle }}</td>
              <td class="px-4 py-3 text-text-secondary">{{ item.created_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="grid gap-4 lg:grid-cols-2">
        <div class="card-base p-4 space-y-3">
          <h3 class="font-medium text-text-primary">测试状态</h3>
          <p class="text-sm text-text-secondary">总测试数：{{ stats?.total_tests || 0 }}</p>
          <p class="text-sm text-text-secondary">已发布：{{ stats?.published_tests || 0 }}</p>
          <p class="text-sm text-text-secondary">画像数：{{ stats?.total_profiles || 0 }}</p>
          <p class="text-sm text-text-secondary">关系结果：{{ stats?.total_pairs || 0 }}</p>
        </div>
        <div class="card-base p-4 space-y-3">
          <h3 class="font-medium text-text-primary">提交状态</h3>
          <p class="text-sm text-text-secondary">登录提交：{{ stats?.user_submissions || 0 }}</p>
          <p class="text-sm text-text-secondary">访客提交：{{ stats?.visitor_submissions || 0 }}</p>
          <p class="text-sm text-text-secondary">总提交：{{ stats?.total_submissions || 0 }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
