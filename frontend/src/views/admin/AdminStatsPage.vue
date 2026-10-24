<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'

const stats = ref([
  { label: '总用户数', value: '--', icon: 'users', color: 'from-maple-500 to-maple-600' },
  { label: '日活跃用户', value: '--', icon: 'activity', color: 'from-success-500 to-success-600' },
  { label: '动态总数', value: '--', icon: 'fileText', color: 'from-purple-500 to-purple-600' },
  { label: '评论总数', value: '--', icon: 'messageCircle', color: 'from-blue-500 to-blue-600' },
  { label: '消息总数', value: '--', icon: 'send', color: 'from-orange-500 to-orange-600' },
])
const error = ref('')
const loading = ref(true)

const activeTab = ref(7)
const trendsData = ref(null)

const chartConfig = {
  '用户注册': { key: 'users', barClass: 'bg-gradient-to-r from-maple-400 to-maple-600' },
  '动态发布': { key: 'posts', barClass: 'bg-gradient-to-r from-purple-400 to-purple-600' },
  '消息发送': { key: 'messages', barClass: 'bg-gradient-to-r from-orange-400 to-orange-600' },
  '评论数':   { key: 'comments', barClass: 'bg-gradient-to-r from-blue-400 to-blue-600' },
  '访问数':   { key: 'visits', barClass: 'bg-gradient-to-r from-success-400 to-success-600' },
  '好友新增': { key: 'friendships', barClass: 'bg-gradient-to-r from-pink-400 to-pink-600' },
}

const currentTrends = computed(() => trendsData.value?.[activeTab.value])

function maxCount(key) {
  const items = currentTrends.value?.[key]
  if (!items?.length) return 1
  return Math.max(...items.map(i => i.count), 1)
}

onMounted(async () => {
  try {
    const res = await adminApi.stats()
    const data = res.data || {}
    stats.value = [
      { label: '总用户数', value: data.total_users ?? 0, icon: 'users', color: 'from-maple-500 to-maple-600' },
      { label: '日活跃用户', value: data.active_users_today ?? 0, icon: 'activity', color: 'from-success-500 to-success-600' },
      { label: '动态总数', value: data.total_posts ?? 0, icon: 'fileText', color: 'from-purple-500 to-purple-600' },
      { label: '评论总数', value: data.total_comments ?? 0, icon: 'messageCircle', color: 'from-blue-500 to-blue-600' },
      { label: '消息总数', value: data.total_messages ?? 0, icon: 'send', color: 'from-orange-500 to-orange-600' },
    ]
    loading.value = false
  } catch {
    error.value = '统计数据加载失败'
    loading.value = false
  }

  try {
    const [res7, res30] = await Promise.all([
      adminApi.trends(7),
      adminApi.trends(30),
    ])
    trendsData.value = { 7: res7.data, 30: res30.data }
  } catch {
    /* trends not critical */
  }
})

function switchTab(days) {
  activeTab.value = days
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="page-title">数据统计</h2>
    <p v-if="error" class="text-sm text-error-500">{{ error }}</p>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div v-for="i in 5" :key="i" class="rounded-xl border border-border p-5 flex items-center gap-4">
        <div class="skeleton w-12 h-12 rounded-lg shrink-0" />
        <div class="space-y-2 flex-1">
          <div class="skeleton h-7 w-16" />
          <div class="skeleton h-4 w-20" />
        </div>
      </div>
    </div>

    <div
      v-else
      class="grid grid-cols-1 sm:grid-cols-2 gap-4"
    >
      <div
        v-for="(stat, i) in stats"
        :key="stat.label"
        class="card-base p-5 flex items-center gap-4 hover:-translate-y-0.5 hover:scale-[1.02] transition-all duration-200 animate-fade-in"
        :style="{ animationDelay: `${i * 60}ms` }"
      >
        <div
          class="w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-white shadow-sm"
          :class="stat.color"
        >
          <Icon :name="stat.icon" :size="20" />
        </div>
        <div>
          <p class="text-2xl font-bold text-text-primary">{{ stat.value }}</p>
          <p class="text-sm text-text-secondary">{{ stat.label }}</p>
        </div>
      </div>
    </div>

    <h3 class="text-lg font-bold text-text-primary">趋势图表</h3>
    <div class="flex gap-2">
      <button
        @click="switchTab(7)"
        class="tab-btn"
        :class="activeTab === 7 ? 'tab-btn-active' : 'tab-btn-inactive'"
      >
        近7天
      </button>
      <button
        @click="switchTab(30)"
        class="tab-btn"
        :class="activeTab === 30 ? 'tab-btn-active' : 'tab-btn-inactive'"
      >
        近30天
      </button>
    </div>

    <div v-if="currentTrends" class="card-base p-6 space-y-6 animate-fade-in">
      <div v-for="(cfg, label) in chartConfig" :key="label" class="animate-fade-in" style="animationDelay: 50ms">
        <h4 class="text-sm font-medium text-text-primary mb-2">{{ label }}</h4>
        <div v-if="(currentTrends[cfg.key] || []).length === 0" class="text-xs text-text-secondary py-2">
          暂无数据
        </div>
        <div
          v-for="(item, j) in (currentTrends[cfg.key] || [])"
          :key="item.date"
          class="flex items-center gap-2 mb-1 animate-fade-in"
          :style="{ animationDelay: `${j * 30}ms` }"
        >
          <span class="text-xs text-text-secondary w-20 shrink-0">{{ item.date?.slice(5) }}</span>
          <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-700 ease-out"
              :class="cfg.barClass"
              :style="{ width: (item.count / maxCount(cfg.key) * 100) + '%' }"
            ></div>
          </div>
          <span class="text-xs text-text-secondary w-8 text-right shrink-0">{{ item.count }}</span>
        </div>
      </div>
    </div>
    <div v-else class="space-y-3">
      <div v-for="i in 3" :key="i" class="space-y-2">
        <div class="skeleton h-4 w-16" />
        <div v-for="j in 4" :key="j" class="flex items-center gap-2">
          <div class="skeleton h-5 w-20" />
          <div class="skeleton h-5 flex-1" />
          <div class="skeleton h-5 w-8" />
        </div>
      </div>
    </div>
  </div>
</template>
