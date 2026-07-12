# 枫落港 (FallingMapleHaven) — 待修复 Bug 清单

> 来源：全栈联合审计 + 前后端连通性专项审计 2026-07-06
> 审查覆盖：后端 9 个 App × 全部 Python 文件、前端 28 个 View + 20 个 Component + 4 Store + 9 API 模块 + Docs/01~08
> 连通性审计：逐一追踪前端 API 调用 → 后端 Serializer/View 字段映射

**总计：86 项**（Critical 13 / High 20 / Medium 26 / Low 27）

| 严重程度 | 总数 | 已修复 | 误报/跳过 | **待修复** |
|---------|------|--------|-----------|-----------|
| 🔴 Critical | 13 | 12 | 1 | **0** |
| 🟠 High | 20 | 17 | 1 | **1** |
| 🟡 Medium | 26 | 0 | 1 | **25** |
| 🔵 Low | 27 | 0 | 0 | **27** |
| **总计** | **86** | **29** | **3** | **54** |

---

## 🟠 High — 待修复（1 项）

### H18. 前端多处 Store Action 缺少 try/catch 导致未捕获 Rejection

**涉及文件：**
| 文件 | 行号 | 缺少 try/catch 的方法 |
|------|------|----------------------|
| `frontend/src/stores/feed.js` | 27-30 | `createPost()` |
| `frontend/src/stores/feed.js` | 32-44 | `toggleLike()`, `deletePost()` |
| `frontend/src/stores/chat.js` | 17-19 | `fetchRooms()` |
| `frontend/src/stores/chat.js` | 21-31 | `fetchMessages()` |
| `frontend/src/stores/chat.js` | 32-41 | `sendMessage()` |
| `frontend/src/stores/friend.js` | 11-17 | `fetchFriends()`, `fetchRequests()` |
| `frontend/src/stores/auth.js` | 64-67 | `updateProfile()` |
| `frontend/src/components/PostActions.vue` | 15-18 | `handleLike()` |
| `frontend/src/views/FriendsPage.vue` | 82-89 | `goToChat()` |
| **修复方案：** 所有 async action 加 try/catch，失败时 toast 提示

---



## 🟡 Medium — 待修复（25 项）

### M1. `GroupDetailSerializer.get_is_member` 遍历 `obj.members.all()` 忽略 annotation

**文件：** `backend/apps/groups/serializers.py:55-61`
**描述：** `GroupListView` 已 annotate `_is_member=Exists(...)`，但 serializer 忽略 annotation，仍遍历 `obj.members.all()`。

### M2. `GroupDetailSerializer.get_member_count` 未使用 annotation

**文件：** `backend/apps/groups/serializers.py:52-53`
**描述：** `getattr(obj, 'member_count', None) or obj.members.count()` — 0 值时 `or` 短路触发额外查询。

### M3. `PostCreateView` 批量通知循环内逐条创建

**文件：** `backend/apps/groups/views.py:386-397`
**描述：** `Notification.objects.bulk_create` 对外部成员批量一次性创建，但对 admin 的通知使用循环内 `.create()`。

### M4. `QuizLeaderboardView` 方法体内重复 import

**文件：** `backend/apps/plugins/quizzes/views.py:204-205`
**描述：** `from django.db.models import Q` 和 `from apps.friends.models import Friendship` 写在方法体内。

### M5. 前端 `ChatRoomPage.vue` 每次挂载断连 WS

**文件：** `frontend/src/views/ChatRoomPage.vue:42-43`
**描述：** `disconnectWs()` + `connectWs()` 在每次进入聊天室时执行。
**修复方案：** 移除 disconnect/connect 调用。

### M6. 前端 `ChatRoomPage.vue` 进入房间未清除未读计数

**文件：** `frontend/src/views/ChatRoomPage.vue`
**描述：** 进入聊天室后不调用 API 标记已读，聊天列表未读计数不变。

### M7. `HomePage.vue` 快速切换标签页丢失请求

**文件：** `frontend/src/views/HomePage.vue:58-65`
**描述：** `switchTag` 无去抖/竞态处理。快速切换标签时，前一个请求的 `loading=true` 阻塞后一个请求。

