# 枫落港 (FallingMapleHaven) — 全面审查 Bug 清单

> 来源：全栈联合审计 + 2 轮交叉复核 2026-07-05
> 本次审查覆盖：后端 9 个 App × 5 文件类型、前端 17 个 View + 20 个 Component + 4 Store + 9 API 模块

**总计：60 项**（Critical 9 / High 15 / Medium 18 / Low 18）

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| 🔴 Critical | 9 | 会导致服务器 500 / 前端白屏 / 数据丢失 |
| 🟠 High | 15 | 功能异常 / 安全隐患 / 严重性能退化 |
| 🟡 Medium | 18 | 功能不完善 / UI 缺陷 / 潜在风险 |
| 🔵 Low | 18 | 代码风格 / 优化建议 |

---

## 🔴 Critical

### C1. `Notification.objects.create(type=...)` 使用错误字段名（7 处）

**文件：** `backend/apps/groups/views.py:122,143,377,391,403` + `backend/apps/feed/views.py:157`
**描述：** `Notification` 模型的字段是 `notification_type`，但 5 处调用用了 `type=`（Python 内置函数名）。Django ORM 会抛出 `TypeError: 'type' is an invalid keyword argument for Notification`，导致服务器 500。
**修复方案：** 将 7 处 `type=` 全部替换为 `notification_type=`。

### C2. `ALLOWED_HOSTS=[]` 且 `DEBUG=False` 时所有请求被拒绝

**文件：** `backend/config/settings/base.py:17`
**描述：** 默认 `ALLOWED_HOSTS = []`。`prod.py` 从环境变量读取，`default=[]`。若 env 未设置 → 所有 HTTP/WebSocket 请求被 Django 拒绝（400 Bad Request）。
**修复方案：** `prod.py` 删除 `default=[]`，改为 `os.environ["ALLOWED_HOSTS"].split(",")` 并抛 KeyError。

### C3. 管理后台 `AdminQuizQuestionsView` 构建的 `answer_map` 是死代码

**文件：** `backend/apps/admin_dashboard/views.py:232-234`
**描述：** `answer_map` 字典已构建但从未使用。循环内（237-253 行）未引用它——方法体内完全废弃的数据库查询。
**修复方案：** 删除死代码或整合进数据循环。

### C4. WebSocket Origin 校验可被完全绕过

**文件：** `backend/apps/chat/consumers.py:23-36`
**描述：** Origin 校验仅在 `if origin:` 块内执行。若 WebSocket 握手不发送 `Origin` 头，`origin` 为 `None`，校验被完全跳过，任何来源的连接都被接受。
**修复方案：** 先检查 `origin is None` 也应拒绝；或使用 `channels.security.websockets.OriginValidator`。

### C5. `VisitRecord` 缺少 `(visitor, visited_user)` 唯一约束导致 500

**文件：** `backend/apps/profiles/models.py:24-39`
**复现：** 同一认证用户反复访问同一他人主页 → 多次触发 `VisitRecord.objects.update_or_create(visitor=..., visited_user=...)` → 已存在多行记录 → `get()` 返回 10 行 → `MultipleObjectsReturned` → 500
**修复方案：** 在 `VisitRecord.Meta` 添加 `UniqueConstraint(fields=["visitor", "visited_user"])`；如数据已污染需先删重复行。

### C6. `AdminLogsView` 未校验 `user_id` 参数类型导致 500

**文件：** `backend/apps/admin_dashboard/views.py:403-405`
**复现：** `GET /api/v1/admin/logs/?user_id=RL` → `safe_int` 未包裹 → `filter(user_id='RL')` → FK 字段期待 int 收到字符串 → `ValueError: Field 'id' expected a number but got 'RL'` → 500
**修复方案：** 用 `safe_int(user_id, None)` 包裹，仅当返回非 None 时才 filter。

### C7. `GroupDetailPage.vue` 空数组 `[]` 被 `||` 视为 falsy

**文件：** `frontend/src/views/GroupDetailPage.vue:135`
**描述：** `res.data?.results || res.data || []` — 当 `results=[]` 时，`[]` 是 falsy，回退到 `res.data`（整个响应对象），`v-for` 会遍历对象属性。
**修复方案：** 改用 `??` 操作符。

### C8. `GroupTransferView` 未校验 `new_owner_id` 类型 → 500

