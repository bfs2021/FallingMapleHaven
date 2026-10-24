<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import AvatarImage from '@/components/AvatarImage.vue'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'

const authStore = useAuthStore()

const nickname = ref('')
const bio = ref('')
const email = ref('')
const real_name = ref('')
const show_real_name = ref(false)
const visitor_public = ref(true)
const profileSaving = ref(false)
const profileError = ref('')

const oldPassword = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')
const passwordSaving = ref(false)
const passwordError = ref('')

const showPassword = ref(false)
const avatarUploading = ref(false)
const toast = useToast()
const coverUploading = ref(false)
const avatarError = ref('')
const coverError = ref('')

onMounted(() => {
  if (authStore.user) {
    nickname.value = authStore.user.nickname || ''
    bio.value = authStore.user.bio || ''
    email.value = authStore.user.email || ''
    real_name.value = authStore.user.real_name || ''
    show_real_name.value = authStore.user.show_real_name ?? false
    visitor_public.value = authStore.user.visitor_public ?? true
  }
})

function triggerUpload(type) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    if (type === 'avatar') {
      avatarUploading.value = true
      avatarError.value = ''
      try {
        const res = await authApi.uploadAvatar(file)
        authStore.user = { ...authStore.user, ...res.data }
        toast.success('头像已更新')
      } catch (e) {
        avatarError.value = e.response?.data?.message || '头像上传失败'
      } finally {
        avatarUploading.value = false
      }
    } else {
      coverUploading.value = true
      coverError.value = ''
      try {
        const res = await authApi.uploadCover(file)
        authStore.user = { ...authStore.user, ...res.data }
        toast.success('封面已更新')
      } catch (e) {
        coverError.value = e.response?.data?.message || '封面上传失败'
      } finally {
        coverUploading.value = false
      }
    }
  }
  input.click()
}

async function saveProfile() {
  profileSaving.value = true
  profileError.value = ''
  try {
    await authStore.updateProfile({
      nickname: nickname.value,
      bio: bio.value,
      email: email.value || undefined,
      real_name: real_name.value || undefined,
      show_real_name: show_real_name.value,
      visitor_public: visitor_public.value,
    })
    toast.success('个人资料已保存')
  } catch (e) {
    profileError.value = e.response?.data?.message || '保存失败'
  } finally {
    profileSaving.value = false
  }
}

