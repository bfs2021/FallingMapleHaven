# AGENTS.md

## 项目概述

- [项目设计PRD](Docs\01-PRD-需求规格说明书.md)

**技术栈：** Vue 3 + Pinia + Tailwind CSS 3 · Django 5 + DRF + Channels · PostgreSQL · Docker


## 关键约定

### 前端

- Vue 3 Composition API + `<script setup lang="ts">`
- Tailwind CSS 3 + lucide-vue-next 图标库
- Maple 色彩体系：maple-50 (~#FFF8F0) 至 maple-900
- 使用 `@/` 路径别名指向 src/
- 设计系统类名：`card-base`、`btn-primary`、`btn-secondary`、`btn-ghost`、`input-base`、`skeleton`、`page-title`
- 所有组件位于 src/components/ 下
- 确认对话框：使用 `useConfirm()` 组合式函数 + `<ConfirmDialog />`（已在 App.vue 注册）
- 开关组件：使用 `<ToggleSwitch v-model="..." />`，不要使用内联开关

### 匹配现有风格

即使你个人偏好不同，也要匹配项目中已有的代码风格和模式。

### Bug 修复范围

Bug 修复严格限定在确认有问题的范围。

## 测试要求

- 避免 Mock，优先使用真实数据库和 HTTP 调用
- 优先集成测试而非孤立单元测试
- 每项提交必须包含全面测试覆盖

## 禁止事项

### 当进行前端UI/UX改动、BUG修复、定点功能更改和修复时，禁止：
 - 更改与本次改动无关的逻辑和代码
 - 自由发挥出没有被要求的功能和内容

## 重要参考

[Docs](Docs)
