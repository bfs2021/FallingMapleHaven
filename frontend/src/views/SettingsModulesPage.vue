<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'

const authStore = useAuthStore()
const toast = useToast()

const modules = ref([
  { key: 'show_plugin_area', label: '插件入口区', desc: '在主页显示互动工具卡片', icon: 'puzzle', enabled: true },
  { key: 'show_visitors', label: '访客足迹', desc: '在主页显示访客记录标签页', icon: 'users', enabled: true },
])

const saving = ref(false)

onMounted(() => {
  const config = authStore.user?.layout_config || {}
  modules.value.forEach(m => {
    if (config[m.key] !== undefined) {
      m.enabled = config[m.key]
    }
  })
})

async function toggleModule(mod) {
  mod.enabled = !mod.enabled
  saving.value = true
  try {
    const layout_config = {}
    modules.value.forEach(m => { layout_config[m.key] = m.enabled })
    await authStore.updateProfile({ layout_config })
    toast.success(`${mod.label}已${mod.enabled ? '开启' : '关闭'}`)
  } catch {
    mod.enabled = !mod.enabled
    toast.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 py-8">
    <h1 class="page-title">主页模块管理</h1>
    <p class="text-sm text-text-secondary mb-6">控制你的个人主页上显示哪些功能模块，修改即时生效。</p>

    <div class="space-y-3">
      <div
        v-for="mod in modules"
        :key="mod.key"
        class="card-base p-5 flex items-center justify-between"
      >
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-lg bg-maple-50 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Icon :name="mod.icon" :size="20" class="text-maple-600" />
          </div>
          <div>
            <div class="text-sm font-medium text-text-primary">{{ mod.label }}</div>
            <div class="text-xs text-text-secondary mt-0.5">{{ mod.desc }}</div>
          </div>
        </div>
        <ToggleSwitch
          :model-value="mod.enabled"
          :disabled="saving"
          @update:model-value="toggleModule(mod)"
        />
      </div>
    </div>

    <div class="mt-8 p-4 bg-maple-50 rounded-xl border border-maple-200">
      <div class="flex items-start gap-2">
        <Icon name="info" :size="18" class="text-maple-500 mt-0.5 flex-shrink-0" />
        <div>
          <p class="text-sm font-medium text-maple-800">固定显示模块</p>
          <p class="text-xs text-maple-600 mt-1">资料卡和动态时间线始终显示在个人主页上，不可关闭。</p>
        </div>
      </div>
    </div>
  </div>
</template>
