<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Icon from '@/components/Icon.vue'
import { useToast } from '@/composables/useToast'

const authStore = useAuthStore()
const toast = useToast()
const router = useRouter()
const route = useRoute()

const username = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirm = ref(false)
const email = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  if (!username.value || !nickname.value || !password.value || !confirmPassword.value) {
    error.value = '请填写必填字段'
    return
  }
  if (password.value.length < 8) {
    error.value = '密码长度不能少于8位'
    return
  }
  if (!/[A-Za-z]/.test(password.value)) {
    error.value = '密码必须包含字母'
    return
  }
  if (!/\d/.test(password.value)) {
    error.value = '密码必须包含数字'
    return
  }
  if (!/[!@#$%^&*()_+\-=[\]{}|;':",./<>?`~]/.test(password.value)) {
    error.value = '密码必须包含至少一个特殊字符'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次密码输入不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.register({
      username: username.value,
      nickname: nickname.value,
      password: password.value,
      email: email.value || undefined,
    })
    toast.success('注册成功，欢迎加入！')
    const redirect = route.query.next || (authStore.user?.user_id ? `/profile/${authStore.user.user_id}` : '/')
    router.push(redirect)
  } catch (e) {
    error.value = e.response?.data?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center px-4 py-8">
    <div class="w-full max-w-sm animate-scale-in">
      <div class="bg-white rounded-2xl shadow-modal p-8">
        <div class="flex justify-center mb-4">
          <div class="w-14 h-14 rounded-2xl bg-maple-600 flex items-center justify-center text-white text-2xl font-bold shadow-float">枫</div>
        </div>
        <h1 class="text-xl font-bold text-text-primary text-center mb-1">FallingMapleHaven</h1>
        <p class="text-text-secondary text-center text-sm mb-8">创建你的账号</p>
        <form @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="reg-username">用户名 <span class="text-error-500">*</span></label>
            <input id="reg-username" v-model="username" type="text" placeholder="请输入用户名" class="input-base" autocomplete="username" />
          </div>
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="reg-nickname">昵称 <span class="text-error-500">*</span></label>
            <input id="reg-nickname" v-model="nickname" type="text" placeholder="请输入昵称" class="input-base" autocomplete="name" />
          </div>
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="reg-password">密码 <span class="text-error-500">*</span></label>
            <div class="relative">
              <input id="reg-password" v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="至少8位，需包含字母、数字和特殊字符" class="input-base !pr-10" autocomplete="new-password" />
              <button type="button" @click="showPassword = !showPassword" class="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-maple-600 transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center" :aria-label="showPassword ? '隐藏密码' : '显示密码'">
                <Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="18" />
              </button>
            </div>
            <p class="text-xs text-text-secondary mt-1.5 flex items-center gap-1">
              <Icon name="info" :size="12" /> 密码需至少8位，包含字母、数字和至少一个特殊字符
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="reg-confirm">确认密码 <span class="text-error-500">*</span></label>
            <div class="relative">
              <input id="reg-confirm" v-model="confirmPassword" :type="showConfirm ? 'text' : 'password'" placeholder="再次输入密码" class="input-base !pr-10" autocomplete="new-password" />
              <button type="button" @click="showConfirm = !showConfirm" class="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-maple-600 transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center" :aria-label="showConfirm ? '隐藏密码' : '显示密码'">
                <Icon :name="showConfirm ? 'eyeOff' : 'eye'" :size="18" />
              </button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="reg-email">邮箱 <span class="text-text-secondary">(可选)</span></label>
            <input id="reg-email" v-model="email" type="email" placeholder="example@mail.com" class="input-base" autocomplete="email" />
          </div>
          <Transition name="fade">
            <p v-if="error" class="text-error-500 text-sm flex items-center gap-1.5">
              <Icon name="alertCircle" :size="14" /> {{ error }}
            </p>
          </Transition>
          <button type="submit" :disabled="loading" class="w-full py-2.5 btn-primary text-sm flex items-center justify-center gap-2">
            <Icon v-if="loading" name="loader" :size="16" class="animate-spin" />
            <Icon v-else name="userPlus" :size="16" />
            {{ loading ? '注册中...' : '注册' }}
          </button>
        </form>
        <p class="text-center text-sm text-text-secondary mt-6">
          已有账号？
          <RouterLink
            :to="`/login${route.query.next ? '?next=' + encodeURIComponent(route.query.next) : ''}`"
            class="text-maple-600 hover:text-maple-700 font-medium transition-colors"
          >
            去登录
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
