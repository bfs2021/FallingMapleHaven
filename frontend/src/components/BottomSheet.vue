<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: '' },
})

const emit = defineEmits(['close'])

function onKeydown(e) {
  if (e.key === 'Escape' && props.show) emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="show" class="fixed inset-0 z-50 flex items-end md:items-center md:justify-center">
        <div
          class="absolute inset-0 bg-black/40 backdrop-blur-sm"
          @click="emit('close')"
        />

        <div
          class="relative w-full bg-white rounded-t-2xl md:rounded-2xl md:max-w-lg max-h-[90dvh] md:max-h-[80vh] overflow-y-auto shadow-modal animate-slide-up md:animate-scale-in"
        >
          <div class="sticky top-0 bg-white z-10 px-5 pt-3 pb-2 border-b border-border flex items-center justify-between md:hidden">
            <div class="w-8 h-1 bg-gray-300 rounded-full mx-auto absolute left-1/2 -translate-x-1/2 top-2" />
            <h3 v-if="title" class="text-base font-semibold text-text-primary pt-3">{{ title }}</h3>
            <button
              @click="emit('close')"
              class="ml-auto w-10 h-10 flex items-center justify-center text-text-secondary hover:text-maple-600 hover:bg-maple-50 rounded-lg transition-colors cursor-pointer"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="px-5 py-4">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease-out;
}
.sheet-enter-active > div:last-child,
.sheet-leave-active > div:last-child {
  transition: transform 0.25s ease-out;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from > div:last-child {
  transform: translateY(100%);
}
.sheet-leave-to > div:last-child {
  transform: translateY(100%);
}
@media (min-width: 768px) {
  .sheet-enter-from > div:last-child {
    transform: scale(0.9);
    opacity: 0;
  }
  .sheet-leave-to > div:last-child {
    transform: scale(0.9);
    opacity: 0;
  }
}
</style>
