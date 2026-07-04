# AGENTS.md

## Build Command
```bash
cd frontend && npm run build
```

## Key Conventions

- Vue 3 Composition API + Tailwind CSS 3 + lucide-vue-next icons
- Maple color system: maple-50 (~#FFF8F0) through maple-900
- Use `@/` path alias for src/
- Design system classes: `card-base`, `btn-primary`, `btn-secondary`, `btn-ghost`, `input-base`, `skeleton`, `page-title`
- All components under src/components/
- Confirm dialog: `useConfirm()` composable + `<ConfirmDialog />` in App.vue
- ToggleSwitch: use `<ToggleSwitch v-model="..." />` instead of inline switches