**文件：** `backend/apps/groups/views.py:299-303`
**复现：** `POST /groups/1/transfer/` 传 `{"new_owner_id": "abc"}` → `filter(user_id="abc")` → FK 字段期待 int → `ValueError: Field 'id' expected a number but got 'abc'` → 500
**修复方案：** `safe_int(new_owner_id, None)` 包裹，非有效数字则返回 400。

### C9. `GroupJoinView` / `GroupJoinRequestHandleView` 并发竞态 → 500

**文件：** `backend/apps/groups/views.py:133,369`
**描述：** `GroupMember.objects.create(group=group, user=request.user)` 无唯一性兜底。并发请求下，两个请求均通过 `.exists()` 检查，然后同时 `CREATE`，UniqueConstraint 抛出 `IntegrityError` → 500。
**修复方案：** 改用 `get_or_create` 并检查 `created` 标志。

---

## 🟠 High

### H1. Notification `type=` 字段名错误（groups 和 feed 视图）

*见 C1。*

### H2. `AdminPostListView` 未使用 `select_related("author")`

**文件：** `backend/apps/admin_dashboard/views.py:106`
**描述：** `Post.objects.all()` 后序列化 `author.nickname`，每篇动态多一次查询。
**修复方案：** 加 `.select_related("author")`。

### H3. `AdminAnonymousQuestionsView` 未使用 `select_related`

**文件：** `backend/apps/admin_dashboard/views.py:206`
**描述：** 查询 `AnonymousQuestion` 未 select_related recipient/sender。
**修复方案：** 加 `.select_related("recipient", "sender")`。

### H4. `AdminGroupListView` N+1 且无分页

**文件：** `backend/apps/admin_dashboard/views.py:525-543`
**描述：** 遍历时 `g.creator.nickname` 无 `select_related('creator')`；全部返回无分页。
**修复方案：** 加 `select_related('creator')` 和分页逻辑。

### H5. `AdminPluginListView` / `AdminPluginConfigView` 无分页

**文件：** `backend/apps/admin_dashboard/views.py:260,372`
**描述：** 插件列表和配置列表均无分页。

### H6. `AdminQuizQuestionsView` 无分页

**文件：** `backend/apps/admin_dashboard/views.py:230`
**描述：** 问卷题列表无分页，数据量大会 OOM。

### H7. `AdminLogsView` N+1

**文件：** `backend/apps/admin_dashboard/views.py:397,416`
**描述：** `SiteLog.objects.all()` 无 `select_related('user')`，`AdminLogSerializer` 访问 `user.nickname` 触发 N+1。

### H8. 聊天室列表 Prefetch 全量拉取消息

**文件：** `backend/apps/chat/views.py:23-26`
**描述：** `Prefetch("messages", queryset=Message.objects.order_by("-created_at"))` 预取房间内**所有**消息。序列化器实际只需要 `obj.messages.order_by("-created_at").first()`（最新一条）。全量预取导致内存爆炸和大量数据传输。
**修复方案：** 改用子查询取最后一条消息的 ID，或 `annotate(last_message_id=Subquery(...))`。

### H9. `ChatRoomListSerializer._cached_last_msg` 仍触发新查询

**文件：** `backend/apps/chat/serializers.py:19-23`
**描述：** 即使有 prefetch，`.order_by("-created_at").first()` 生成新查询，不使用预取缓存。
**修复方案：** 改用 `obj.messages.all()[0]` 访问预取数据（需确保预取已按 `-created_at` 排序）。

### H10. `get_member_count` 访问 `obj.group` 无 `select_related`

**文件：** `backend/apps/chat/serializers.py:79`
**描述：** `obj.group.members.count()` 触发 `obj.group` 查询（FK 未预取）。
**修复方案：** `RoomListView` 加 `.select_related('group')`。

### H11. 前端 `FriendButton.vue` 用 `from_user_id` 而非 `request_id`

**文件：** `frontend/src/components/FriendButton.vue:27`
**描述：** `friendStore.handleRequest({ from_user_id: props.userId }, action)` — 后端虽支持 `from_user_id`，但此方式在有多个未决请求时存在歧义，无法区分同一用户的多条请求。
**修复方案：** 改为传入具体的 `request_id`（需从请求列表获取）。

### H12. 通知轮询（30s）全量刷新丢失滚动位置

**文件：** `frontend/src/views/NotificationsPage.vue:44`
**描述：** 轮询重新获取第 1 页并替换整个列表，用户滚动位置丢失。已有滚动恢复代码，但选择器与模板 DOM 不匹配。
**修复方案：** 恢复轮询时不重新加载列表，仅更新未读计数；或增量更新。

