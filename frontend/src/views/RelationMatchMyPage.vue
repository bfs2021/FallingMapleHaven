<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { relationMatchApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'
import {
  buildRelationMatchAbsoluteUrl,
  normalizeRelationMatchQueryValue,
} from '@/utils/relationMatch'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const home = ref(null)
const loading = ref(true)
const busy = ref(false)
const matchCode = ref(normalizeRelationMatchQueryValue(route.query.shareCode))

const historyItems = computed(() => home.value?.history?.results || [])
const historyTotal = computed(() => home.value?.history?.total || 0)
const hasProfile = computed(() => Boolean(home.value?.has_profile))
const profileName = computed(() => home.value?.profile?.participant_name || '关系匹配')
const profileCode = computed(() => home.value?.profile?.share_code || '')
const profileUrl = computed(() => home.value?.profile?.share_url || '')
const profileAbsoluteUrl = computed(() => buildRelationMatchAbsoluteUrl(profileUrl.value))
const isAuthenticated = computed(() => authStore.isAuthenticated)
const inviteLabel = computed(() => {
  if (!hasProfile.value) return '尚未完成测试'
  if (historyTotal.value > 0) return '已生成画像'
  return '已完成测试'
})

watch(
  () => route.query.shareCode,
  (value) => {
    matchCode.value = normalizeRelationMatchQueryValue(value)
  },
)

onMounted(loadMy)

async function loadMy() {
  loading.value = true
  try {
    const res = await relationMatchApi.getMy()
    home.value = res.data || null
  } catch (error) {
    toast.error(error.response?.data?.message || '我的画像加载失败', 5000)
  } finally {
    loading.value = false
  }
}

function openTestFlow() {
  const code = matchCode.value.trim()
  router.push({
    name: 'RelationMatchJoinPage',
    query: code ? { shareCode: code } : {},
  })
}

async function startMatchByCode() {
  const code = matchCode.value.trim()
  if (!code) {
    toast.error('请输入匹配码', 4000)
    return
  }

  if (!hasProfile.value) {
    router.push({ name: 'RelationMatchJoinPage', query: { shareCode: code } })
    return
  }

  busy.value = true
  try {
    const res = await relationMatchApi.matchProfile(code, {
      participant_name: authStore.user?.nickname || authStore.user?.username || '',
    })
    const pairId = res.data?.pair_id ?? res.data?.id
    if (!pairId) {
      throw new Error('关系结果缺少 ID')
    }

    await router.replace({
      name: 'RelationMatchPairResultStandalone',
      params: { pairId },
    })
  } catch (error) {
    toast.error(error.response?.data?.message || '匹配失败，请检查短码后重试', 5000)
  } finally {
    busy.value = false
  }
}

async function copyText(text, successMessage) {
  if (!text) return

  try {
    if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
      throw new Error('clipboard unavailable')
    }
    await navigator.clipboard.writeText(text)
    toast.success(successMessage)
  } catch {
    toast.error('复制失败，请手动复制', 4000)
  }
}

function goToHistory(pairId) {
  router.push({
    name: 'RelationMatchPairResultStandalone',
    params: { pairId },
  })
}

