<script setup>
import { computed } from 'vue'
import {
  SelectRoot,
  SelectTrigger,
  SelectPortal,
  SelectContent,
  SelectViewport,
  SelectItem,
  SelectItemText,
} from 'reka-ui'
import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

// reka Select 的 value 不接受 null/''，用索引键作内部代理，对外保持原 value 语义（含 null/0）
function keyOf(i) {
  return `__opt_${i}`
}

const selectedIndex = computed(() =>
  props.options.findIndex(o => (o.value ?? o) === props.modelValue)
)

const selectedLabel = computed(() => {
  if (selectedIndex.value === -1) return ''
  const opt = props.options[selectedIndex.value]
  return opt ? (opt.label ?? opt) : ''
})

function onUpdate(key) {
  const opt = props.options[Number(String(key).replace('__opt_', ''))]
  emit('update:modelValue', opt ? (opt.value ?? opt) : '')
}
</script>

<template>
  <SelectRoot
    :model-value="selectedIndex === -1 ? undefined : keyOf(selectedIndex)"
    :disabled="disabled"
    @update:model-value="onUpdate"
  >
    <SelectTrigger as-child>
      <button
        type="button"
        class="group input-base flex items-center justify-between gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-left
               data-[state=open]:ring-2 data-[state=open]:ring-maple-600/20 data-[state=open]:border-maple-600"
      >
        <span :class="selectedLabel ? 'text-text-primary' : 'text-text-secondary/50'">
          {{ selectedLabel || placeholder }}
        </span>
        <Icon
          name="chevronDown"
          :size="16"
          class="text-text-secondary shrink-0 transition-transform duration-150 group-data-[state=open]:rotate-180"
        />
      </button>
    </SelectTrigger>
    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="4"
        class="z-[70] bg-white rounded-xl shadow-modal border border-border overflow-hidden max-h-60 overflow-y-auto w-[var(--reka-popper-anchor-width)] min-w-32"
      >
        <SelectViewport>
          <SelectItem
            v-for="(opt, i) in options"
            :key="keyOf(i)"
            :value="keyOf(i)"
            class="w-full text-left px-4 py-2.5 text-sm transition-colors cursor-pointer outline-none
                   data-[state=checked]:bg-maple-50 data-[state=checked]:text-maple-700 data-[state=checked]:font-medium
                   data-[highlighted]:bg-maple-50/60 data-[highlighted]:text-text-primary"
          >
            <SelectItemText>{{ opt.label ?? opt }}</SelectItemText>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