### M8. 前端 `feedStore` 无错误处理（与 H18 重叠）

**文件：** `frontend/src/stores/feed.js:32-44`
**描述：** `toggleLike` 和 `deletePost` 无 try/catch。见 H18。

### M9. `PostActions.vue` like 操作无错误处理（与 H18 重叠）

**文件：** `frontend/src/components/PostActions.vue:15-18`
**描述：** `handleLike` 无 try/catch。见 H18。

### M10. `ProfilePage.vue` `isOwner` 比较可能类型不匹配

**文件：** `frontend/src/views/ProfilePage.vue:35`
**描述：** `authStore.user?.user_id` 为 number，`userId.value` 可能为 string（如 username 路径），`===` 失败。
**修复方案：** `==` 或 `Number(userId.value)`。

### M11. `QuestionBoxPage.vue` 单个 `submittingAnswer` 阻塞所有回答按钮

**文件：** `frontend/src/views/QuestionBoxPage.vue:110`
**描述：** 一个布尔值控制所有问题，提交答案时其他所有按钮被禁用。
**修复方案：** 改为 `Record<questionId, boolean>`。

### M13. `InboxView` 匿名提问收件箱对 `answered` 参数处理不完整

**文件：** `backend/apps/plugins/questions/views.py:58-63`
**描述：** 只检查 `answered= "true"` 或 `"false"`，其他值或缺失时返回所有。

### M14. `CommentListView` 无分页

**文件：** `backend/apps/feed/views.py:282-298`
**描述：** 返回帖子的所有顶级评论，无分页。
**修复方案：** 加分页参数。

### M15. `RoomListView` 中 `RoomCreateView` 的委托调用

**文件：** `backend/apps/chat/views.py:30-31`
**描述：** `RoomListView.post` 手动实例化 `RoomCreateView.as_view()(request)`，中间件/认证处理链可能不完整。

### M16. 前端 `groupApi.create` / `update` 的 `Content-Type` 判断不完整

**文件：** `frontend/src/api/plugin.js:27`
**描述：** 若 data 不是 FormData 实例也不手动指定 `multipart/form-data`，但后端某些字段（如 cover_image）需要 multipart 编码。

### M17. `ProfilePage.vue` 插件卡片缓存 fallback 中的 route 未替换 userId

**文件：** `frontend/src/views/ProfilePage.vue:97-114`
**描述：** catch 分支用 `profile.value?.plugins` 中的 route（含 `:userId` 占位符），未替换为实际 userId。

### M18. 前端 `SettingsModulesPage.vue` ToggleSwitch 忽略 emit 值

**文件：** `frontend/src/views/SettingsModulesPage.vue`
**描述：** `@update:model-value="toggleModule(mod)"` 不接收新值，而是手动翻转 `mod.enabled`。

### M19. 🆕 `InboxView`（plugins/questions）缺少 select_related 导致 N+1

**文件：** `backend/apps/plugins/questions/views.py:59,73-74`
**描述：** `AdminQuestionSerializer` 访问 `obj.sender.nickname`（`real_sender` SerializerMethodField），但 queryset 无 `select_related('sender', 'recipient')`。

### M20. 🆕 `useConfirm.js` 模块级 `resolveCallback` 被并发调用覆盖

**文件：** `frontend/src/composables/useConfirm.js:12`
**描述：** `resolveCallback` 是模块级变量。若两个组件同时调用 `confirm()`，第二个调用会覆盖第一个的 resolver。
**修复方案：** 改用队列或唯一 ID 追踪

### M21. 🆕 `notifications/tests/` 测试文件仅兼容 SQLite

**文件：** `backend/apps/notifications/tests/test_c1_fix.py:90-103`
**描述：** `Notification.objects.bulk_create()` 时未传 `title`/`content`/`link`。SQLite 允许 NULL，但 PostgreSQL 中这些字段有 `NOT NULL` 约束。
**修复方案：** 添加缺失的必填字段值