async function changePassword() {
  passwordError.value = ''
  if (!oldPassword.value || !newPassword.value || !confirmNewPassword.value) {
    passwordError.value = '请填写所有密码字段'
    return
  }
  if (newPassword.value.length < 8) {
    passwordError.value = '新密码长度不能少于8位'
    return
  }
  if (newPassword.value !== confirmNewPassword.value) {
    passwordError.value = '两次新密码输入不一致'
    return
  }
  passwordSaving.value = true
  try {
    await authApi.changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    toast.success('密码修改成功')
    oldPassword.value = ''
    newPassword.value = ''
    confirmNewPassword.value = ''
  } catch (e) {
    passwordError.value = e.response?.data?.message || '修改密码失败'
  } finally {
    passwordSaving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 py-8 space-y-6">
    <h1 class="page-title">个人设置</h1>

    <!-- 头像与封面 -->
    <div class="card-section p-6 space-y-5">
      <h2 class="text-lg font-semibold text-text-primary">头像与封面</h2>

      <div class="relative w-full h-32 rounded-xl bg-maple-100 overflow-hidden">
        <img
          v-if="authStore.user?.cover_url"
          :src="authStore.user.cover_url"
          class="w-full h-full object-cover"
          alt="封面"
        />
        <div class="absolute inset-0 flex items-center justify-center">
          <button
            @click="triggerUpload('cover')"
            :disabled="coverUploading"
            class="px-4 py-2.5 bg-black/40 text-white text-sm rounded-lg hover:bg-black/50 transition-colors"
          >
            {{ coverUploading ? '上传中...' : '更换封面' }}
          </button>
        </div>
      </div>

      <div class="flex items-end gap-4 -mt-10 relative z-10">
        <div class="rounded-full border-4 border-white overflow-hidden flex-shrink-0">
          <AvatarImage :user="authStore.user" size="2xl" />
        </div>
        <button
          @click="triggerUpload('avatar')"
          :disabled="avatarUploading"
          class="btn-primary px-4"
        >
          {{ avatarUploading ? '上传中...' : '更换头像' }}
        </button>
      </div>
      <p v-if="avatarError" class="text-sm text-error-500">{{ avatarError }}</p>
      <p v-if="coverError" class="text-sm text-error-500">{{ coverError }}</p>
    </div>

    <!-- 资料编辑 -->
    <div class="card-section p-6 space-y-5">
      <h2 class="text-lg font-semibold text-text-primary">个人资料</h2>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">昵称</label>
        <input v-model="nickname" type="text" class="input-base" />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">个人签名</label>
        <textarea v-model="bio" rows="3" class="input-base resize-none" />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">邮箱</label>
        <input v-model="email" type="email" class="input-base" />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">真实姓名</label>
        <input v-model="real_name" type="text" class="input-base" />
      </div>
      <label class="flex items-center gap-3 py-1 w-fit cursor-pointer select-none">
        <span class="text-sm font-medium text-text-primary">公开真实姓名</span>
        <ToggleSwitch v-model="show_real_name" />
      </label>
      <label class="flex items-center gap-3 py-1 w-fit cursor-pointer select-none">
        <span class="text-sm font-medium text-text-primary">足迹对外可见</span>
        <ToggleSwitch v-model="visitor_public" />
      </label>

      <div class="flex items-center gap-3">
        <button
          @click="saveProfile"
          :disabled="profileSaving"
          class="btn-primary px-6"
        >
          {{ profileSaving ? '保存中...' : '保存' }}
        </button>
      </div>
      <p v-if="profileError" class="text-sm text-error-500">{{ profileError }}</p>
    </div>

    <!-- 主页模块 -->
    <RouterLink
      to="/settings/modules"
      class="card-base p-6 flex items-center justify-between group hover:border-maple-300"
    >
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-maple-50 flex items-center justify-center">
          <Icon name="layout" :size="20" class="text-maple-600" />
        </div>
        <div>
          <div class="text-sm font-medium text-text-primary">主页模块管理</div>
          <div class="text-xs text-text-secondary mt-0.5">控制主页上显示哪些模块</div>
        </div>
      </div>
      <Icon name="chevronRight" :size="18" class="text-text-secondary group-hover:text-maple-600 transition-colors" />
    </RouterLink>

    <!-- 修改密码 -->
    <div class="card-section p-6 space-y-5">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-text-primary">修改密码</h2>
        <button
          type="button"
          @click="showPassword = !showPassword"
          class="text-text-secondary hover:text-maple-600 transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-maple-50"
          :aria-label="showPassword ? '隐藏密码' : '显示密码'"
        >
          <Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="18" />
        </button>
      </div>

      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">旧密码</label>
        <input v-model="oldPassword" :type="showPassword ? 'text' : 'password'" class="input-base" />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">新密码</label>
        <input v-model="newPassword" :type="showPassword ? 'text' : 'password'" placeholder="至少8位" class="input-base" />
      </div>
      <div>
        <label class="block text-sm font-medium text-text-primary mb-1.5">确认新密码</label>
        <input v-model="confirmNewPassword" :type="showPassword ? 'text' : 'password'" class="input-base" />
      </div>

      <p v-if="passwordError" class="text-error-500 text-sm">{{ passwordError }}</p>

      <button
        @click="changePassword"
        :disabled="passwordSaving"
        class="btn-primary px-6"
      >
        {{ passwordSaving ? '修改中...' : '修改密码' }}
      </button>
    </div>
  </div>
</template>
