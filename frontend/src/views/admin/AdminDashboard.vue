<script setup>
import { ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { pluginRegistry } from '@/plugins/registry'
import Icon from '@/components/Icon.vue'

const route = useRoute()
const mobileNavOpen = ref(false)

const builtinNavItems = [
  { path: '/admin', name: '数据统计', icon: 'barChart', exact: true },
  { path: '/admin/users', name: '用户管理', icon: 'users' },
  { path: '/admin/posts', name: '内容管理', icon: 'fileText' },
  { path: '/admin/groups', name: '群组管理', icon: 'hash' },
  { path: '/admin/plugins', name: '插件管理', icon: 'puzzle' },
  { path: '/admin/settings', name: '站点设置', icon: 'settings' },
  { path: '/admin/logs', name: '操作日志', icon: 'scrollText' },
]

const pluginNavItems = pluginRegistry.getAdminSidebarItems()
const navItems = [
  ...builtinNavItems.map(item => ({ ...item, isPlugin: false })),
  ...pluginNavItems.map(item => ({ ...item, isPlugin: true })),
]

function isActive(path, exact = false) {
  if (exact) return route.path === path
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="min-h-screen bg-maple-50">
    <header class="bg-gradient-to-r from-maple-800 to-maple-700 text-white px-4 md:px-6 py-3 flex items-center justify-between shadow-card">
      <div class="flex items-center gap-3">
        <button
          @click="mobileNavOpen = !mobileNavOpen"
          class="md:hidden w-9 h-9 flex items-center justify-center text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors cursor-pointer"
        >
          <Icon name="menu" :size="20" />
        </button>
        <Icon name="shield" :size="22" class="text-maple-200" />
        <h1 class="text-lg font-bold tracking-wide">管理后台</h1>
      </div>
      <RouterLink
        to="/"
        class="flex items-center gap-1.5 text-sm text-white/70 hover:text-white transition-colors"
      >
        <Icon name="arrowLeft" :size="14" /> 返回前台
      </RouterLink>
    </header>

    <div class="flex">
      <aside class="hidden md:flex flex-col w-56 bg-white border-r border-border min-h-[calc(100vh-52px)] p-3 gap-0.5 shadow-card">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ease-out relative"
          :class="isActive(item.path, item.exact)
            ? 'bg-maple-50 text-maple-700 font-medium'
            : 'text-text-secondary hover:bg-maple-50/50 hover:text-text-primary'"
        >
          <div
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-maple-600 rounded-r-full transition-all duration-200"
            :class="isActive(item.path, item.exact) ? 'opacity-100 scale-y-100' : 'opacity-0 scale-y-0'"
          />
          <Icon
            :name="item.icon"
            :size="18"
            class="transition-transform duration-150"
            :class="isActive(item.path, item.exact) ? '' : 'group-hover:scale-110'"
          />
          <span>{{ item.name }}</span>
          <span v-if="item.isPlugin" class="text-[10px] px-1.5 py-0.5 rounded bg-maple-100 text-maple-600 ml-auto">插件</span>
        </RouterLink>
      </aside>

      <div v-if="mobileNavOpen" class="md:hidden fixed inset-0 z-40 flex">
        <div @click="mobileNavOpen = false" class="flex-1 bg-black/30 backdrop-blur-sm" />
        <div class="w-56 bg-white h-full p-4 shadow-modal animate-slide-in-right">
          <div class="flex items-center gap-3 mb-4 pb-3 border-b border-border">
            <Icon name="shield" :size="20" class="text-maple-600" />
            <span class="text-sm font-semibold text-text-primary">管理后台</span>
          </div>
          <div class="flex flex-col gap-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          @click="mobileNavOpen = false"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
              :class="isActive(item.path, item.exact)
                ? 'bg-maple-50 text-maple-700 font-medium'
                : 'text-text-secondary hover:bg-maple-50/50 hover:text-text-primary'"
            >
              <Icon :name="item.icon" :size="18" />
              <span>{{ item.name }}</span>
              <span v-if="item.isPlugin" class="text-[10px] px-1.5 py-0.5 rounded bg-maple-100 text-maple-600 ml-auto">插件</span>
            </RouterLink>
          </div>
        </div>
      </div>

      <main class="flex-1 p-4 md:p-6">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.page-enter-active,
.page-leave-active {
  transition: all 0.2s ease-out;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
