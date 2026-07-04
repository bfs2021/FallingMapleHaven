<script setup>
defineProps({
  images: { type: Array, required: true },
})
</script>

<template>
  <div v-if="images.length === 1" class="max-w-[400px] overflow-hidden rounded-lg group/image">
    <img :src="images[0]" class="w-full h-auto max-h-[400px] object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
  </div>
  <div v-else-if="images.length === 2" class="grid grid-cols-2 gap-2">
    <div v-for="(img, i) in images" :key="i" class="overflow-hidden rounded-lg group/image">
      <img :src="img" class="w-full h-48 object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
    </div>
  </div>
  <div v-else-if="images.length === 3" class="grid grid-cols-2 gap-2">
    <div class="overflow-hidden rounded-lg row-span-2 group/image">
      <img :src="images[0]" class="w-full h-64 object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
    </div>
    <div v-for="(img, i) in images.slice(1)" :key="i" class="overflow-hidden rounded-lg group/image">
      <img :src="img" class="w-full h-[7.5rem] object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
    </div>
  </div>
  <div v-else-if="images.length === 4" class="grid grid-cols-2 gap-2">
    <div v-for="(img, i) in images" :key="i" class="overflow-hidden rounded-lg group/image">
      <img :src="img" class="w-full h-36 object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
    </div>
  </div>
  <div v-else class="grid grid-cols-3 gap-2">
    <div v-for="(img, i) in images" :key="i" class="overflow-hidden rounded-lg group/image">
      <img :src="img" class="w-full h-32 object-cover transition-transform duration-300 ease-out group-hover/image:scale-105" />
    </div>
  </div>
</template>
