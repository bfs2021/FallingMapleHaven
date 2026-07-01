<script setup>
import { ref } from 'vue'
import { useFeedStore } from '@/stores/feed'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AvatarImage from './AvatarImage.vue'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'

const emit = defineEmits(['close'])

const feedStore = useFeedStore()
const authStore = useAuthStore()
const toast = useToast()

const newContent = ref('')
const newImages = ref([])
const newVisibility = ref('public')
const newTag = ref('')
const submitting = ref(false)
const imageInput = ref(null)

const tags = [
  { key: 'chat', label: '#闲聊' },
  { key: 'share', label: '#分享' },
  { key: 'help', label: '#求助' },
  { key: 'question', label: '#提问' },
  { key: 'daily', label: '#日常' },
]

function triggerImagePick() {
  imageInput.value?.click()
}

function handleImagePick(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    if (newImages.value.length >= 9) break
    const url = URL.createObjectURL(file)
    newImages.value.push({ file, url })
  }
  e.target.value = ''
}

function removeImage(index) {
  URL.revokeObjectURL(newImages.value[index].url)
  newImages.value.splice(index, 1)
}

async function submitPost() {
  if (!newContent.value.trim() && !newImages.value.length) return
  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('content', newContent.value.trim())
    formData.append('visibility', newVisibility.value)
    if (newTag.value) formData.append('topic_tag', newTag.value)
    for (const img of newImages.value) {
      formData.append('images', img.file)
    }
    await feedStore.createPost(formData)
    newContent.value = ''
    newVisibility.value = 'public'
    newTag.value = ''
    for (const img of newImages.value) URL.revokeObjectURL(img.url)
    newImages.value = []
    toast.success('发布成功')
    emit('close')
  } catch { /* ignore */ } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <AvatarImage :user="authStore.user" size="md" />
      <span class="text-sm font-medium text-text-primary">{{ authStore.user?.nickname || authStore.user?.username }}</span>
    </div>

    <textarea
      v-model="newContent"
      rows="4"
      placeholder="分享你的想法..."
      class="input-base resize-none"
    />

    <div v-if="newImages.length" class="flex flex-wrap gap-2">
      <div v-for="(img, i) in newImages" :key="i" class="relative w-20 h-20 rounded-lg overflow-hidden group">
        <img :src="img.url" class="w-full h-full object-cover" />
        <button
          @click="removeImage(i)"
          class="absolute top-1 right-1 w-8 h-8 bg-black/50 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
        >
          <Icon name="x" :size="12" />
        </button>
      </div>
    </div>

    <div class="flex items-center gap-3 justify-between">
      <div class="flex items-center gap-3 flex-wrap min-w-0">
        <button
          @click="triggerImagePick"
          class="btn-ghost px-3 py-2 flex items-center gap-1.5"
        >
          <Icon name="image" :size="16" /> 图片
        </button>
        <input ref="imageInput" type="file" accept="image/*" multiple class="hidden" @change="handleImagePick" />

        <div class="w-28">
          <SelectField
            v-model="newVisibility"
            :options="[
              { value: 'public', label: '公开' },
              { value: 'friends', label: '仅好友' },
              { value: 'private', label: '私密' }
            ]"
          />
        </div>

        <div class="w-28">
          <SelectField
            v-model="newTag"
            :options="[{ value: '', label: '选择话题' }, ...tags.map(t => ({ value: t.key, label: t.label }))]"
          />
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button @click="$emit('close')" class="btn-ghost px-3 py-2">取消</button>
        <button
          @click="submitPost"
          :disabled="submitting || (!newContent.trim() && !newImages.length)"
          class="btn-primary px-5 py-2"
        >
          {{ submitting ? '发布中...' : '发布' }}
        </button>
      </div>
    </div>
  </div>
</template>