### H13. `QuizLeaderboardView` N+1 查询

**文件：** `backend/apps/plugins/quizzes/views.py:215-231`
**描述：** `QuizResult` queryset 无 `select_related('user_a', 'user_b')`，循环内每次访问 `friend.nickname` / `friend.avatar` 都触发查询。
**修复方案：** 加 `.select_related('user_a', 'user_b')`。

### H14. `QuizReceivedQuestionsView` 无分页

**文件：** `backend/apps/plugins/quizzes/views.py:57-64`
**描述：** 返回所有接收的题目，无分页。

### H15. 管理后台图标用非受支持 emoji

**文件：** `frontend/src/plugins/questions/index.js:7`、`frontend/src/plugins/quiz/index.js:7`
**描述：** 图标名 `message-question` / `help-circle` 用 kebab-case 但 lucide-vue-next 注册 PascalCase。`PluginEntryGrid`/`Icon.vue` 可能无法解析。
**修复方案：** 保证 icon 名与 lucide 组件名匹配。

---

## 🟡 Medium

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
**描述：** `from django.db.models import Q` 和 `from apps.friends.models import Friendship` 写在方法体内而非文件顶部。

### M5. 前端 `ChatRoomPage.vue` 每次挂载断连 WS

**文件：** `frontend/src/views/ChatRoomPage.vue:42-43`
**描述：** `disconnectWs()` + `connectWs()` 在每次进入聊天室时执行。同一个 WS 连接可处理所有房间。
**修复方案：** 移除 disconnect/connect 调用。

### M6. 前端 `ChatRoomPage.vue` 进入房间未清除未读计数

**文件：** `frontend/src/views/ChatRoomPage.vue`
**描述：** 进入聊天室后不调用 API 标记已读，聊天列表未读计数不变。
**修复方案：** 后端 RoomMessagesView 已更新 `last_read_at`，前端需刷新房间列表。

### M7. `HomePage.vue` 快速切换标签页丢失请求

**文件：** `frontend/src/views/HomePage.vue:58-65`
**描述：** `switchTag` 无去抖/竞态处理。快速切换标签时，前一个请求的 `loading=true` 阻塞后一个请求。
**修复方案：** 加 AbortController 或防抖。

### M8. 前端 `feedStore` 无错误处理

**文件：** `frontend/src/stores/feed.js:32-44`
**描述：** `toggleLike` 和 `deletePost` 无 try/catch，网络失败导致未捕获的 Promise rejection。
**修复方案：** 加 try/catch 和 toast 提示。

### M9. `PostActions.vue` like 操作无错误处理

**文件：** `frontend/src/components/PostActions.vue:15-18`
**描述：** `handleLike` 无 try/catch，失败时前台无反馈。

### M10. `ProfilePage.vue` `isOwner` 比较可能类型不匹配

**文件：** `frontend/src/views/ProfilePage.vue:35`
**描述：** `authStore.user?.user_id` 为 number，`userId.value` 可能为 string（如 username 路径），`===` 失败。
**修复方案：** `==` 或 `Number(userId.value)`。

### M11. `QuestionBoxPage.vue` 单个 `submittingAnswer` 阻塞所有回答按钮

**文件：** `frontend/src/views/QuestionBoxPage.vue:110`
**描述：** 一个布尔值控制所有问题，提交答案时其他所有按钮被禁用。
**修复方案：** 改为 `Record<questionId, boolean>`。

### M12. `SelectField.vue` 全局滚动/点击监听器泄漏

**文件：** `frontend/src/components/SelectField.vue:58-60`
**描述：** 每个实例在 `onMounted` 添加全局 `scroll`/`click` 监听器，`onUnmounted` 不移除。

### M13. `InboxView` 匿名提问收件箱对 `answered` 参数处理不完整

**文件：** `backend/apps/plugins/questions/views.py:58-63`
**描述：** 只检查 `answered= "true"` 或 `"false"`，其他值或缺失时返回所有。但分页参数 `page_size` 默认为 hardcoded 20，不接受前端自定义。

### M14. `CommentListView` 无分页

**文件：** `backend/apps/feed/views.py:282-298`
**描述：** 返回帖子的所有顶级评论，无分页。一帖 200 评论时 payload 过大。
**修复方案：** 加分页参数。

### M15. `RoomListView` 中 `RoomCreateView` 的委托调用