### M22. 前端 `ProfilePage.vue` 访客模式下无 guestbook Tab（与文档不一致）

**文件：** `frontend/src/views/ProfilePage.vue:48-56`
**描述：** `Docs/07` 设计文档规定访客模式 Tab 为 `posts + guestbook`，但实际实现访客模式仅显示 `posts` Tab。

### M23. 🟡 `PluginEntryGrid.vue` 读取 `plugin.desc` 但 API 返回 `description`（连通性）

**文件：** `frontend/src/components/PluginEntryGrid.vue:57` — 后端 `plugins/base.py:20-37`
**描述：** `PluginEntryGrid` 从插件数据对象读取 `plugin.desc`，而后端 `BasePlugin` 定义的字段名是 `description`。`plugin.desc` 在 fallback 数据中不存在 → 显示 `undefined`。
**修复方案：** `PluginEntryGrid.vue:57` 将 `plugin.desc` 改为 `plugin.description`

### M24. 🟡 `RoomCreateSerializer` 使用 `type` 字段名，与模型 `room_type` 不一致（连通性）

**文件：** `backend/apps/chat/serializers.py:89` — 模型 `chat/models.py:12`
**描述：** 后端 `RoomCreateSerializer` 定义的字段名是 `type`，但 `ChatRoom` 模型的 DB 字段是 `room_type`。
**修复方案：** 序列化器字段改为 `room_type` 以匹配模型，或在序列化器中加 `room_type = CharField(source='type')` 别名

### M25. 🟡 私密小组 `hasPendingRequest` 状态跨页面刷新不保持（连通性）

**文件：** `frontend/src/views/GroupDetailPage.vue:29,87-99,159`
**描述：** 加入私密小组后，`GroupJoinRequest` 被创建，`hasPendingRequest.value` 设为 `true`。但 `fetchGroup()` 不向后端检查 `GroupJoinRequest` 状态，页面刷新后 `hasPendingRequest` 重置为 `false`。
**修复方案：** `fetchGroup()` 中增加对 `/groups/{id}/join-requests/?applicant=me` 的检查

### M26. 🟡 `AdminPluginsPage.vue` 读取 `plugin.description` 但管理 API 不返回该字段（连通性）

**文件：** `frontend/src/views/admin/AdminPluginsPage.vue:77` — `backend/apps/admin_dashboard/views.py:266-276`
**描述：** Admin 插件列表视图遍历 `Plugin.objects.all()`（Django model 实例），该模型只含 `name, plugin_type, is_active, config, created_at`，不含 `description` 字段。所有插件显示"暂无描述"。
**修复方案：** `AdminPluginListView` 中在遍历时从 `PluginRegistry` 获取对应插件类的 `description` 属性

---

## 🔵 Low — 待修复（27 项）

### L1. `ChatRoom` 模型同时有 `is_group` 和 `room_type` 两个冗余字段

**文件：** `backend/apps/chat/models.py:11-12`
**描述：** `room_type` 已能区分 private/group，`is_group` 是冗余且可能不一致。
**修复：** 移除 `is_group` 或改为 property。

### L2. `SECRET_KEY` 开发环境每次启动随机生成

**文件：** `backend/config/settings/base.py:13`
**描述：** `get_random_secret_key()` fallback 导致 dev 重启后所有会话失效。

### L3. ngrok 域名硬编码在 base.py

**文件：** `backend/config/settings/base.py:127,131`
**描述：** `CORS_ALLOWED_ORIGINS` 和 `CSRF_TRUSTED_ORIGINS` 硬编码 ngrok 地址。

### L4. Redis 地址不可配置

**文件：** `backend/config/settings/base.py:116-123`
**描述：** `CHANNEL_LAYERS` 的 `hosts: [("localhost", 6379)]` 无环境变量覆盖。

### L5. 非匿名用户速率限制缺失

**文件：** `backend/config/settings/base.py:140-145`
**描述：** 仅配置了 `AnonRateThrottle`，认证用户无限流。

### L6. `AdminQuizQuestionsView` 中 `answer_map` 死代码

**文件：** `backend/apps/admin_dashboard/views.py:232-234`

