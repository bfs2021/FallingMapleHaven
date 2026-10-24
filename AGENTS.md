# AGENTS.md

## 项目概述

枫落港 (FallingMapleHaven) 是一个轻量社交平台，技术栈为：

- 前端：Vue 3 + Pinia + Tailwind CSS 3 + lucide-vue-next
- 后端：Django 5 + DRF + Channels
- 数据库与基础设施：PostgreSQL + Redis + Docker

通用项目文档：

- [项目设计 PRD](Docs/01-PRD-需求规格说明书.md)
- [API 与 WebSocket 接口文档](Docs/03-API与WebSocket接口文档.md)
- [插件系统设计](Docs/05-插件系统设计.md)

## 通用协作原则

所有开发都必须遵守以下原则：

- 先读文档，再读代码，最后再改代码。
- 文档、代码和测试发生冲突时，不允许擅自猜测；必须先确认并修正文档或契约。
- 修改必须围绕当前任务，避免顺手重构无关模块。
- 优先做最小正确改动，不引入没有明确需求的抽象层、兼容层或新功能。
- 命名、目录、响应格式、UI 语言必须匹配现有项目风格。
- 遇到用户或其他协作者留下的未提交改动，不得回滚、覆盖或清理，除非用户明确要求。

## 文档优先级

通用功能开发时按以下优先级理解需求：

1. 当前任务中明确指定的文档或用户确认结论。
2. 当前分支专用文档。
3. 通用项目文档。
4. 现有代码实现。

如果低优先级内容与高优先级内容冲突，以高优先级为准。

当前分支中，相关开发必须以 `Docs/16` 和 `Docs/17` 为最高优先级。

## 代码范围控制

- 不允许大范围重写账号、动态、聊天、小组、好友等无关模块。
- 如果某个无关模块必须调整，必须能说明它是满足默契问答契约所必需。
- 不允许为了让测试通过而降低权限、隐藏错误或放宽契约校验。



## 前端约定

- 使用 Vue 3 Composition API。
- 新增或改造 SFC 时使用 `<script setup>`，除非现有文件风格不同。
- 使用 Pinia 管理跨页面状态。
- 使用 Tailwind CSS 3。
- 使用 lucide-vue-next 图标库，不使用 emoji 作为结构性图标。
- Maple 色彩体系：`maple-50` 到 `maple-900`。
- 使用 `@/` 路径别名指向 `src/`。
- 优先复用项目设计系统类名：
  - `card-base`
  - `btn-primary`
  - `btn-secondary`
  - `btn-ghost`
  - `input-base`
  - `skeleton`
  - `page-title`
- 确认对话框必须使用 `useConfirm()` + `<ConfirmDialog />`。
- 开关组件必须使用 `<ToggleSwitch v-model="..." />`，不要写内联开关。
- UI 风格必须遵循温暖卡片风格，延续枫落港现有视觉语言。
- 移动端和桌面端同等重视。

## 后端约定

- 使用 Django 5 + DRF。
- API 统一基础路径为 `/api/v1`。
- 响应必须使用统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- 错误码沿用项目约定：
  - `40001` 参数错误
  - `40003` 无权限
  - `40004` 资源不存在
  - `40005` 操作冲突
  - `50000` 服务器内部错误
- 公开答题接口不得返回标准答案。
- 访客 Cookie 不得明文入库。
- 提交答卷必须防并发重复提交。
- 发布校验错误必须返回字段级错误，便于前端定位题卡。

## 测试要求

- 避免 Mock，优先使用真实数据库和 HTTP 调用。
- 优先集成测试，而不是孤立单元测试。
- 每项功能提交必须包含对应测试覆盖。

## 禁止事项

- 禁止继续实现旧版好友单题出题主流程。
- 禁止新增未写入文档的产品功能。
- 禁止在公开接口返回标准答案。
- 禁止将访客昵称作为唯一身份。
- 禁止以 IP 作为防重复主依据。
- 禁止发布后修改题目、选项和标准答案。
- 禁止把答卷榜做成全站排行榜。
- 禁止为结果单独设计个人结果页；结果分享统一落到答卷榜。
- 禁止物理删除新版测试和答卷业务数据。
- 禁止大范围修改与默契问答无关的功能。
- 禁止在未确认需求的情况下自由发挥 UI、流程或字段。

## 匹配现有风格

即使个人偏好不同，也必须匹配项目中已有的代码风格、命名模式、目录结构和 UI 语言。

Bug 修复必须严格限定在确认有问题的范围内，不要顺手重构无关代码。

## 对项目经理的三条忠告
"Act as an orchestrator. Use parallel agents to do the research and execution work. Write detailed tasks for each parallel agent and force them to act, iterate, finish tasks, and bring back in-depth reports. Your job is to deeply analyze the agents' work, provide feedback, and give them ongoing tasks."

"Measure twice, cut once policy."

"Keep the codebase clean, no tmp files, no dead code, no dead files. Stay organized all the time. No unnecessary folders, subfolders, or files."