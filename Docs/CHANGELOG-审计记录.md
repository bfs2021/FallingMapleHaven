# 审计与修复记录 — 归档合并

> 合并来源（8 份）：`代码审计报告.md`、`缺失功能分析报告.md`、`缺失功能实施计划.md`、
> `文档修改报告.md`、`代码佐证与文档偏差报告.md`、`用户体验探索与需求符合度报告.md`、
> `前端UI-UX优化记录.md`、`UI-UX-AUDIT.md`
>
> 合并日期: 2026-07-04
> 状态: 以下条目标注 [已修复] 的均已在代码或文档中修正，标注 [待处理] 的为已知未结项。

---

## 2026-07-01 — 文档对齐 & 功能修复

### 所做工作
- 对齐 Docs/01〜07 与代码，修复 API 路径、路由权限、路由守卫等不一致项
- 实现留言板回复/删除功能（GuestbookPage.vue）
- 实现消息分页加载（ChatRoomPage.vue）
- 实现动态分页加载（GroupDetailPage.vue）
- 实现通知轮询 + 分页（NotificationsPage.vue）
- 修复路由守卫 `?next=` 跳转参数
- 修复 `chat.js` 房间排序
- 补写 `Docs/08-内测部署指南.md`
- 添加 ngrok 兼容配置（`allowedHosts`、`CSRF_TRUSTED_ORIGINS` 等）
- 写入 README「未完成」章节

### 未结项（当前 batch）
- [待处理] CommentListView 未分页
- [待处理] `base.py` 中 ngrok 域名硬编码，应移至 `dev.py` 或 `.env`
- [待处理] Docs/04 中 error red / success green 未注册到 tailwind.config.js（已加注释说明）

---

## 2026-06-30 — 文档偏差全面审计

### 发现
- [已修复] README / Docs/03 / Docs/05 默契问答 DELETE 路径缺 `/delete/`
- [已修复] Docs/01-PRD 通知类型缺 `system`/`friend_accepted`，多云 `新消息提醒`
- [已修复] Docs/02 Redis host 写 `"redis"` 实际 `"localhost"`
- [已修复] Docs/02 CORS 配置写 `localhost:8000` 实际无
- [已修复] Docs/02 技术栈 Uvicorn → Daphne（`daphne` 在 INSTALLED_APPS，`asgi.py` 用 ProtocolTypeRouter）
- [已修复] Docs/02 `admin_sitelog` 字段名 `user_id` → `user`（model 字段）
- [已修复] Docs/03 §3.2 管理员路径参数 `{username_or_id}` → `{user_id}`（整数）
- [已修复] Docs/03 §3.2 标题编号重复（3.2 出现两次）
- [已修复] Docs/04 色板中错误红/成功绿未注册到 Tailwind（加说明）
- [已修复] 文档与代码偏差报告中的 API 路径问题已在 07-01 batch 修复

---

## 2026-06-25 前 — 早期审计与修复

### 代码审计（来源: 代码审计报告.md）
- [已修复] 50+ 项问题（关键漏洞、性能问题），49 项已修复
- 主要覆盖：XSS 防护、CSRF、SQL 注入、文件上传限制、密码策略等
- 详情见原 `代码审计报告.md`（已归档）

### 缺失功能分析（来源: 缺失功能分析报告.md）
- [已修复] 首批无分页/无限刷新的 4 个页面（C1-C3）：HomePage、ChatRoomPage、NotificationsPage
- [已修复] 表单数据 tag/visibility 不匹配
- [已修复] 图片上传 MIME 校验
- [已修复] WebSocket 断线重连
- [已修复] FriendButton catch 缺失
- 其余 P2+ 功能（Docker/Nginx 部署、纪念日倒计时、许愿池等）已明确推迟

### UI/UX 优化（来源: 前端UI-UX优化记录.md + UI-UX-AUDIT.md）
- [已修复] Tailwind 配置扩展：动画、阴影、圆角、字号 tokens
- [已修复] 枫叶色系统一（maple-50 到 maple-900）
- [已修复] 12 项 UI 交叉验证问题
- [已修复] 留言板、聊天室、通知等 UX 流程

### 用户体验探索（来源: 用户体验探索与需求符合度报告.md）
- 发现：项目具备基础社交产品骨架，但核心体验因流程断裂/不一致未通过验收
- 团队已逐步修复断裂流程

---

## 归档说明

以下原始文件已保留但内容过时，如需查阅详情请直接打开：

| 文件 | 状态 |
|------|------|
| `Docs/代码审计报告.md` | 已归档（内容合并至本文件） |
| `Docs/缺失功能分析报告.md` | 已归档 |
| `Docs/缺失功能实施计划.md` | 已归档 |
| `Docs/文档修改报告.md` | 已归档 |
| `Docs/代码佐证与文档偏差报告.md` | 已归档 |
| `Docs/用户体验探索与需求符合度报告.md` | 已归档 |
| `Docs/前端UI-UX优化记录.md` | 已归档 |
| `Docs/UI-UX-AUDIT.md` | 已归档 |