**文件：** `backend/apps/chat/views.py:30-31`
**描述：** `RoomListView.post` 手动实例化 `RoomCreateView.as_view()`(request)，创建了新的 View 实例，但中间件/认证处理链可能不完整。
**修复方案：** 直接复制创建逻辑或拆分为独立的 URL pattern。

### M16. 前端 `groupApi.create` / `update` 的 `Content-Type` 判断不完整

**文件：** `frontend/src/api/plugin.js:27`
**描述：** 若 data 不是 FormData 实例也不手动指定 `multipart/form-data`，但后端某些字段（如 cover_image）需要 multipart 编码。

### M17. `ProfilePage.vue` 插件卡片缓存 fallback 中的 route 未替换 userId

**文件：** `frontend/src/views/ProfilePage.vue:97-114`
**描述：** catch 分支用 `profile.value?.plugins` 中的 route（含 `:userId` 占位符），未替换为实际 userId，导航会失败。

### M18. 前端 `settingsModules` / `settings` 页面 ToggleSwitch 忽略 emit 值

**文件：** `frontend/src/views/SettingsModulesPage.vue`
**描述：** `@update:model-value="toggleModule(mod)"` 不接收新值，而是手动翻转 `mod.enabled`。若 ToggleSwitch emit 值滞后，方向可能错。

---

## 🔵 Low

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
**描述：** `CHANNEL_LAYERS"redis"` 的 `hosts: [("localhost", 6379)]` 无环境变量覆盖。

### L5. 非匿名用户速率限制缺失

**文件：** `backend/config/settings/base.py:140-145`
**描述：** 仅配置了 `AnonRateThrottle`，认证用户无限流。

### L6. `AdminQuizQuestionsView` 中 `answer_map` 死代码（见 C3）

### L7. `QuizLeaderboardView` 中 `answered_ids` 死代码

**文件：** `backend/apps/plugins/quizzes/views.py:132-134`
**描述：** `answered_ids` 赋值后从未使用。

### L8. `AdminUserListView` 限 `is_staff` 更新只检查 `is_superuser`

**文件：** `backend/apps/admin_dashboard/views.py:81`
**描述：** `if request.user.is_superuser: allowed_fields.add("is_staff")` — 权限粒度偏粗，但符合预期。

### L9. `AdminUserUpdateView` 审计日志记录原始 request.data

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

**文件：** `backend/apps/feed/views.py:119,139-140,150` 等多处

### L16. `PostImage`/`PostFile` 仍用循环内 `create()` 而非 `bulk_create`

**文件：** `backend/apps/feed/views.py:137-147`

### L17. 前端 plugin registry 的 `getActivePlugins()` 名不副实

**文件：** `frontend/src/plugins/registry.js:14-16`
**描述：** 返回所有插件而非仅活跃。

### L18. `ActivePluginsView` 无认证限制

**文件：** `backend/apps/plugins/views.py:7-8`
**描述：** `permission_classes = []`（默认 AllowAny），任何人都可获取活跃插件列表。

---

## 交叉复核已排除的误报

| 原编号 | 说明 | 排除原因 |
|--------|------|---------|
| M8 | 点赞 TOCTOU 竞态 | Django `UniqueConstraint(post, user)` 在 DB 层级序列化冲突 |
| M11 | 登录页开放重定向 | Vue Router 4 客户端路由无法跳转到外域 |
| M19 | AdminPermissionMixin 不防重入 | `check_admin` 是无状态检查 |
| FriendButton from_user_id | 后端 FriendHandleSerializer 接受 `from_user_id` | 序列化器和视图均支持该参数 |

---

## 修复优先级建议

1. **立即（Critical）：** C1（7 处 type→notification_type，否则 500）
2. **立即（Critical）：** C5（VisitRecord 唯一约束缺失 → 500）
3. **立即（Critical）：** C6（AdminLogsView 参数类型未校验 → 500）
4. **立即（Critical）：** C8（GroupTransferView 类型未校验 → 500）
5. **立即（Critical）：** C9（GroupMember.create 竞态 → 500）
6. **立即（Critical）：** C2（ALLOWED_HOSTS 配置）
3. **高：** H2~H8、H13（N+1 和性能问题）
4. **高：** H11（FriendButton 请求 ID 问题）
5. **高：** C4（WebSocket Origin 绕过）
6. **中：** M1~M18（按严重性排序）
7. **低：** L1~L18（代码整洁性）
