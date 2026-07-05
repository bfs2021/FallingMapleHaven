# AGENTS.md

## 项目概述

- [项目设计PRD](Docs\01-PRD-需求规格说明书.md)

**技术栈：** Vue 3 + Pinia + Tailwind CSS 3 · Django 5 + DRF + Channels · PostgreSQL · Docker

## 构建命令

```bash
# 前端
cd frontend && npm run build
```

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

### 后端

<!-- Django 后端约定 -->

### 数据库

<!-- 数据库约定 -->

## 架构说明

<!-- 关键目录结构、各层职责 -->

## 工作流

### 顾全大局
当编写或改动字段名称或者数据结构、类型等时，一定要作透彻的上下游搜索和验证，避免出现任何不同步的问题。

### 先思考再编码

实现前先明确假设，暴露取舍。如果有多个可能的方案，列出来再选，不要默默决定。不确定就问。

### 简约至上

用最小代码解决当前问题。不需要的功能不做，单次使用的代码不抽象，没要求的"灵活性"不加。

### 精确改动

只碰必须碰的文件。不改相邻代码、不重构没坏的东西。每行改动都应当能回溯到本次需求。

### 目标驱动

把任务转化为可验证的目标：
- "加验证" → "先写无效输入的测试，再让它们通过"
- "修 Bug" → "先写复现测试，再让它通过"
- "重构 X" → "确保重构前后所有测试通过"

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
