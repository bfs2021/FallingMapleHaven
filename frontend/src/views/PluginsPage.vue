<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { pluginApi } from '@/api/plugin'
import { adminApi } from '@/api/admin'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const authStore = useAuthStore()
const plugins = ref([])
const loading = ref(true)

const iconMap = {
  'help-circle': 'helpCircle',
  'message-question': 'messageCircleMore',
  'message-square': 'messageSquare',
}

async function fetchPlugins() {
  try {
    const res = await pluginApi.getSummary()
    plugins.value = res.data || []
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function goToPlugin(plugin) {
  if (plugin.route && plugin.is_active) {
    router.push(plugin.route)
  }
}

async function togglePlugin(plugin) {
  if (!authStore.isAdmin) return
  try {
    const res = await adminApi.plugins()
    const target = res.data?.find(p => p.type === plugin.type)
    if (target) {
      await adminApi.updatePlugin(target.id, { is_active: !plugin.is_active })
      plugin.is_active = !plugin.is_active
    }
  } catch { /* ignore */ }
}

const gridIcon = (icon) => iconMap[icon] || icon || 'gift'

onMounted(fetchPlugins)
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 py-8">
    <h1 class="page-title">互动工具</h1>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="card-base p-5 flex flex-col items-center text-center">
        <div class="w-10 h-10 rounded-lg skeleton mb-3" />
        <div class="h-5 w-24 skeleton mb-1" />
        <div class="h-4 w-36 skeleton" />
      </div>
    </div>

    <div v-else-if="!plugins.length" class="text-center py-16 text-text-secondary">
      <Icon name="puzzle" :size="48" class="mx-auto mb-3 text-maple-300" />
      <p class="font-medium">暂无可用插件</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="plugin in plugins"
        :key="plugin.type"
        class="card-base p-5 flex flex-col items-center text-center"
        :class="plugin.is_active
          ? 'cursor-pointer'
          : 'opacity-60'"
        @click="goToPlugin(plugin)"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
          :class="plugin.is_active ? 'bg-maple-50' : 'bg-gray-100'"
        >
          <Icon
            :name="gridIcon(plugin.icon)"
            :size="20"
            :class="plugin.is_active ? 'text-maple-600' : 'text-gray-400'"
          />
        </div>

        <div class="flex items-center gap-2 mb-1">
          <span class="font-medium text-text-primary">{{ plugin.name }}</span>
          <span
            v-if="!plugin.is_active"
            class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-text-secondary"
          >未启用</span>
        </div>

        <p class="text-sm text-text-secondary line-clamp-2">{{ plugin.description }}</p>

        <div
          v-if="plugin.is_active && plugin.data"
          class="w-full mt-3 pt-3 border-t border-maple-100"
        >
          <template v-if="plugin.type === 'quiz'">
            <div class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs">
              <span class="text-maple-600 font-medium">
                匹配度 {{ plugin.data.avg_match_rate || 0 }}%
              </span>
              <span v-if="plugin.data.best_friend_name" class="text-text-secondary">
                最佳: {{ plugin.data.best_friend_name }} ({{ plugin.data.best_match_rate }}%)
              </span>
            </div>
          </template>
          <template v-else-if="plugin.type === 'question_box'">
            <div class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs">
              <span class="text-maple-600 font-medium">
                {{ plugin.data.unanswered_count || 0 }} 条未答
              </span>
              <span class="text-text-secondary">
                共 {{ plugin.data.total_questions || 0 }} 条
              </span>
            </div>
          </template>
        </div>

        <button
          v-if="!plugin.is_active && authStore.isAdmin"
          @click.stop="togglePlugin(plugin)"
          class="mt-3 px-4 py-2 text-xs rounded-lg border border-maple-300 text-maple-600 hover:bg-maple-50 transition-colors active:scale-[0.97] min-h-[44px]"
        >
          启用
        </button>
      </div>
    </div>
  </div>
</template>
