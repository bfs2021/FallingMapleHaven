<script setup>
import Icon from '@/components/Icon.vue'

defineProps({
  icon: { type: String, default: 'fileText' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="text-center py-16 text-text-secondary">
    <Icon :name="icon" :size="44" class="mx-auto mb-3 text-maple-300" />
    <p class="text-base font-medium text-text-primary mb-1">{{ title }}</p>
    <p v-if="description" class="text-sm">{{ description }}</p>
    <div v-if="$slots.default" class="mt-4 flex justify-center">
      <slot />
    </div>
  </div>
</template>
