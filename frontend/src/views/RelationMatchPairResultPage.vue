<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { relationMatchApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'
import {
  buildRelationMatchAbsoluteUrl,
  buildRelationMatchDimensionInsight,
  extractRelationMatchPairId,
  formatRelationMatchTendency,
  getRelationMatchTypeName,
  RELATION_MATCH_DIMENSIONS,
} from '@/utils/relationMatch'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const result = ref(null)
const loading = ref(true)

const ownerId = computed(() => route.params.userId)
const pairId = computed(() => route.params.pairId)
const homeTarget = computed(() => {
  if (route.params.userId) {
    return { name: 'RelationMatchPage', params: { userId: ownerId.value } }
  }
  if (authStore.isAuthenticated) {
    return { name: 'RelationMatchPage', params: { userId: authStore.user.user_id } }
  }
  return { name: 'RelationMatchMyPage' }
})
const shareUrl = computed(() => result.value?.share_url || route.fullPath)
const shareAbsoluteUrl = computed(() => buildRelationMatchAbsoluteUrl(shareUrl.value))
const profileA = computed(() => result.value?.profile_a || {})
const profileB = computed(() => result.value?.profile_b || {})
const dimensionRows = computed(() => buildDimensionRows(result.value))
const radarValuesA = computed(() => RELATION_MATCH_DIMENSIONS.map(item => getDimensionScore(profileA.value, result.value, item.key, 'a')))
const radarValuesB = computed(() => RELATION_MATCH_DIMENSIONS.map(item => getDimensionScore(profileB.value, result.value, item.key, 'b')))
const radarPathA = computed(() => buildRadarPath(radarValuesA.value))
const radarPathB = computed(() => buildRadarPath(radarValuesB.value))
const radarGrid = [0.32, 0.52, 0.72, 0.9]

watch(
  () => route.params.pairId,
  () => loadResult(),
)

onMounted(loadResult)

async function loadResult() {
  loading.value = true
  try {
    const res = await relationMatchApi.getPairResult(pairId.value)
    result.value = res.data || null
  } catch (error) {
    toast.error(error.response?.data?.message || '关系结果加载失败', 5000)
    result.value = null
  } finally {
    loading.value = false
  }
}

function getDisplayName(profile) {
  return profile?.participant_name || profile?.user?.nickname || profile?.user?.username || '未命名'
}

function getDimensionScore(profile, rawResult, key, side) {
  const direct = profile?.dimension_scores?.[key]
  if (typeof direct === 'number') return direct

  const compare = rawResult?.dimension_compare?.[key]
  if (compare && typeof compare === 'object') {
    const value = compare[side] ?? compare.value ?? compare.score ?? compare.points
    if (typeof value === 'number') return value
  }

  if (typeof compare === 'number') return compare
  return 5
}

function normalizeCompareItem(raw, key) {
  const base = RELATION_MATCH_DIMENSIONS.find(item => item.key === key) || { key, label: key }

  if (Array.isArray(raw)) {
    return {
      key,
      label: base.label,
      a: raw[0] ?? 0,
      b: raw[1] ?? 0,
      gap: typeof raw[3] === 'number' ? raw[3] : Math.abs((raw[0] ?? 0) - (raw[1] ?? 0)),
      shared: typeof raw[4] === 'number' ? raw[4] : Math.min(raw[0] ?? 0, raw[1] ?? 0),
      tendency: typeof raw[5] === 'string' ? raw[5] : ((raw[0] ?? 0) === (raw[1] ?? 0) ? 'equal' : (raw[0] ?? 0) > (raw[1] ?? 0) ? 'a' : 'b'),
      note: typeof raw[2] === 'string' ? raw[2] : '',
    }
  }

  if (raw && typeof raw === 'object') {
    return {
      key,
      label: base.label,
      a: raw.a ?? raw.left ?? raw.profile_a ?? raw.value_a ?? raw.score_a ?? raw.first ?? raw.user_a ?? 0,
      b: raw.b ?? raw.right ?? raw.profile_b ?? raw.value_b ?? raw.score_b ?? raw.second ?? raw.user_b ?? 0,
      gap: raw.gap ?? Math.abs((raw.a ?? raw.left ?? raw.profile_a ?? raw.value_a ?? raw.score_a ?? raw.first ?? raw.user_a ?? 0) - (raw.b ?? raw.right ?? raw.profile_b ?? raw.value_b ?? raw.score_b ?? raw.second ?? raw.user_b ?? 0)),
      shared: raw.shared ?? Math.min(
        raw.a ?? raw.left ?? raw.profile_a ?? raw.value_a ?? raw.score_a ?? raw.first ?? raw.user_a ?? 0,
        raw.b ?? raw.right ?? raw.profile_b ?? raw.value_b ?? raw.score_b ?? raw.second ?? raw.user_b ?? 0,
      ),
      tendency: raw.tendency || raw.direction || raw.side || ((raw.a ?? raw.left ?? raw.profile_a ?? raw.value_a ?? raw.score_a ?? raw.first ?? raw.user_a ?? 0) === (raw.b ?? raw.right ?? raw.profile_b ?? raw.value_b ?? raw.score_b ?? raw.second ?? raw.user_b ?? 0) ? 'equal' : (raw.a ?? raw.left ?? raw.profile_a ?? raw.value_a ?? raw.score_a ?? raw.first ?? raw.user_a ?? 0) > (raw.b ?? raw.right ?? raw.profile_b ?? raw.value_b ?? raw.score_b ?? raw.second ?? raw.user_b ?? 0) ? 'a' : 'b'),
      note: raw.note || raw.description || raw.summary || raw.explain || raw.text || '',
    }
  }

    return {
      key,
      label: base.label,
      a: 0,
      b: 0,
      gap: 0,
      shared: 0,
      tendency: 'equal',
      note: typeof raw === 'string' ? raw : '',
    }
}

function buildDimensionRows(rawResult) {
  const compare = rawResult?.dimension_compare || {}
  return RELATION_MATCH_DIMENSIONS.map((item) => normalizeCompareItem(compare[item.key], item.key))
}

function formatScore(score) {
  return `${Math.max(1, Math.min(10, Number(score) || 5))}/10`
}

function formatCompareTendency(tendency) {
  return formatRelationMatchTendency(tendency)
}

function buildCompareInsight(row) {
  return buildRelationMatchDimensionInsight(row)
}

function buildRadarPath(values) {
  const center = 100
  const radius = 72
  const step = (Math.PI * 2) / values.length
  return values
    .map((score, index) => {
      const angle = -Math.PI / 2 + step * index
      const pointRadius = radius * (Math.max(1, Math.min(10, Number(score) || 5)) / 10)
      const x = center + Math.cos(angle) * pointRadius
      const y = center + Math.sin(angle) * pointRadius
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

async function copyLink() {
  if (!shareAbsoluteUrl.value) return
  try {
    if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
      throw new Error('clipboard unavailable')
    }
    await navigator.clipboard.writeText(shareAbsoluteUrl.value)
    toast.success('结果链接已复制')
  } catch {
    toast.error('复制失败，请手动复制', 4000)
  }
}

function goHome() {
  router.push(homeTarget.value)
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-6 sm:py-8 space-y-4 sm:space-y-6">
    <div v-if="loading" class="space-y-4 animate-fade-in">
      <div class="card-base p-6 space-y-4">
        <div class="h-6 w-40 skeleton" />
        <div class="h-4 w-72 skeleton" />
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="h-24 skeleton rounded-2xl" />
          <div class="h-24 skeleton rounded-2xl" />
        </div>
      </div>
      <div class="card-base p-6 space-y-4">
        <div class="h-64 skeleton rounded-3xl" />
        <div class="h-20 skeleton rounded-2xl" />
        <div class="h-20 skeleton rounded-2xl" />
      </div>
    </div>

    <template v-else-if="result">
      <section class="card-base p-5 sm:p-6 space-y-5 animate-fade-in">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div class="space-y-2">
            <div class="inline-flex items-center gap-2 text-xs font-medium text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full">
              <Icon name="heartHandshake" :size="14" />
              关系结果
            </div>
            <h1 class="page-title">{{ getDisplayName(profileA) }} · {{ getDisplayName(profileB) }}</h1>
            <p class="text-sm text-text-secondary">{{ getRelationMatchTypeName(result.relation_type) }} / {{ result.subtitle }}</p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button class="btn-secondary px-3 py-2 text-sm min-h-[44px]" @click="copyLink">
              <Icon name="copy" :size="16" />
              复制链接
            </button>
            <button class="btn-primary px-3 py-2 text-sm min-h-[44px]" @click="goHome">
              <Icon name="arrowLeft" :size="16" />
              返回主页
            </button>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-2xl border border-maple-100 bg-white p-4 min-h-[104px]">
            <p class="text-xs text-text-secondary mb-2">参与者 A</p>
            <p class="text-lg font-semibold text-text-primary truncate">{{ getDisplayName(profileA) }}</p>
            <p class="text-sm text-text-secondary mt-1">{{ result.role_a }}</p>
          </div>
          <div class="rounded-2xl border border-maple-100 bg-white p-4 min-h-[104px]">
            <p class="text-xs text-text-secondary mb-2">参与者 B</p>
            <p class="text-lg font-semibold text-text-primary truncate">{{ getDisplayName(profileB) }}</p>
            <p class="text-sm text-text-secondary mt-1">{{ result.role_b }}</p>
          </div>
        </div>

        <div class="rounded-3xl border border-maple-100 bg-gradient-to-br from-maple-50/70 to-white p-5 sm:p-6 space-y-4">
          <div class="flex flex-col gap-1">
            <p class="text-xs text-maple-700 font-medium">关系类型</p>
            <h2 class="text-2xl font-semibold text-text-primary">{{ getRelationMatchTypeName(result.relation_type) }}</h2>
            <p class="text-sm text-text-secondary">{{ result.subtitle }}</p>
          </div>

          <p v-if="result.relation_explain" class="text-sm text-text-primary leading-7">{{ result.relation_explain }}</p>
        </div>
      </section>

      <section class="card-base p-5 sm:p-6 space-y-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-text-primary">八维对比</h2>
          </div>
          <Icon name="barChart" :size="18" class="text-maple-400" />
        </div>

        <div class="grid gap-5 lg:grid-cols-[1.1fr_0.9fr] items-start">
          <div class="rounded-3xl border border-maple-100 bg-white p-4 sm:p-5">
            <div class="flex items-center justify-between text-xs text-text-secondary mb-3">
              <span>{{ getDisplayName(profileA) }}</span>
              <span>{{ getDisplayName(profileB) }}</span>
            </div>

            <div class="relative mx-auto w-full max-w-[320px] aspect-square">
              <svg viewBox="0 0 200 200" class="w-full h-full">
                <g v-for="ring in radarGrid" :key="ring">
                  <polygon
                    :points="RELATION_MATCH_DIMENSIONS.map((_, index) => {
                      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / RELATION_MATCH_DIMENSIONS.length
                      const x = 100 + Math.cos(angle) * 72 * ring
                      const y = 100 + Math.sin(angle) * 72 * ring
                      return `${x.toFixed(1)},${y.toFixed(1)}`
                    }).join(' ')"
                    fill="none"
                    stroke="rgba(199, 59, 29, 0.12)"
                    stroke-width="1"
                  />
                </g>

                <g v-for="(dimension, index) in RELATION_MATCH_DIMENSIONS" :key="dimension.key">
                  <line
                    x1="100"
                    y1="100"
                    :x2="100 + Math.cos(-Math.PI / 2 + (Math.PI * 2 * index) / RELATION_MATCH_DIMENSIONS.length) * 72"
                    :y2="100 + Math.sin(-Math.PI / 2 + (Math.PI * 2 * index) / RELATION_MATCH_DIMENSIONS.length) * 72"
                    stroke="rgba(199, 59, 29, 0.12)"
                    stroke-width="1"
                  />
                </g>

                <polygon :points="radarPathA" fill="rgba(199, 59, 29, 0.18)" stroke="rgba(199, 59, 29, 0.7)" stroke-width="2" />
                <polygon :points="radarPathB" fill="rgba(245, 166, 35, 0.18)" stroke="rgba(245, 166, 35, 0.9)" stroke-width="2" />
              </svg>

              <div
                v-for="(dimension, index) in RELATION_MATCH_DIMENSIONS"
                :key="dimension.key"
                class="absolute text-center"
                :style="(() => {
                  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / RELATION_MATCH_DIMENSIONS.length
                  const x = 50 + Math.cos(angle) * 44
                  const y = 50 + Math.sin(angle) * 44
                  return { left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }
                })()"
              >
                <span class="block text-[11px] font-medium text-text-primary whitespace-nowrap">{{ dimension.label }}</span>
              </div>
            </div>

            <div class="mt-4 flex flex-wrap justify-center gap-3 text-xs text-text-secondary">
              <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-maple-500" />{{ getDisplayName(profileA) }}</span>
              <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-maple-400" />{{ getDisplayName(profileB) }}</span>
            </div>
          </div>

          <div class="space-y-3">
            <div
              v-for="row in dimensionRows"
              :key="row.key"
              class="rounded-2xl border border-border bg-white p-4 space-y-3"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="font-medium text-text-primary">{{ row.label }}</p>
                  <p class="text-xs text-text-secondary mt-1">{{ RELATION_MATCH_DIMENSIONS.find(item => item.key === row.key)?.hint }}</p>
                </div>
                <div class="text-xs text-text-secondary">
                  <span class="text-maple-700 font-medium">{{ formatScore(row.a) }}</span>
                  <span class="mx-1">/</span>
                  <span class="text-maple-500 font-medium">{{ formatScore(row.b) }}</span>
                </div>
              </div>

              <div class="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
                <div class="h-2 rounded-full bg-maple-50 overflow-hidden">
                  <div class="h-full rounded-full bg-maple-500" :style="{ width: `${Math.max(8, (Number(row.a) || 5) * 10)}%` }" />
                </div>
                <span class="text-xs text-text-secondary px-1">vs</span>
                <div class="h-2 rounded-full bg-maple-50 overflow-hidden">
                  <div class="h-full rounded-full bg-maple-400" :style="{ width: `${Math.max(8, (Number(row.b) || 5) * 10)}%` }" />
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                <span class="rounded-full bg-maple-50 px-2.5 py-1">共同值 {{ row.shared }}/10</span>
                <span class="rounded-full bg-maple-50 px-2.5 py-1">差值 {{ row.gap }}/10</span>
                <span class="rounded-full bg-maple-50 px-2.5 py-1">倾向 {{ formatCompareTendency(row.tendency) }}</span>
              </div>

              <p class="text-sm text-text-secondary leading-6">{{ buildCompareInsight(row) }}<span v-if="row.note"> {{ row.note }}</span></p>
            </div>
          </div>
        </div>
      </section>

      <section class="grid gap-4 lg:grid-cols-2">
        <div class="card-base p-5 sm:p-6 space-y-3">
          <div class="flex items-center gap-2">
            <Icon name="fileText" :size="18" class="text-maple-400" />
            <h2 class="text-lg font-semibold text-text-primary">双方摘要</h2>
          </div>
          <div class="space-y-3">
            <div class="rounded-2xl border border-border bg-white p-4">
              <p class="text-xs text-text-secondary mb-2">{{ getDisplayName(profileA) }}</p>
              <p class="text-sm leading-7 text-text-primary">{{ result.summary_a }}</p>
            </div>
            <div class="rounded-2xl border border-border bg-white p-4">
              <p class="text-xs text-text-secondary mb-2">{{ getDisplayName(profileB) }}</p>
              <p class="text-sm leading-7 text-text-primary">{{ result.summary_b }}</p>
            </div>
          </div>
        </div>

        <div class="card-base p-5 sm:p-6 space-y-3">
          <div class="flex items-center gap-2">
            <Icon name="sparkles" :size="18" class="text-maple-400" />
            <h2 class="text-lg font-semibold text-text-primary">相处亮点</h2>
          </div>
          <p class="text-sm leading-7 text-text-primary bg-white border border-border rounded-2xl p-4 min-h-[120px]">{{ result.highlight_text }}</p>
        </div>
      </section>

      <section class="card-base p-5 sm:p-6 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="info" :size="18" class="text-maple-400" />
          <h2 class="text-lg font-semibold text-text-primary">相处建议</h2>
        </div>
        <p class="text-sm leading-7 text-text-primary bg-white border border-border rounded-2xl p-4 min-h-[120px]">{{ result.advice_text }}</p>
      </section>
    </template>

    <div v-else class="card-base p-8 text-center space-y-3">
      <Icon name="alertCircle" :size="40" class="mx-auto text-maple-300" />
      <p class="font-medium text-text-primary">关系结果不存在</p>
      <p class="text-sm text-text-secondary">请检查链接是否正确。</p>
      <RouterLink class="btn-primary inline-flex items-center gap-2 px-4 py-2 min-h-[44px]" :to="homeTarget">
        返回主页
      </RouterLink>
    </div>
  </div>
</template>