### L7. `QuizLeaderboardView` 中 `answered_ids` 死代码

**文件：** `backend/apps/plugins/quizzes/views.py:132-134`
**描述：** `answered_ids` 赋值后从未使用。

### L8. `AdminUserListView` 限 `is_staff` 更新只检查 `is_superuser`

**文件：** `backend/apps/admin_dashboard/views.py:81`
**描述：** `if request.user.is_superuser: allowed_fields.add("is_staff")` — 权限粒度偏粗，但符合预期。

### L9. `AdminUserUpdateView` 审计日志记录原始 `request.data`

**文件：** `backend/apps/admin_dashboard/views.py:91`
**描述：** `detail={"changes": request.data}` — 可能包含未经校验的字段。

### L10. `ensureSession` 初始化竞态

**文件：** `frontend/src/stores/auth.js:37-48`
**描述：** `sessionInitPromise` 在失败后被设为 `null`，不会重试。

### L11. 前端 `vite.config.js` `allowedHosts: true` 过于宽松

**文件：** `frontend/vite.config.js:10`
**描述：** 允许任意 host 连接 dev 服务器，存在 DNS rebinding 风险。

### L12. `UserSearchSerializer` 暴露冗余 `avatar` + `avatar_url`

**文件：** `backend/apps/friends/serializers.py:25`

### L13. `GroupMember.role` 使用原始列表而非 `TextChoices`

**文件：** `backend/apps/groups/models.py:32`

### L14. 硬编码特殊字符集重复定义

**文件：** `backend/apps/accounts/views.py:141` 和 `serializers.py:27`

### L15. import 写在方法体内（PEP 8）

**文件：** 多处 — `feed/views.py`、`plugins/quizzes/views.py`、`plugins/quizzes/plugin.py`、`plugins/questions/plugin.py`、`plugins/views.py`、`plugins/registry.py`、`accounts/models.py`、`accounts/serializers.py`、`profiles/views.py`、`admin_dashboard/views.py` 等 15+ 处。
**描述：** 方法级 import 违反 PEP 8，包括 `Q`、`Friendship`、`InterestGroup`、`Notification` 等。

### L16. `PostImage`/`PostFile` 仍用循环内 `create()` 而非 `bulk_create`

**文件：** `backend/apps/feed/views.py:137-147`

### L17. 前端 plugin registry 的 `getActivePlugins()` 名不副实

**文件：** `frontend/src/plugins/registry.js:14-16`
**描述：** 返回所有插件而非仅活跃。

### L18. `ActivePluginsView` 权限偏严

**文件：** `backend/apps/plugins/views.py:7-8`
**描述：** 继承全局 `[IsAuthenticated]`，但作为活跃插件列表，可能应对访客开放。

### L19. 🆕 `HomePage.vue` 未使用 import

**文件：** `frontend/src/views/HomePage.vue:5,11`
**描述：** `postApi`（line 5）和 `useToast`（line 11，line 17 赋值）均未使用。

### L20. 🆕 `useToast.js` setTimeout 未清理

**文件：** `frontend/src/composables/useToast.js`
**描述：** `setTimeout` 在 `show()` 中未保存 timer id，组件卸载后回调仍可能执行。

### L21. 🆕 数据库字段名文档偏差：`type` → `plugin_type` / `notification_type` / `room_type`

**文件：** `Docs/02-技术架构与数据库设计.md` §2.2.11/2.2.17/2.2.22
**描述：** 文档使用 `type` 字段名，但实际代码中 `plugins_plugin` → `plugin_type`，`notifications_notification` → `notification_type`，`chat_chatroom` → `room_type`。

### L22. 🆕 `Docs/05` 插件基类缺少 `get_summary()` / `get_profile_card_data()`

**文件：** `Docs/05-插件系统设计.md` §2.1
**描述：** `BasePlugin` 代码实际有 `get_summary()` 和 `get_profile_card_data()`，但文档未记录。

### L23. 聊天室 API 文档字段名不匹配

**文件：** `Docs/03-API与WebSocket接口文档.md` §6.1
**描述：** 文档响应字段为 `room_id`/`type`，实际代码返回 `id`/`room_type`。

