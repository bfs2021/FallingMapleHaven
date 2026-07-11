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

---

## 2026-07-06 — ISSUE.md 全栈 + 连通性联合审计

来源：`ISSUE.md` 新版，共 86 项（C13/H20/M26/L27），覆盖后端 9 App + 前端 28 View + 20 Component + 4 Store + 9 API 模块 + Docs/01~08

### ✅ 已完全修复（17 项 + 2 误报）

| 编号 | 项目 | 说明 |
|------|------|------|
| C1 | `Notification.type=` → `notification_type=` | 7 处字段名修正 |
| C2 | `ALLOWED_HOSTS` 默认值 | `prod.py` 删 `default=[]` |
| C4 | WebSocket Origin 校验 | 加 `origin is None` 拒绝分支 |
| C5 | `VisitRecord` 唯一约束 | UniqueConstraint + 迁移去重 |
| C6 | `AdminLogsView` 类型校验 | `safe_int` 包裹 |
| C7 | `GroupDetailPage.vue` `\|\|` → `??` | 空数组 `[]` falsy 修复 |
| C8 | `GroupTransferView` 类型校验 | `safe_int` 包裹 + 修复 ChatRoomMember 同步（X1） |
| C9 | `GroupJoinView` 并发竞态 | `create` → `get_or_create` |
| C10 | `authStore.logout()` 无 try/catch | API 失败仍清除本地状态 |
| C11 | 注册 API 返回字段不全 | 改用完整 UserSerializer |
| C12+C13 | `<int:user_id>` 不兼容用户名 | 改为 `<str:username_or_id>` + resolve_profile_user |
| H8+H9 | 聊天室列表 N+1 | Subquery annotation 替代 Prefetch |
| H11 | FriendButton `requestId` prop | 新增 prop 精确指定请求 |
| H12 | 通知轮询丢滚动 | 仅更新未读计数 |
| H19 | WS `message_id` → `id` | 统一字段名，前端移除 fallback |
| H20 | `unreadCounts` 未填充 | fetchRooms 写入 + WS 递增 |
| X1 | 群转让 ChatRoomMember 不同步 | 转让后 `get_or_create` 成员记录 |
| — | ChatListPage last_message | 模板 `?.content` → 字符串直接显示 |

**误报排除（⏭️）：**
| 编号 | 说明 | 原因 |
|------|------|------|
| C3 | `answer_map` 死代码 | line 238 实际使用 |
| M12 | `SelectField.vue` 监听器泄漏 | 代码已正确 cleanup |

### 📋 待处理（70 项）

| 区间 | 待修复 | 说明 |
|------|--------|------|
| 🔴 Critical | 0 | 全部修复 |
| 🟠 High | 14 | 并发竞态 H16/H17、admin N+1/无分页 H2-H7、chat N+1 H10、Quiz N+1 H13/H14、图标名 H15、缺少 try/catch H18 |
| 🟡 Medium | 25 | N+1/Serialzier 优化 M1-M4、UI/UX M5-M11、分页 M13-M15、连通性 M17/M19/M23-M26、并发 M20、测试 M21、字段名 M24 |
| 🔵 Low | 27 | 代码整洁 L1-L20、文档偏差 L21-L23、字段名不一 L24-L26、WS 未使用 L27、API 风格 L28、竞态 L29-L30 |

---

## 2026-07-04 — ISSUE.md 首次全栈审计（旧版 66 项）

来源：`ISSUE.md` 旧版，该版本已由 2026-07-06 新版替代。以下为旧版归档：

### 🔴 Critical（7/7 已修复）
- C1 文件上传用 FormData
- C2 3 图布局重复/缺失
- C3 滚动加载页码双重递增
- C4 `int()` 无异常处理 11 处 → `safe_int`
- C5 WebSocket 房间订阅仅连接时执行
- C6 `get_unread_count` 每次 COUNT
- C7 `safe_int` 未导入致 500

### 🟠 High（17/23 已修复）
- H1 staff 可越权授 staff
- H2 排行榜字段名错误 500
- H5 点赞/评论数 `.count()` 忽略预取
- H6 访客足迹去重/限流
- H7 任意用户向任意小组发帖
- H8 直接修改 prop
- H9 相对时间无输入验证
- H11 Axios 401 绕过 logout
- H12 PostListView 缺 select_related
- H13 VisitorListView 缺 select_related
- H14 UserPostListView N+1
- H15 GroupPostsView 无预取
- H16 CommentListView N+1
- H17 RoomMessagesView N+1
- H18 GuestbookListView N+1
- H19 AdminQuizQuestionsView N+1
- H3 管理后台分页（5/7 视图已修，AdminGroupListView + AdminQuizQuestionsView 待修）
- H4 聊天室列表 N+1（主要修复，2 处残留）

### 🟡 Medium（13/21 已修复）
- M1 ImageField 替换 FileField（groups cover 待修）
- M2 PIL verify 不充分
- M3 批量通知 bulk_create
- M4 WebSocket 截断
- M7 默认密钥安全
- M9 路由守卫 Session
- M10 PostDetailView 小组可见性
- M11 FriendButton prop 类型
- M12 ensureSession 永久挂起
- M14 fetchNotifications 回退
- M16 needsTruncation 计算属性
- M17 WebSocket 来源验证
- M18 匿名提问分页
- M6 通知 HTML 过滤（部分修复）
- M8 `type` 字段遮蔽（2 处遗漏）
- M13 通知轮询滚动位置（选择器不匹配）

### 🔵 Low（0/15 已修复）
- 全部 15 项 Low 待修复

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