function buildShareUrlWithCode() {
  return profileAbsoluteUrl.value || profileUrl.value || ''
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6 sm:py-8 space-y-4 sm:space-y-6">
    <div v-if="loading" class="space-y-4 animate-fade-in">
      <div class="card-base p-6 space-y-4">
        <div class="h-6 w-36 skeleton" />
        <div class="h-4 w-64 skeleton" />
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="h-24 skeleton rounded-2xl" />
          <div class="h-24 skeleton rounded-2xl" />
        </div>
      </div>
      <div class="card-base p-6 space-y-3">
        <div class="h-5 w-28 skeleton" />
        <div class="h-16 skeleton rounded-2xl" />
        <div class="h-10 skeleton rounded-xl" />
      </div>
    </div>

    <template v-else>
      <section class="card-base p-5 sm:p-6 space-y-5 animate-fade-in">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div class="space-y-2">
            <div class="inline-flex items-center gap-2 text-xs font-medium text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full">
              <Icon name="heartHandshake" :size="14" />
              {{ inviteLabel }}
            </div>
            <h1 class="page-title">我的画像</h1>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              v-if="profileCode"
              class="btn-secondary px-3 py-2 text-sm min-h-[44px]"
              @click="copyText(profileCode, '短码已复制')"
            >
              <Icon name="copy" :size="16" />
              复制短码
            </button>
            <button
              v-if="buildShareUrlWithCode()"
              class="btn-secondary px-3 py-2 text-sm min-h-[44px]"
              @click="copyText(buildShareUrlWithCode(), '链接已复制')"
            >
              <Icon name="link" :size="16" />
              复制链接
            </button>
            <button
              class="btn-primary px-4 py-2 text-sm min-h-[44px]"
              :disabled="busy"
              @click="openTestFlow"
            >
              <Icon name="arrowRight" :size="16" />
              开始测试
            </button>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-3">
          <div class="rounded-2xl border border-maple-100 bg-maple-50/50 p-4 min-h-[108px]">
            <p class="text-xs text-text-secondary mb-2">我的画像状态</p>
            <p class="font-semibold text-text-primary">{{ hasProfile ? profileName : '还没有完成' }}</p>
            <p class="text-sm text-text-secondary mt-1">{{ inviteLabel }}</p>
          </div>
          <div class="rounded-2xl border border-maple-100 bg-white p-4 min-h-[108px]">
            <p class="text-xs text-text-secondary mb-2">短匹配码</p>
            <p class="font-semibold text-maple-700 tracking-[0.2em]">
              {{ profileCode || '— — — — — —' }}
            </p>
            <p class="text-sm text-text-secondary mt-1">{{ profileCode ? '可直接分享给对方' : '完成测试后自动生成' }}</p>
          </div>
          <div class="rounded-2xl border border-maple-100 bg-white p-4 min-h-[108px]">
            <p class="text-xs text-text-secondary mb-2">分享链接</p>
            <p class="text-sm text-text-primary break-all leading-6">
              {{ buildShareUrlWithCode() || '完成测试后生成分享链接' }}
            </p>
          </div>
        </div>
      </section>

      <section class="card-base p-5 sm:p-6 space-y-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-text-primary">输入匹配码</h2>
          </div>
          <Icon name="hash" :size="18" class="text-maple-400" />
        </div>

        <div class="flex flex-col gap-3 sm:flex-row">
          <input
            v-model="matchCode"
            class="input-base flex-1"
            inputmode="numeric"
            autocomplete="off"
            maxlength="20"
            placeholder="输入对方给你的短匹配码"
          />
          <button class="btn-primary px-5 min-h-[44px]" :disabled="busy" @click="startMatchByCode">
            <Icon name="send" :size="16" />
            {{ hasProfile ? '直接匹配' : '去答题' }}
          </button>
        </div>

        <div v-if="!hasProfile" class="rounded-2xl border border-dashed border-maple-200 bg-maple-50/40 p-4">
          <p class="text-sm text-text-secondary mb-3">完成基础测试后，这里会展示你的画像状态、短码和分享链接。</p>
          <div class="flex flex-wrap gap-2">
            <button class="btn-primary px-4 py-2 min-h-[44px]" @click="openTestFlow">
              <Icon name="arrowRight" :size="16" />
              开始测试
            </button>
            <template v-if="!isAuthenticated">
              <RouterLink class="btn-secondary px-4 py-2 min-h-[44px] inline-flex items-center gap-2" :to="{ name: 'Login', query: { next: route.fullPath } }">
                登录
              </RouterLink>
              <RouterLink class="btn-ghost px-4 py-2 min-h-[44px] inline-flex items-center gap-2" :to="{ name: 'Register', query: { next: route.fullPath } }">
                注册
              </RouterLink>
            </template>
          </div>
        </div>
      </section>

      <section class="card-base p-5 sm:p-6 space-y-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-text-primary">匹配历史</h2>
          </div>
          <span class="text-xs text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full">{{ historyTotal }} 条</span>
        </div>

        <div v-if="historyItems.length" class="space-y-3">
          <button
            v-for="item in historyItems"
            :key="item.pair_id"
            class="w-full text-left rounded-2xl border border-border bg-white px-4 py-3 hover:border-maple-300 hover:shadow-card transition-all min-h-[72px]"
            @click="goToHistory(item.pair_id)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="font-medium text-text-primary truncate">
                  {{ item.other_participant_name }} · {{ item.relation_type_name }}
                </p>
                <p class="text-sm text-text-secondary mt-1 truncate">{{ item.subtitle }}</p>
              </div>
              <Icon name="chevronRight" :size="16" class="text-maple-300 mt-1" />
            </div>
          </button>
        </div>

        <div v-else class="rounded-2xl border border-dashed border-maple-200 bg-maple-50/30 px-4 py-8 text-center text-text-secondary">
          <Icon name="scrollText" :size="36" class="mx-auto mb-3 text-maple-200" />
          <p class="font-medium text-text-primary">还没有关系结果</p>
          <p class="text-sm mt-1">完成测试并和对方匹配后，这里会显示历史记录。</p>
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