### L24. 🔵 `CommentAuthorSerializer` 用户 ID 字段名使用 `id` 而非 `user_id`（连通性）

**文件：** `backend/apps/feed/serializers.py:96` — `frontend/src/views/CommentSection.vue:38`
**描述：** 该序列化器输出 `id` 作为用户 ID，而 `UserSerializer` 输出 `user_id`。

### L25. 🔵 `FriendSerializer` 缺少 `user_id` 和 `username`（连通性）

**文件：** `backend/apps/friends/serializers.py:31-58` — `frontend/src/views/FriendsPage.vue:83`
**描述：** 好友列表序列化器返回 `id`（通过 `get_id()` 返回好友的用户 ID）而非 `user_id`，且不含 `username`。

### L26. 🔵 `UserSearchSerializer` 使用 `id` 而非 `user_id`（连通性）

**文件：** `backend/apps/friends/serializers.py:20-28` — `frontend/src/views/FriendsPage.vue:199,209,211`
**描述：** 用户搜索序列化器输出 `id` 而非 `user_id`。

### L27. 🔵 前端 WebSocket 从未发送 `send_message` 消息（连通性）

**文件：** `backend/apps/chat/consumers.py:58-79`（Consumer 处理 `send_message`）— `frontend/src/stores/chat.js`
**描述：** Consumer 的 `receive()` 正确处理 `send_message` 类型，但前端通过 REST API 发送消息。WebSocket `send_message` 流程从未被前端使用。

### L28. 🔵 Admin 问答列表返回裸数组而非分页包装器（连通性）

**文件：** `backend/apps/admin_dashboard/views.py:222-254`
**描述：** `/admin/quiz/questions/` 返回 `{code: 0, data: [...]}`（裸数组），而所有其他管理列表端点返回 `{code: 0, data: {total, page, page_size, results: [...]}}`。

### L29. 🔵 `GroupJoinView` 中 `ChatRoomMember.create()` 的竞态条件

**文件：** `backend/apps/groups/views.py:135-137`
**描述：** `ChatRoomMember.objects.create()` 前只有 `.exists()` 检查，无唯一性兜底。

### L30. 🔵 `RoomCreateView` 私聊创建 TOCTOU 竞态

**文件：** `backend/apps/chat/views.py:97-103`
**描述：** 先 `.exists()` 检查再创建，存在竞态窗口。

---

## ✅ 已修复（18 项）

### 🔴 Critical（12 项）

| 编号 | 项目 | 说明 |
|------|------|------|
| C1 | `Notification.type=` → `notification_type=` | 7 处字段名修正（`groups/views.py` 5 处 + `feed/views.py` 1 处 + tests） |
| C2 | `ALLOWED_HOSTS` 默认值 | `prod.py` 删 `default=[]` |
| C4 | WebSocket Origin 校验 | 加 `origin is None` 拒绝分支 |
| C5 | `VisitRecord` 唯一约束 | UniqueConstraint(`visitor`, `visited_user`) + 数据迁移去重 |
| C6 | `AdminLogsView` 类型校验 | `safe_int(user_id, None)` 包裹 |
| C7 | `GroupDetailPage.vue` `\|\|` → `??` | 空数组 `[]` 被 `||` 视为 falsy 修复 |
| C8 | `GroupTransferView` 类型校验 | `safe_int` 包裹；同时修复 ChatRoomMember 不同步（X1） |
| C9 | `GroupJoinView` 并发竞态 | `create` → `get_or_create` |
| C10 | `authStore.logout()` 无 try/catch | API 失败仍清除本地状态（`finally` 块设 `this.user = null`） |
| C11 | 注册 API 返回字段不全 | 改用完整 `UserSerializer` 替代手写 dict |
| C12+C13 | `<int:user_id>` 不兼容用户名 | 管理员和 profile-cards 路由改为 `<str:username_or_id>` + `resolve_profile_user()` |

### 🟠 High（17 项）

