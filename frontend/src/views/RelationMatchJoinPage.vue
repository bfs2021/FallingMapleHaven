<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { relationMatchApi } from '@/api/plugin'
import { useToast } from '@/composables/useToast'
import AvatarImage from '@/components/AvatarImage.vue'
import Icon from '@/components/Icon.vue'
import { isOwnRelationMatchShare, normalizeRelationMatchQueryValue } from '@/utils/relationMatch'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const loading = ref(false)
const shareCode = ref(normalizeRelationMatchQueryValue(route.query.shareCode))
const sharer = ref(null)
const shareError = ref(false)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const effectiveShareCode = computed(() => (shareError.value ? '' : shareCode.value.trim()))

watch(
  () => route.query.shareCode,
  (value) => {
    shareCode.value = normalizeRelationMatchQueryValue(value)
    loadShareInfo()
  },
)

onMounted(loadShareInfo)

async function loadShareInfo() {
  const code = shareCode.value.trim()
  if (!code) {
    sharer.value = null
    shareError.value = false
    loading.value = false
    return
  }

  loading.value = true
  shareError.value = false
  try {
    const [res, myRes] = await Promise.all([
      relationMatchApi.getShareInfo(code),
      relationMatchApi.getMy().catch(() => null),
    ])
    // 分享人自己打开自己的链接：回到自己的插件主页，不展示邀请页（Docs/16 §6.7）
    if (isOwnRelationMatchShare(myRes?.data, code)) {
      router.replace(buildSelfOpenTarget())
      return
    }
    sharer.value = res.data || null
  } catch (error) {
    sharer.value = null
    if (error.response?.data?.code === 40004) {
      shareError.value = true
    } else {
      toast.error(error.response?.data?.message || '分享信息加载失败', 5000)
    }
  } finally {
    loading.value = false
  }
}

function buildSelfOpenTarget() {
  if (authStore.isAuthenticated && authStore.user?.user_id) {
    return { name: 'RelationMatchPage', params: { userId: authStore.user.user_id } }
  }
  return { name: 'RelationMatchMyPage' }
}

function buildTestTarget() {
  const code = effectiveShareCode.value
  if (authStore.isAuthenticated) {
    return {
      name: 'RelationMatchTestPage',
      params: { userId: sharer.value?.user?.user_id || authStore.user.user_id },
      query: code ? { shareCode: code } : {},
    }
  }
  return {
    name: 'RelationMatchTestStandalone',
    query: code ? { shareCode: code } : {},
  }
}

function goToTest() {
  router.push(buildTestTarget())
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 py-6 sm:py-8 space-y-4 sm:space-y-6">
    <div v-if="loading" class="card-base p-6 space-y-4 animate-fade-in">
      <div class="flex items-center gap-4">
        <div class="w-24 h-24 rounded-full skeleton" />
        <div class="flex-1 space-y-2">
          <div class="h-5 w-40 skeleton" />
          <div class="h-4 w-64 skeleton" />
          <div class="h-4 w-52 skeleton" />
        </div>
      </div>
      <div class="h-16 skeleton rounded-2xl" />
      <div class="h-10 skeleton rounded-xl" />
    </div>

    <template v-else>
      <section v-if="shareCode && sharer" class="card-base p-5 sm:p-6 space-y-5 animate-fade-in">
        <div class="flex items-center gap-4">
          <AvatarImage :user="sharer.user || null" size="2xl" />
          <div class="min-w-0 space-y-1.5">
            <div class="inline-flex items-center gap-2 text-xs font-medium text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full">
              <Icon name="heartHandshake" :size="14" />
              关系匹配邀请
            </div>
            <h1 class="page-title">「{{ sharer.participant_name }}」邀请你一起测测你们像什么</h1>
            <p v-if="sharer.summary_text" class="text-sm text-text-secondary leading-6">{{ sharer.summary_text }}</p>
          </div>
        </div>
      </section>

      <section v-else-if="shareCode && shareError" class="card-base p-8 text-center space-y-3 animate-fade-in">
        <Icon name="alertCircle" :size="40" class="mx-auto text-maple-300" />
        <p class="font-medium text-text-primary">分享码无效或已失效</p>
        <p class="text-sm text-text-secondary">请向分享人确认短码是否正确，也可以先直接开始测试。</p>
        <button class="btn-primary inline-flex items-center gap-2 px-4 py-2 min-h-[44px] mx-auto" @click="goToTest">
          <Icon name="arrowRight" :size="16" />
          开始测试
        </button>
      </section>

      <section class="card-base p-5 sm:p-6 space-y-5 animate-fade-in">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 text-xs font-medium text-maple-700 bg-maple-50 px-2.5 py-1 rounded-full">
            <Icon name="heartHandshake" :size="14" />
            关系匹配
          </div>
          <h1 class="page-title">{{ shareCode && !shareError ? '测测你们像什么' : '看看你们像什么' }}</h1>
        </div>

        <div class="flex flex-wrap gap-2">
          <template v-if="isAuthenticated">
            <button class="btn-primary px-4 py-2 min-h-[44px]" @click="goToTest">
              <Icon name="arrowRight" :size="16" />
              开始测试
            </button>
          </template>
          <template v-else>
            <button class="btn-secondary px-4 py-2 min-h-[44px]" @click="goToTest">
              <Icon name="user" :size="16" />
              以访客身份答题
            </button>
            <RouterLink class="btn-secondary px-4 py-2 min-h-[44px] inline-flex items-center gap-2" :to="{ name: 'Login', query: { next: route.fullPath } }">
              登录
            </RouterLink>
            <RouterLink class="btn-ghost px-4 py-2 min-h-[44px] inline-flex items-center gap-2" :to="{ name: 'Register', query: { next: route.fullPath } }">
              注册
            </RouterLink>
          </template>
        </div>
      </section>
    </template>
  </div>
</template>
