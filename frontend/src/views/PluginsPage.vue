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

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card-base p-5 flex items-center gap-4">
        <div class="w-10 h-10 rounded-lg skeleton" />
        <div class="flex-1 space-y-2">
          <div class="h-4 w-24 skeleton" />
          <div class="h-3 w-40 skeleton" />
        </div>
      </div>
    </div>

    <div v-else-if="!plugins.length" class="text-center py-16 text-text-secondary">
      <Icon name="puzzle" :size="48" class="mx-auto mb-3 text-maple-300" />
      <p class="font-medium">暂无可用插件</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="plugin in plugins"
        :key="plugin.type"
        class="card-base p-5 flex items-center gap-4"
        :class="plugin.is_active
          ? 'hover:-translate-y-0.5 cursor-pointer'
          : 'opacity-60'"
        @click="goToPlugin(plugin)"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="plugin.is_active ? 'bg-maple-50' : 'bg-gray-100'"
        >
          <Icon
            :name="gridIcon(plugin.icon)"
            :size="20"
            :class="plugin.is_active ? 'text-maple-600' : 'text-gray-400'"
          />
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-text-primary">{{ plugin.name }}</span>
            <span
              v-if="!plugin.is_active"
              class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-text-secondary"
            >未启用</span>
          </div>
          <p class="text-xs text-text-secondary mt-0.5 truncate">{{ plugin.description }}</p>

          <div v-if="plugin.is_active && plugin.data" class="flex items-center gap-4 mt-2">
            <template v-if="plugin.type === 'quiz'">
              <span class="text-xs text-maple-600 font-medium">
                平均匹配度 {{ plugin.data.avg_match_rate || 0 }}%
              </span>
              <span v-if="plugin.data.best_friend_name" class="text-xs text-text-secondary">
                最佳: {{ plugin.data.best_friend_name }} ({{ plugin.data.best_match_rate }}%)
              </span>
            </template>
            <template v-else-if="plugin.type === 'question_box'">
              <span class="text-xs text-maple-600 font-medium">
                {{ plugin.data.unanswered_count || 0 }} 条未答
              </span>
              <span class="text-xs text-text-secondary">
                共 {{ plugin.data.total_questions || 0 }} 条
              </span>
            </template>
          </div>
        </div>

        <div class="flex-shrink-0">
          <button
            v-if="!plugin.is_active && authStore.isAdmin"
            @click.stop="togglePlugin(plugin)"
            class="px-3 py-2 text-xs rounded-lg border border-maple-300 text-maple-600 hover:bg-maple-50 transition-colors active:scale-[0.97] min-h-[44px]"
          >
            启用
          </button>
          <Icon
            v-else-if="plugin.is_active"
            name="chevronRight"
            :size="18"
            class="text-text-secondary"
          />
        </div>
      </div>
    </div>
  </div>
</template>