| 编号 | 项目 | 说明 |
|------|------|------|
| H2-H7 | admin_dashboard 6 项 N+1/无分页 | 5 处 `select_related` + 3 处分页，前端适配 `results` |
| H8+H9 | 聊天室列表 N+1 | Subquery annotation 替代 Prefetch，`_cached_last_msg` 改用 `obj.messages.all()[0]` |
| H10 | chat serializer `obj.group` 无 select_related | `RoomListView` 加 `.select_related('group')` |
| H11 | FriendButton `requestId` prop | 新增 prop 精确指定请求，避免歧义 |
| H12 | 通知轮询丢滚动 | 轮询仅更新未读计数，不再全量刷新列表 |
| H13 | `QuizLeaderboardView` N+1 | 加 `.select_related('user_a', 'user_b')` |
| H14 | `QuizReceivedQuestionsView` 无分页 | 后端加分页 + 前端适配 `results` |
| H16 | `GroupJoinRequest.create()` 并发 → 500 | 改为 `get_or_create` |
| H17 | `Friendship.create()` 并发 → 500 | 改为 `get_or_create` |
| H19 | WS `message_id` → `id` | 统一字段名，前端移除 `||` fallback |
| H20 | `unreadCounts` 未填充 | `fetchRooms()` 写入每个房间的 `unread_count` + WebSocket 递增 |

### 🆕 其它已修复

| 编号 | 项目 | 说明 |
|------|------|------|
| X1 | 群转让 ChatRoomMember 不同步 | `transaction.atomic()` 内追加 `get_or_create` 成员记录 |
| — | ChatListPage last_message | 模板 `?.content` → 字符串直接显示 |

---

## ⏭️ 误报排除

| 原编号 | 说明 | 排除原因 |
|--------|------|---------|
| C3 | `answer_map` 死代码 | line 238 实际使用（`answer_map.get(obj.correct_answer, ...)`） |
| H15 | 管理后台图标用 kebab-case | `PluginEntryGrid.vue` 已有 `iconMap` 映射转 PascalCase |
| M12 | `SelectField.vue` 监听器泄漏 | 代码已正确移除（原始报告为误报） |
| ~~M8（旧）~~ | 点赞 TOCTOU 竞态 | UniqueConstraint 在 DB 层级序列化 |
| ~~M11（旧）~~ | 登录页开放重定向 | Vue Router 4 无法跳转外域 |
| ~~M19（旧）~~ | AdminPermissionMixin 不防重入 | `check_admin` 是无状态检查 |
| ~~FriendButton from_user_id~~ | 后端接受 `from_user_id` | 序列化器和视图均支持 |

---

## 待修复优先级

**第二阶段 — 后端稳定性与性能**
1. ✅ ~~**🔴 H16** — `GroupJoinRequest.create()` 并发竞态 → 500~~ **[已修]**
2. ✅ ~~**🔴 H17** — `Friendship.create()` 并发竞态 → 500~~ **[已修]**
3. ✅ ~~**🟠 H2-H7** — admin_dashboard N+1/无分页（6 项）~~ **[已修]**
4. ✅ ~~**🟠 H10** — chat serializer `obj.group` 无 select_related~~ **[已修]**
5. ✅ ~~**🟠 H13** — `QuizLeaderboardView` N+1~~ **[已修]**
6. ✅ ~~**🟠 H14** — `QuizReceivedQuestionsView` 无分页~~ **[已修]**
7. ✅ ~~**🟠 H15** — 管理后台图标 emoji 名~~ **[误报]**
8. **🟡 M1-M4, M13-M15, M19** — SQL/N+1/异常处理优化

**第三阶段 — 前后端字段名统一**
9. **🟡 M23-M26** — 前端读取字段名与后端 API 字段不匹配
10. **🔵 L24-L26** — 序列化器 `id` vs `user_id` 字段名不统一

**第四阶段 — 打磨**
11. **🟡 M5-M11, M16-M18, M20-M22, M25** — UI/UX 缺陷
12. **🟡 H18** — 前端 Store Action 缺少 try/catch
13. **🔵 L1-L30** — 代码整洁性 / 文档偏差
