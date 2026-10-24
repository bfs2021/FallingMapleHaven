<script setup>
import { watch } from 'vue'
import { useConfirm } from '@/composables/useConfirm'
import Icon from '@/components/Icon.vue'

const { dialogState, resolveConfirm } = useConfirm()

function onKeydown(e) {
  if (e.key === 'Escape') resolveConfirm(false)
}

watch(() => dialogState.visible, (v) => {
  if (v) document.addEventListener('keydown', onKeydown)
  else document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div
        v-if="dialogState.visible"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4"
        @click.self="resolveConfirm(false)"
      >
        <div class="fixed inset-0 bg-black/40 backdrop-blur-sm" />
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          class="relative bg-white rounded-2xl shadow-modal p-6 w-full max-w-sm animate-scale-in"
        >
          <div class="flex items-center gap-3 mb-4">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
              :class="dialogState.variant === 'danger'
                ? 'bg-red-50 text-red-500'
                : 'bg-maple-50 text-maple-600'"
            >
              <Icon :name="dialogState.variant === 'danger' ? 'alertTriangle' : 'helpCircle'" :size="20" />
            </div>
            <h2 id="confirm-title" class="text-lg font-semibold text-text-primary">
              {{ dialogState.title }}
            </h2>
          </div>
          <p class="text-sm text-text-secondary mb-6 leading-relaxed">
            {{ dialogState.message }}
          </p>
          <div class="flex justify-end gap-3">
            <button
              class="btn-secondary px-4 py-2 cursor-pointer"
              @click="resolveConfirm(false)"
            >
              {{ dialogState.cancelText }}
            </button>
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 ease-out cursor-pointer select-none inline-flex items-center gap-1.5"
              :class="dialogState.variant === 'danger'
                ? 'bg-red-500 text-white hover:bg-red-600 active:bg-red-700 active:scale-[0.97]'
                : 'btn-primary'"
              @click="resolveConfirm(true)"
            >
              {{ dialogState.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-enter-active,
.confirm-leave-active {
  transition: all 0.2s ease-out;
}
.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}
.confirm-enter-from [role="alertdialog"] {
  transform: scale(0.92);
}
</style>
