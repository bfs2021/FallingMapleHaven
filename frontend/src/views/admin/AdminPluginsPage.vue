<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import Icon from '@/components/Icon.vue'

const plugins = ref([])
const loading = ref(true)
const error = ref('')

async function fetchPlugins() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.plugins()
    plugins.value = res.data || []
  } catch {
    error.value = '插件列表加载失败'
  } finally {
    loading.value = false
  }
}

async function togglePlugin(plugin) {
  const nextActive = !plugin.is_active
  try {
    const res = await adminApi.updatePlugin(plugin.id, { is_active: nextActive })
    Object.assign(plugin, res.data)
  } catch {
    error.value = '插件状态更新失败'
  }
}

onMounted(fetchPlugins)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">插件管理</h2>
    <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card-base p-4 space-y-3">
        <div class="flex items-center justify-between">
          <div class="skeleton h-5 w-24" />
          <div class="skeleton h-5 w-10 rounded-full" />
        </div>
        <div class="skeleton h-4 w-20" />
        <div class="skeleton h-4 w-full" />
      </div>
    </div>

    <div v-else-if="!plugins.length" class="card-base p-10 flex flex-col items-center justify-center text-text-secondary gap-3">
      <Icon name="puzzle" :size="40" class="text-maple-200" />
      <p class="text-sm font-medium">暂无插件</p>
      <p class="text-xs text-text-secondary/60">安装插件后，他们将显示在此处</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="(plugin, i) in plugins"
        :key="plugin.id"
        class="card-base p-4 space-y-3 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 animate-fade-in"
        :style="{ animationDelay: `${i * 50}ms` }"
      >
        <div class="flex items-center justify-between">
          <h3 class="font-medium text-text-primary flex items-center gap-2">
            <Icon name="puzzle" :size="16" class="text-maple-500" />
            {{ plugin.name }}
          </h3>
          <ToggleSwitch
            :modelValue="plugin.is_active"
            @update:modelValue="togglePlugin(plugin)"
          />
        </div>
        <p class="text-xs text-text-secondary">类型: {{ plugin.type }}</p>
        <p class="text-xs text-text-secondary">{{ plugin.description || '暂无描述' }}</p>
      </div>
    </div>
  </div>
</template>
