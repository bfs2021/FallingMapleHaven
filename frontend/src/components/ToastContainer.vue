<script setup>
import { useToast } from '@/composables/useToast'
import Icon from '@/components/Icon.vue'

const { toasts, dismiss } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto px-4 py-2.5 rounded-lg shadow-float text-sm font-medium transition-all duration-300 flex items-center gap-2 max-w-sm animate-slide-in"
        :class="{
          'bg-green-600 text-white': toast.type === 'success',
          'bg-red-600 text-white': toast.type === 'error',
          'bg-gray-800 text-white': toast.type === 'info',
        }"
      >
        <span>{{ toast.message }}</span>
        <button
          @click="dismiss(toast.id)"
          aria-label="关闭"
          class="ml-auto text-white/70 hover:text-white cursor-pointer leading-none flex-shrink-0"
        >
          <Icon name="x" :size="14" />
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
</style>