<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import Icon from '@/components/Icon.vue'

const settings = ref({
  allow_register: true,
  site_notice: '',
  site_name: 'FallingMapleHaven',
  site_logo: '',
  site_favicon: '',
  max_file_size: 50,
  allowed_extensions: '.jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.zip,.txt,.md,.csv,.xlsx,.pptx',
})
const saving = ref(false)
const loading = ref(true)
const saved = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    const res = await adminApi.settings()
    for (const item of res.data || []) {
      if (item.key in settings.value) {
        settings.value[item.key] = item.value
      }
    }
  } catch {
    error.value = '站点设置加载失败'
  } finally {
    loading.value = false
  }
})

async function saveSettings() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await adminApi.updateSettings(settings.value)
    saved.value = true
  } catch { /* ignore */ } finally {
    if (!saved.value) error.value = '站点设置保存失败'
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <h2 class="page-title">站点设置</h2>
    <p v-if="error" class="text-sm text-error-500">{{ error }}</p>

    <div v-if="loading" class="card-base p-6 max-w-lg space-y-5">
      <div v-for="i in 4" :key="i" class="space-y-2">
        <div class="skeleton h-4 w-24" />
        <div class="skeleton h-10 w-full" />
      </div>
    </div>

    <div v-else class="card-base p-6 max-w-lg space-y-5">
      <div class="flex items-center justify-between py-1">
        <span class="text-sm text-text-primary">允许新用户注册</span>
        <ToggleSwitch v-model="settings.allow_register" />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">网站名称</label>
        <input v-model="settings.site_name" type="text" class="input-base w-full" />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">站点公告</label>
        <textarea
          v-model="settings.site_notice"
          rows="4"
          placeholder="输入公告内容..."
          class="input-base w-full resize-none"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">站点 Logo (URL 路径)</label>
        <input v-model="settings.site_logo" type="text" placeholder="/static/logo.png" class="input-base w-full" />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">站点 Favicon (URL 路径)</label>
        <input v-model="settings.site_favicon" type="text" placeholder="/static/favicon.ico" class="input-base w-full" />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">最大文件上传大小 (MB)</label>
        <input v-model.number="settings.max_file_size" type="number" min="1" max="500" class="input-base w-full" />
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">允许上传文件扩展名</label>
        <input v-model="settings.allowed_extensions" type="text" class="input-base w-full" />
      </div>

      <div class="flex items-center gap-3 pt-2">
        <button @click="saveSettings" :disabled="saving" class="btn-primary cursor-pointer">
          <Icon name="check" :size="15" />
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
        <span v-if="saved" class="text-sm text-success-600 flex items-center gap-1">
          <Icon name="check" :size="14" /> 设置已保存
        </span>
      </div>
    </div>
  </div>
</template>
