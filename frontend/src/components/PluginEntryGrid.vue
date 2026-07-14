<script setup>
import Icon from './Icon.vue'

defineProps({
  plugins: { type: Array, default: () => [] },
})

const emit = defineEmits(['navigate'])

const iconMap = {
  'help-circle': 'helpCircle',
  'message-question': 'messageCircleMore',
  'message-square': 'messageSquare',
}

const gridIcon = (icon) => iconMap[icon] || icon || 'gift'
</script>

<template>
  <div class="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
    <button
      v-for="plugin in plugins"
      :key="plugin.route || plugin.type"
      @click="emit('navigate', plugin)"
      class="flex flex-col items-start gap-1.5 p-4 bg-white rounded-xl border border-border shadow-card hover:border-maple-300 hover:shadow-float transition-all flex-shrink-0 cursor-pointer min-h-[44px] w-44 text-left active:scale-[0.97]"
    >
      <div class="flex items-center gap-2 w-full">
        <Icon :name="gridIcon(plugin.icon)" :size="18" class="text-maple-600 flex-shrink-0" />
        <span class="text-sm font-medium text-text-primary truncate">{{ plugin.name }}</span>
      </div>

      <!-- Data summary -->
	      <div v-if="plugin.data" class="w-full space-y-0.5">
	        <template v-if="plugin.type === 'quiz'">
	          <p class="text-sm font-semibold text-maple-700 leading-snug line-clamp-2">
	            {{ plugin.data.entry_text || plugin.description || '来测测你有多了解我' }}
	          </p>
	          <p class="text-tag text-text-secondary leading-tight">
	            已发布 {{ plugin.data.published_test_count ?? 0 }} 套测试
	          </p>
	        </template>
        <template v-else-if="plugin.type === 'question_box'">
          <p class="text-lg font-bold text-maple-600 leading-tight">
            {{ plugin.data.unanswered_count ?? 0 }}
          </p>
          <p class="text-tag text-text-secondary leading-tight">
            未答 / 共 {{ plugin.data.total_questions ?? 0 }} 条
          </p>
        </template>
        <template v-else-if="plugin.type === 'guestbook'">
          <p class="text-lg font-bold text-maple-600 leading-tight">
            {{ plugin.data.total_messages ?? 0 }}
          </p>
          <p class="text-tag text-text-secondary leading-tight">条留言</p>
        </template>
        <template v-else>
          <p class="text-tag text-text-secondary leading-tight">{{ plugin.desc || '' }}</p>
        </template>
      </div>

      <div class="flex items-center gap-1 text-tag text-text-secondary mt-auto pt-1">
        <span>点击进入</span>
        <Icon name="chevronRight" :size="12" />
      </div>
    </button>
  </div>
</template>
