<script setup>
import {
  AlertDialogRoot,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogDescription,
} from 'reka-ui'
import { useConfirm } from '@/composables/useConfirm'
import Icon from '@/components/Icon.vue'

const { dialogState, resolveConfirm } = useConfirm()

function onOpenChange(visible) {
  if (!visible) resolveConfirm(false)
}
</script>

<template>
  <AlertDialogRoot :open="dialogState.visible" @update:open="onOpenChange">
    <AlertDialogPortal>
      <AlertDialogOverlay
        class="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm
               data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out"
      />
      <AlertDialogContent
        class="fixed inset-0 z-[60] m-auto h-fit w-full max-w-sm bg-white rounded-2xl shadow-modal p-6
               data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out"
      >
        <div class="flex items-center gap-3 mb-4">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
            :class="dialogState.variant === 'danger'
              ? 'bg-error-50 text-error-500'
              : 'bg-maple-50 text-maple-600'"
          >
            <Icon :name="dialogState.variant === 'danger' ? 'alertTriangle' : 'helpCircle'" :size="20" />
          </div>
          <AlertDialogTitle class="text-lg font-semibold text-text-primary">
            {{ dialogState.title }}
          </AlertDialogTitle>
        </div>
        <AlertDialogDescription class="text-sm text-text-secondary mb-6 leading-relaxed">
          {{ dialogState.message }}
        </AlertDialogDescription>
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
              ? 'bg-error-500 text-white hover:bg-error-600 active:bg-error-700 active:scale-[0.97]'
              : 'btn-primary'"
            @click="resolveConfirm(true)"
          >
            {{ dialogState.confirmText }}
          </button>
        </div>
      </AlertDialogContent>
    </AlertDialogPortal>
  </AlertDialogRoot>
</template>
