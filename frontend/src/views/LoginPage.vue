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
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.login(username.value, password.value)
    const redirect = route.query.next || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e.response?.data?.message || '登录失败'
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
        <p class="text-text-secondary text-center text-sm mb-8">登录你的账号</p>
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="login-username">用户名</label>
            <input
              id="login-username"
              v-model="username"
              type="text"
              placeholder="请输入用户名"
              class="input-base"
              autocomplete="username"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-text-primary mb-1.5" for="login-password">密码</label>
            <div class="relative">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                class="input-base !pr-10"
                autocomplete="current-password"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-maple-600 transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              >
                <Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="18" />
              </button>
            </div>
          </div>
          <Transition name="fade">
            <p v-if="error" class="text-error-500 text-sm flex items-center gap-1.5">
              <Icon name="alertCircle" :size="14" /> {{ error }}
            </p>
          </Transition>
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 btn-primary text-sm flex items-center justify-center gap-2"
          >
            <Icon v-if="loading" name="loader" :size="16" class="animate-spin" />
            <Icon v-else name="logIn" :size="16" />
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>
        <p class="text-center text-sm text-text-secondary mt-6">
          没有账号？
          <RouterLink
            :to="`/register${route.query.next ? '?next=' + encodeURIComponent(route.query.next) : ''}`"
            class="text-maple-600 hover:text-maple-700 font-medium transition-colors"
          >
            去注册
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
