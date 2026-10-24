<script setup>
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
} from 'reka-ui'
import Icon from '@/components/Icon.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: '' },
})

const emit = defineEmits(['close'])

function onOpenChange(visible) {
  if (!visible) emit('close')
}
</script>

<template>
  <DialogRoot :open="show" @update:open="onOpenChange">
    <DialogPortal>
      <DialogOverlay
        class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm
               data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out"
      />
      <DialogContent
        :aria-label="title ? undefined : '对话框'"
        class="fixed z-50 inset-x-0 bottom-0 w-full bg-white rounded-t-2xl max-h-[90dvh] overflow-y-auto shadow-modal
               md:inset-0 md:m-auto md:w-fit md:h-fit md:max-w-lg md:max-h-[80vh] md:rounded-2xl
               max-md:data-[state=open]:animate-slide-in-bottom max-md:data-[state=closed]:animate-slide-out-bottom
               md:data-[state=open]:animate-dialog-in md:data-[state=closed]:animate-dialog-out"
      >
        <div class="sticky top-0 bg-white z-10 px-5 pt-3 pb-2 border-b border-border flex items-center justify-between">
          <div class="w-8 h-1 bg-gray-300 rounded-full mx-auto absolute left-1/2 -translate-x-1/2 top-2 md:hidden" />
          <DialogTitle v-if="title" class="text-base font-semibold text-text-primary pt-3 md:pt-0">
            {{ title }}
          </DialogTitle>
          <button
            @click="emit('close')"
            aria-label="关闭"
            class="ml-auto w-10 h-10 flex items-center justify-center text-text-secondary hover:text-maple-600 hover:bg-maple-50 rounded-lg transition-colors cursor-pointer"
          >
            <Icon name="x" :size="20" />
          </button>
        </div>

        <div class="px-5 py-4">
          <slot />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
