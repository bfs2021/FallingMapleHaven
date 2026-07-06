# 枫落港 (FallingMapleHaven) — 全面审查 Bug 清单

> 来源：全栈联合审计 + 前后端连通性专项审计 2026-07-06
> 审查覆盖：后端 9 个 App × 全部 Python 文件、前端 28 个 View + 20 个 Component + 4 Store + 9 API 模块 + Docs/01~08
> 连通性审计：逐一追踪前端 API 调用 → 后端 Serializer/View 字段映射，检查字段名、类型、嵌套结构是否匹配

**总计：86 项**（Critical 13 / High 20 / Medium 26 / Low 27）

| 严重程度 | 总数 | 已修复 | 误报/跳过 | 待修复 | 说明 |
|---------|------|--------|-----------|--------|------|
| 🔴 Critical | 13 | 8 | 1 | **4** | 会导致服务器 500 / 前端白屏 / 数据丢失 / 关键 API 契约断裂 |
| 🟠 High | 20 | 5 | 1 | **14** | 功能异常 / 安全隐患 / 严重性能退化 / 字段不匹配 |
| 🟡 Medium | 26 | 1 | 0 | **25** | 功能不完善 / UI 缺陷 / 潜在风险 / 字段命名不一致 |
| 🔵 Low | 27 | 0 | 0 | **27** | 代码风格 / 优化建议 / 文档偏差 / 备用字段 |
| **总计** | **86** | **14** | **2** | **70** | 修复率 16% |

---

## 🔴 Critical

### C1. `Notification.objects.create(type=...)` 使用错误字段名（7 处） ✅

**文件：** `backend/apps/groups/views.py:122,143,377,391,403` + `backend/apps/feed/views.py:157`
**描述：** `Notification` 模型的字段是 `notification_type`，但 5 处调用用了 `type=`（Python 内置函数名）。Django ORM 会抛出 `TypeError: 'type' is an invalid keyword argument for Notification`，导致服务器 500。
**修复方案：** 将 7 处 `type=` 全部替换为 `notification_type=`。
**状态：** 已修复 — 7 处全部替换，含 `groups/views.py` 5 处 + `feed/views.py` 1 处 + tests。`notifications/signals.py` 中的信号调用使用正确字段名。

### C2. `ALLOWED_HOSTS=[]` 且 `DEBUG=False` 时所有请求被拒绝 ✅

**文件：** `backend/config/settings/base.py:17`
**描述：** 默认 `ALLOWED_HOSTS = []`。`prod.py` 从环境变量读取，`default=[]`。若 env 未设置 → 所有 HTTP/WebSocket 请求被 Django 拒绝（400 Bad Request）。
**修复方案：** `prod.py` 删除 `default=[]`，改为 `os.environ["ALLOWED_HOSTS"].split(",")` 并抛 KeyError。
**状态：** 已修复 — `prod.py` 删 `default=[]`

### C3. 管理后台 `AdminQuizQuestionsView` 构建的 `answer_map` 是死代码 ⏭️ 误报

**文件：** `backend/apps/admin_dashboard/views.py:232-234`
**描述：** `answer_map` 字典已构建但从未使用。循环内（237-253 行）未引用它——方法体内完全废弃的数据库查询。
**修复方案：** 删除死代码或整合进数据循环。
**状态：** ⏭️ 误报 — `answer_map` 在 line 238 被引用（`answer_map.get(obj.correct_answer, ...)`），交叉复核遗漏

### C4. WebSocket Origin 校验可被完全绕过 ✅

**文件：** `backend/apps/chat/consumers.py:23-36`
**描述：** Origin 校验仅在 `if origin:` 块内执行。若 WebSocket 握手不发送 `Origin` 头，`origin` 为 `None`，校验被完全跳过，任何来源的连接都被接受。
**修复方案：** 先检查 `origin is None` 也应拒绝；或使用 `channels.security.websockets.OriginValidator`。
**状态：** 已修复 — `consumers.py` 加 `origin is None` 拒绝分支

### C5. `VisitRecord` 缺少 `(visitor, visited_user)` 唯一约束导致 500 ✅

**文件：** `backend/apps/profiles/models.py:24-39`
**复现：** 同一认证用户反复访问同一他人主页 → 多次触发 `VisitRecord.objects.update_or_create(visitor=..., visited_user=...)` → 已存在多行记录 → `get()` 返回 10 行 → `MultipleObjectsReturned` → 500
**修复方案：** 在 `VisitRecord.Meta` 添加 `UniqueConstraint(fields=["visitor", "visited_user"])`；如数据已污染需先删重复行。
**状态：** 已修复 — 加 `UniqueConstraint` + 数据迁移去重

### C6. `AdminLogsView` 未校验 `user_id` 参数类型导致 500 ✅

**文件：** `backend/apps/admin_dashboard/views.py:403-405`
**复现：** `GET /api/v1/admin/logs/?user_id=RL` → `safe_int` 未包裹 → `filter(user_id='RL')` → FK 字段期待 int 收到字符串 → `ValueError: Field 'id' expected a number but got 'RL'` → 500
**修复方案：** 用 `safe_int(user_id, None)` 包裹，仅当返回非 None 时才 filter。
**状态：** 已修复 — `safe_int` 包裹

### C7. `GroupDetailPage.vue` 空数组 `[]` 被 `||` 视为 falsy ✅

**文件：** `frontend/src/views/GroupDetailPage.vue:135`
**描述：** `res.data?.results || res.data || []` — 当 `results=[]` 时，`[]` 是 falsy，回退到 `res.data`（整个响应对象），`v-for` 会遍历对象属性。
**修复方案：** 改用 `??` 操作符。
**状态：** 已修复 — `||` → `??`

### C8. `GroupTransferView` 未校验 `new_owner_id` 类型 → 500 ✅

**文件：** `backend/apps/groups/views.py:299-303`
**复现：** `POST /groups/1/transfer/` 传 `{"new_owner_id": "abc"}` → `filter(user_id="abc")` → FK 字段期待 int → `ValueError: Field 'id' expected a number but got 'abc'` → 500
**修复方案：** `safe_int(new_owner_id, None)` 包裹，非有效数字则返回 400。
**状态：** 已修复 — `safe_int` 包裹。修复中还发现群主转让后 `ChatRoomMember` 不同步的附加 Bug（见 X1）

### C9. `GroupJoinView` / `GroupJoinRequestHandleView` 并发竞态 → 500 ✅

**文件：** `backend/apps/groups/views.py:133,369`
**描述：** `GroupMember.objects.create(group=group, user=request.user)` 无唯一性兜底。并发请求下，两个请求均通过 `.exists()` 检查，然后同时 `CREATE`，UniqueConstraint 抛出 `IntegrityError` → 500。
**修复方案：** 改用 `get_or_create` 并检查 `created` 标志。
**状态：** 已修复 — `create` → `get_or_create`

### C10. `authStore.logout()` 无错误处理 → 401 后会话损坏

**文件：** `frontend/src/stores/auth.js:49-53`
**复现：** `client.js:56` 在 401 响应时调用 `authStore.logout()` → `logout()` 无 try/catch → 调用 `authApi.logout()` 失败 → `this.user = null` 不执行 → 前端认为已登录但后端 Session 已失效 → 无限死循环
**影响链：** `client.js:56` → `authStore.logout()` → catch 丢失 → 状态不一致
**修复方案：** `logout()` 内加 try/catch，无论 API 成败均设置 `this.user = null`

### C11. 🔴 `POST /auth/register/` 返回字段不全导致注册后页面数据缺失（连通性）

**文件：** `backend/apps/accounts/views.py:44-51` → `frontend/src/stores/auth.js:57-58`
**描述：** 注册 API 手写返回仅 `{user_id, username, nickname, avatar_url}` 4 个字段，而 `/me/` 和登录接口返回完整的 `UserSerializer`（13 个字段，含 `cover_url, bio, email, real_name, show_real_name, is_admin, unread_count, date_joined` 等）。注册后 `authStore.user` 缺少这些字段，设置页面和个人主页数据不完整，直到刷新页面触发 `/me/` 调用。
**影响：** 新注册用户首次看到的个人设置页和个人主页字段为空。所有依赖 `authStore.user` 的页面均受影响。
**修复方案：** 使用 `UserSerializer(user, context={"request": request}).data` 替代手写 dict

### C12. 🔴 `profiles/urls.py` 管理端路由 `<int:user_id>` 与用户名路径不兼容（连通性）

**文件：** `backend/apps/profiles/urls.py:16` → `frontend/src/views/ProfilePage.vue:29-33`
**描述：** 管理员端 `GET/PATCH /profiles/{user_id}/admin/` URL 模式使用 `<int:user_id>`，但前端的 `userId` 可能是用户名字符串（如 `/profile/johndoe`）。以用户名访问主页时，管理面板的请求会因 404 失败。同时 `userId` computed 返回 string 时，axios 请求路径会发送 `/profiles/johndoe/admin/`，Django 拒绝匹配 `<int:user_id>`。
**修复方案：** 改为 `<str:username_or_id>`，视图内用 `resolve_profile_user()` 解析

### C13. 🔴 `plugins/urls.py` profile-cards 路由 `<int:user_id>` 与用户名路径不兼容（连通性）

**文件：** `backend/apps/plugins/urls.py:7` → `frontend/src/api/plugin.js:5`
**描述：** 与 C12 相同的问题。`plugin.js:5` 调用 `/plugins/profile-cards/{userId}/`，当 `userId` 是用户名时路由不匹配，导致 `PluginEntryGrid` 完全依赖 fallback 路径 `profile.value?.plugins`。而 fallback 路径的 route 字段含 `:userId` 占位符（M17），双重故障。
**修复方案：** 改为 `<str:username_or_id>`，视图内用 `resolve_profile_user()` 解析

---

## 🟠 High

### H1. Notification `type=` 字段名错误（groups 和 feed 视图） ⏭️

*见 C1（已修复）。*

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

### H8. 聊天室列表 Prefetch 全量拉取消息 ✅

**文件：** `backend/apps/chat/views.py:23-26`
**描述：** `Prefetch("messages", queryset=Message.objects.order_by("-created_at"))` 预取房间内**所有**消息。
**修复方案：** 改用子查询取最后一条消息的 ID。
**状态：** 已修复 — 与 H9 一同修复：Subquery annotation + 序列化器读 annotation

### H9. `ChatRoomListSerializer._cached_last_msg` 仍触发新查询 ✅

**文件：** `backend/apps/chat/serializers.py:19-23`
**描述：** 即使有 prefetch，`.order_by("-created_at").first()` 生成新查询。
**修复方案：** 改用 `obj.messages.all()[0]` 访问预取数据。
**状态：** 已修复 — 与 H8 一同修复

### H10. `get_member_count` 访问 `obj.group` 无 `select_related`

**文件：** `backend/apps/chat/serializers.py:79`
**描述：** `obj.group.members.count()` 触发 `obj.group` 查询（FK 未预取）。
**修复方案：** `RoomListView` 加 `.select_related('group')`。

### H11. 前端 `FriendButton.vue` 用 `from_user_id` 而非 `request_id` ✅

**文件：** `frontend/src/components/FriendButton.vue:27`
**描述：** `friendStore.handleRequest({ from_user_id: props.userId }, action)` — 后端虽支持 `from_user_id`，但此方式在有多个未决请求时存在歧义。
**修复方案：** 改为传入具体的 `request_id`。
**状态：** 已修复 — 新增 `requestId` prop

### H12. 通知轮询（30s）全量刷新丢失滚动位置 ✅

**文件：** `frontend/src/views/NotificationsPage.vue:44`
**描述：** 轮询重新获取第 1 页并替换整个列表，用户滚动位置丢失。
**修复方案：** 恢复轮询时不重新加载列表，仅更新未读计数。
**状态：** 已修复 — 轮询仅更新未读计数

### H13. `QuizLeaderboardView` N+1 查询

**文件：** `backend/apps/plugins/quizzes/views.py:215-231`
**描述：** `QuizResult` queryset 无 `select_related('user_a', 'user_b')`，循环内每次访问 `friend.nickname` / `friend.avatar` 都触发查询。
**修复方案：** 加 `.select_related('user_a', 'user_b')`。

### H14. `QuizReceivedQuestionsView` 无分页

**文件：** `backend/apps/plugins/quizzes/views.py:57-64`
**描述：** 返回所有接收的题目，无分页。

### H15. 🟠 管理后台图标用非受支持 emoji

**文件：** `frontend/src/plugins/questions/index.js:7`、`frontend/src/plugins/quiz/index.js:7`
**描述：** 图标名 `message-question` / `help-circle` 用 kebab-case 但 lucide-vue-next 注册 PascalCase。`PluginEntryGrid`/`Icon.vue` 可能无法解析。
**更新：** 实际 `PluginEntryGrid.vue` 有 `iconMap` 映射（`message-question → messageCircleMore`、`help-circle → helpCircle`），但管理后台侧边栏如果直接使用未转换的 icon 名可能出错。

### H16. 🆕 `GroupJoinRequest.create()` 并发竞态 → 500（**新发现**）

**文件：** `backend/apps/groups/views.py:118`
**复现：** 并发申请加入私密小组 → 两个请求均通过 `exists()`/`.first()` 检查 → 同时 `create()` → UniqueConstraint 冲突 → IntegrityError → 500
**修复方案：** 改用 `get_or_create` 并检查 `created` 标志

### H17. 🆕 `Friendship.create()` 并发竞态 → 500（**新发现**）

**文件：** `backend/apps/friends/views.py:61`
**复现：** 并发发送好友申请 → 两个请求均通过 `exists()` + `first()` 检查 → 同时 `create()` → UniqueConstraint 冲突 → IntegrityError → 500
**修复方案：** 改用 `get_or_create` 并检查 `created` 标志

### H18. 前端多处 Store Action 缺少 try/catch 导致未捕获 Rejection

**涉及文件：**
| 文件 | 行号 | 缺少 try/catch 的方法 |
|------|------|----------------------|
| `frontend/src/stores/feed.js` | 27-30 | `createPost()` |
| `frontend/src/stores/feed.js` | 32-44 | `toggleLike()`, `deletePost()` (M8 确认待修) |
| `frontend/src/stores/chat.js` | 17-19 | `fetchRooms()` |
| `frontend/src/stores/chat.js` | 21-31 | `fetchMessages()` |
| `frontend/src/stores/chat.js` | 32-41 | `sendMessage()` |
| `frontend/src/stores/friend.js` | 11-17 | `fetchFriends()`, `fetchRequests()` |
| `frontend/src/stores/auth.js` | 64-67 | `updateProfile()` |
| `frontend/src/components/PostActions.vue` | 15-18 | `handleLike()` (M9 确认待修) |
| `frontend/src/views/FriendsPage.vue` | 82-89 | `goToChat()` |
| **修复方案：** 所有 async action 加 try/catch，失败时 toast 提示

### H19. 🟠 WebSocket 广播 `id` vs `message_id` 字段名不一致（连通性）

**文件：** `backend/apps/chat/views.py:157` vs `backend/apps/chat/consumers.py:105` → `frontend/src/stores/chat.js:72`
**描述：** REST API 的 `MessageSendView`（views.py:157）广播时使用 `serializer.data`，字段名为 `id`。WebSocket Consumer 的 `send_message` 处理程序（consumers.py:105）广播时使用 `message_id`。前端 chat.js:72 用 `payload.data.id || payload.data.message_id` 掩盖差异。如果任何一条路径在未来被修改且未保留两个字段名，消息 ID 解析会静默失败。
**修复方案：** 统一字段名 — 建议 Consumer 也使用 `id` 以匹配 REST 序列化器

### H20. 🟠 `unreadCounts` 状态映射从未从 API 填充 → 聊天未读徽章永远不显示（连通性）

**文件：** `frontend/src/stores/chat.js:9,17-19` → `frontend/src/views/ChatListPage.vue:56-60`
**描述：** `chatStore.unreadCounts` 声明为 `{}`，但 `fetchRooms()` 从不将每个房间的 `unread_count` 写入该映射。`ChatListPage.vue:56` 读取 `chatStore.unreadCounts[room.id]` 始终为 `undefined`（假值），#unread 徽章从不渲染。后端 `ChatRoomListSerializer` 正确返回 `unread_count`（serializers.py:16）。
**修复方案：** `fetchRooms()` 中将每个 room 的 `unread_count` 同步到 `unreadCounts[room.id]`

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

### M12. `SelectField.vue` 全局滚动/点击监听器泄漏 ✅

**文件：** `frontend/src/components/SelectField.vue:80-92`
**描述：** 每个实例在 `onMounted` 添加全局 `scroll`/`click` 监听器，`onUnmounted` 不移除。
**状态：** 已修复 — 实际代码中已正确移除监听器（原始报告为误报）

### M13. `InboxView` 匿名提问收件箱对 `answered` 参数处理不完整

**文件：** `backend/apps/plugins/questions/views.py:58-63`
**描述：** 只检查 `answered= "true"` 或 `"false"`，其他值或缺失时返回所有。分页参数 `page_size` 不接受前端自定义。

### M14. `CommentListView` 无分页

**文件：** `backend/apps/feed/views.py:282-298`
**描述：** 返回帖子的所有顶级评论，无分页。一帖 200 评论时 payload 过大。
**修复方案：** 加分页参数。

### M15. `RoomListView` 中 `RoomCreateView` 的委托调用

**文件：** `backend/apps/chat/views.py:30-31`
**描述：** `RoomListView.post` 手动实例化 `RoomCreateView.as_view()`(request)，中间件/认证处理链可能不完整。
**修复方案：** 直接复制创建逻辑或拆分为独立的 URL pattern。

### M16. 前端 `groupApi.create` / `update` 的 `Content-Type` 判断不完整

**文件：** `frontend/src/api/plugin.js:27`
**描述：** 若 data 不是 FormData 实例也不手动指定 `multipart/form-data`，但后端某些字段（如 cover_image）需要 multipart 编码。

### M17. `ProfilePage.vue` 插件卡片缓存 fallback 中的 route 未替换 userId

**文件：** `frontend/src/views/ProfilePage.vue:97-114`
**描述：** catch 分支用 `profile.value?.plugins` 中的 route（含 `:userId` 占位符），未替换为实际 userId，导航会失败。

### M18. 前端 `SettingsModulesPage.vue` ToggleSwitch 忽略 emit 值

**文件：** `frontend/src/views/SettingsModulesPage.vue`
**描述：** `@update:model-value="toggleModule(mod)"` 不接收新值，而是手动翻转 `mod.enabled`。

### M19. 🆕 `InboxView`（plugins/questions）缺少 select_related 导致 N+1

**文件：** `backend/apps/plugins/questions/views.py:59,73-74`
**描述：** `AdminQuestionSerializer` 访问 `obj.sender.nickname`（`real_sender` SerializerMethodField），但 queryset 无 `select_related('sender', 'recipient')`。仅影响 staff 用户。

### M20. 🆕 `useConfirm.js` 模块级 `resolveCallback` 被并发调用覆盖

**文件：** `frontend/src/composables/useConfirm.js:12`
**描述：** `resolveCallback` 是模块级变量。若两个组件同时调用 `confirm()`，第二个调用会覆盖第一个的 resolver，导致第一个弹窗永久挂起。
**修复方案：** 改用队列或唯一 ID 追踪

### M21. 🆕 `notifications/tests/` 测试文件仅兼容 SQLite

**文件：** `backend/apps/notifications/tests/test_c1_fix.py:90-103`
**描述：** `Notification.objects.bulk_create()` 时未传 `title`/`content`/`link`。SQLite 允许 NULL，但 PostgreSQL 中这些字段有 `NOT NULL` 约束 → 报错。
**修复方案：** 添加缺失的必填字段值

### M22. 前端 `ProfilePage.vue` 访客模式下无 guestbook Tab（与文档不一致）

**文件：** `frontend/src/views/ProfilePage.vue:48-56`
**描述：** `Docs/07` 设计文档规定访客模式 Tab 为 `posts + guestbook`，但实际实现访客模式仅显示 `posts` Tab，guestbook 在独立路由 `/profile/:userId/guestbook` 上。

### M23. 🟡 `PluginEntryGrid.vue` 读取 `plugin.desc` 但 API 返回 `description`（连通性）

**文件：** `frontend/src/components/PluginEntryGrid.vue:57` — 后端 `plugins/base.py:20-37`
**描述：** `PluginEntryGrid` 从插件数据对象读取 `plugin.desc`，而后端 `BasePlugin` 定义的字段名是 `description`（`base.py:8`）。当前因主 API 调用失败时走 fallback 路径，fallback 数据通过后端 `get_profile_data()` 返回的对象带 `description` 字段，`plugin.desc` 在 fallback 数据中不存在 → 显示 `undefined`。
**修复方案：** `PluginEntryGrid.vue:57` 将 `plugin.desc` 改为 `plugin.description`

### M24. 🟡 `RoomCreateSerializer` 使用 `type` 字段名，与模型 `room_type` 不一致（连通性）

**文件：** `backend/apps/chat/serializers.py:89` — 模型 `chat/models.py:12`
**描述：** 后端 `RoomCreateSerializer` 定义的字段名是 `type`，但 `ChatRoom` 模型的 DB 字段是 `room_type`。当前前端 `FriendsPage.vue:85` 发送 `{type: 'private', member_ids: [...]}` 正常工作，但如果未来代码按模型字段名发送 `room_type`，序列化器会静默忽略它 → 验证错误。这是等待发生的陷阱。
**修复方案：** 序列化器字段改为 `room_type` 以匹配模型，或在序列化器中加 `room_type = CharField(source='type')` 别名

### M25. 🟡 私密小组 `hasPendingRequest` 状态跨页面刷新不保持（连通性）

**文件：** `frontend/src/views/GroupDetailPage.vue:29,87-99,159`
**描述：** 加入私密小组后，`GroupJoinRequest` 被创建，`hasPendingRequest.value` 设为 `true`。但 `fetchGroup()`（onMounted）不向后端检查 `GroupJoinRequest` 状态，只从 `group` 响应读取。页面刷新后 `hasPendingRequest` 重置为 `false`，按钮恢复为"申请加入"。
**修复方案：** `fetchGroup()` 中增加对 `/groups/{id}/join-requests/?applicant=me` 的检查

### M26. 🟡 `AdminPluginsPage.vue` 读取 `plugin.description` 但管理 API 不返回该字段（连通性）

**文件：** `frontend/src/views/admin/AdminPluginsPage.vue:77` — `backend/apps/admin_dashboard/views.py:266-276`
**描述：** Admin 插件列表视图遍历 `Plugin.objects.all()`（Django model 实例），该模型只含 `name, plugin_type, is_active, config, created_at`，不含 `description` 字段。实际 `description` 在 Python 插件类上（`QuizPlugin.description`），但管理 API 未将其纳入序列化。因此所有插件显示"暂无描述"。
**修复方案：** `AdminPluginListView` 中在遍历时从 `PluginRegistry` 获取对应插件类的 `description` 属性

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
**描述：** `CHANNEL_LAYERS` 的 `hosts: [("localhost", 6379)]` 无环境变量覆盖。

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

**文件：** 多处 — `feed/views.py:119,139-140,150`, `plugins/quizzes/views.py:204-205`, `plugins/quizzes/plugin.py:13-14,48-50,76-78,93-94`, `plugins/questions/plugin.py:13-17`, `plugins/views.py:26,44`, `plugins/registry.py:16`, `accounts/models.py:25`, `accounts/serializers.py:109`, `profiles/views.py:166,336`, `admin_dashboard/views.py:204,230,444-472`
**描述：** 15+ 处方法级 import，违反 PEP 8。包括方法体内 import Q、Friendship、InterestGroup、Notification 等。

### L16. `PostImage`/`PostFile` 仍用循环内 `create()` 而非 `bulk_create`

**文件：** `backend/apps/feed/views.py:137-147`

### L17. 前端 plugin registry 的 `getActivePlugins()` 名不副实

**文件：** `frontend/src/plugins/registry.js:14-16`
**描述：** 返回所有插件而非仅活跃。

### L18. `ActivePluginsView` 权限偏严

**文件：** `backend/apps/plugins/views.py:7-8`
**描述：** 继承全局 `[IsAuthenticated]`，但作为活跃插件列表，可能应对访客开放（供首页展示）。当前无功能影响。

### L19. 🆕 `HomePage.vue` 未使用 import

**文件：** `frontend/src/views/HomePage.vue:5,11`
**描述：** `postApi`（line 5）和 `useToast`（line 11，line 17 赋值）均未使用。

### L20. 🆕 `useToast.js` setTimeout 未清理

**文件：** `frontend/src/composables/useToast.js`
**描述：** `setTimeout` 在 `show()` 中未保存 timer id，组件卸载后回调仍可能执行。

### L21. 🆕 数据库字段名文档偏差：`type` → `plugin_type` / `notification_type` / `room_type`

**文件：** `Docs/02-技术架构与数据库设计.md` §2.2.11/2.2.17/2.2.22
**描述：** 文档使用 `type` 字段名，但实际代码中：
- `plugins_plugin` 表 → `plugin_type`
- `notifications_notification` 表 → `notification_type`
- `chat_chatroom` 表 → `room_type`
**影响：** 开发者依据文档可能写出 `filter(type="quiz")` 导致 500。

### L22. 🆕 `Docs/05` 插件基类缺少 `get_summary()` / `get_profile_card_data()`

**文件：** `Docs/05-插件系统设计.md` §2.1
**描述：** `BasePlugin` 代码实际有 `get_summary()` 和 `get_profile_card_data()`（`plugins/base.py:20-37`），但文档未记录。

### L23. 聊天室 API 文档字段名不匹配

**文件：** `Docs/03-API与WebSocket接口文档.md` §6.1
**描述：** 文档响应字段为 `room_id`/`type`，实际代码返回 `id`/`room_type`。

### L24. 🔵 `CommentAuthorSerializer` 用户 ID 字段名使用 `id` 而非 `user_id`（连通性）

**文件：** `backend/apps/feed/serializers.py:96` — `frontend/src/views/CommentSection.vue:38`
**描述：** 该序列化器输出 `id` 作为用户 ID，而 `UserSerializer` 输出 `user_id`。前端用 `comment.user?.user_id || comment.user?.id` 后备兜底，但字段命名不一致。

### L25. 🔵 `FriendSerializer` 缺少 `user_id` 和 `username`（连通性）

**文件：** `backend/apps/friends/serializers.py:31-58` — `frontend/src/views/FriendsPage.vue:83`
**描述：** 好友列表序列化器返回 `id`（通过 `get_id()` 返回好友的用户 ID）而非 `user_id`，且不含 `username`。前端用 `friend.user_id || friend.id` 后备，`friend.nickname || friend.username` 后备。

### L26. 🔵 `UserSearchSerializer` 使用 `id` 而非 `user_id`（连通性）

**文件：** `backend/apps/friends/serializers.py:20-28` — `frontend/src/views/FriendsPage.vue:199,209,211`
**描述：** 用户搜索序列化器输出 `id` 而非 `user_id`，前端用 `user.user_id || user.id` 后备。字段名不统一。

### L27. 🔵 前端 WebSocket 从未发送 `send_message` 消息（连通性）

**文件：** `backend/apps/chat/consumers.py:58-79`（Consumer 处理 `send_message`）— `frontend/src/stores/chat.js`
**描述：** Consumer 的 `receive()` 正确处理 `send_message` 类型，但前端通过 REST API（`chat.js:42-44` 的 `sendMessage` 调用 `fetch`）发送消息。WebSocket `send_message` 流程从未被前端使用，且无测试覆盖，重构时可能退化。

### L28. 🔵 Admin 问答列表返回裸数组而非分页包装器（连通性）

**文件：** `backend/apps/admin_dashboard/views.py:222-254`
**描述：** `/admin/quiz/questions/` 返回 `{code: 0, data: [...]}`（裸数组），而所有其他管理列表端点返回 `{code: 0, data: {total, page, page_size, results: [...]}}`。前端 `AdminQuizPage.vue:20` 用 `res.data`（裸数组）处理，所以功能正常，但接口风格不一致。

### L29. 🔵 `GroupJoinView` 中 `ChatRoomMember.create()` 的竞态条件

**文件：** `backend/apps/groups/views.py:135-137`
**描述：** `ChatRoomMember.objects.create()` 前只有 `.exists()` 检查，无唯一性兜底。并发请求可触发唯一约束违规。

### L30. 🔵 `RoomCreateView` 私聊创建 TOCTOU 竞态

**文件：** `backend/apps/chat/views.py:97-103`
**描述：** 先 `.exists()` 检查再创建，存在竞态窗口，并发创建会得到重复私聊房间。

---

## 🆕 额外发现并修复（测试驱动发现）

### X1. `GroupTransferView` 转让群主后 `ChatRoomMember` 不同步 ✅

**文件：** `backend/apps/groups/views.py:310-316`
**复现：** 群主 A 将群转让给 B → `GroupMember.role` 改为 `member`/`owner`，`group.creator` 改为 B，但 `ChatRoomMember` 无变化 → B 发消息时 `ChatRoomMember.DoesNotExist` → 500
**根因：** 转让逻辑只改了 `GroupMember` 和 `Group` 表，未同步 `ChatRoom` 的成员表。
**修复：** 在 `transaction.atomic()` 内追加 `ChatRoomMember.objects.get_or_create(room=room, user_id=new_owner_id)`

---

## 交叉复核已排除的误报

| 原编号 | 说明 | 排除原因 |
|--------|------|---------|
| C3 | answer_map 死代码 | line 238 实际使用 |
| M8（旧） | 点赞 TOCTOU 竞态 | UniqueConstraint 在 DB 层级序列化 |
| M11（旧） | 登录页开放重定向 | Vue Router 4 无法跳转外域 |
| M12 | SelectField 监听器泄漏 | 代码已正确 cleanup |
| M19（旧） | AdminPermissionMixin 不防重入 | `check_admin` 是无状态检查 |
| FriendButton from_user_id | 后端接受 `from_user_id` | 序列化器和视图均支持 |

---

## 修复状态 & 待修复优先级

### ✅ 已修复（14 项）
| 编号 | 项目 | 说明 |
|------|------|------|
| C1 | `Notification.type=` → `notification_type=` | 7 处字段名修正 |
| C2 | `ALLOWED_HOSTS` 默认值 | `prod.py` 删 `default=[]` |
| C3 | ⏭️ `answer_map` 死代码 | 误报，line 238 实际使用 |
| C4 | WebSocket Origin 校验 | 加 `origin is None` 拒绝 |
| C5 | `VisitRecord` 唯一约束 | UniqueConstraint + 迁移去重 |
| C6 | `AdminLogsView` 类型校验 | `safe_int` 包裹 |
| C7 | `GroupDetailPage.vue` `\|\|` | → `??` 操作符 |
| C8 | `GroupTransferView` 类型校验 | `safe_int` 包裹 |
| C9 | `GroupJoinView` 并发竞态 | `create` → `get_or_create` |
| H8+H9 | 聊天室列表 N+1 | Subquery annotation 替代 Prefetch |
| H11 | FriendButton `requestId` prop | 新增 prop 精确指定请求 |
| H12 | 通知轮询丢滚动 | 仅更新未读计数 |
| M12 | `SelectField.vue` 监听器泄漏 | 误报 — 代码已正确 cleanup |
| X1 | 群转让 ChatRoomMember 同步 | 转让后 `get_or_create` 成员记录 |

### 📋 待修复优先级

**第一阶段 — 前后端接口断裂（功能无法正常使用）**
1. **🔴 C11** — 注册返回字段不全 → 页面数据缺失
2. **🔴 C12/C13** — `<int:user_id>` 不兼容用户名路径 → 管理面板和插件卡片断路
3. **🔴 C10** — `authStore.logout()` 无 try/catch → 401 后状态损坏
4. **🟠 H19** — WS `id` vs `message_id` 不一致 → 消息 ID 解析脆弱
5. **🟠 H20** — `unreadCounts` 未填充 → 聊天未读徽章不显示

**第二阶段 — 后端稳定性与性能**
6. **🔴 H16/H17** — 并发竞态 → IntegrityError → 500
7. **🟠 H2-H7, H10, H13-H15** — N+1 查询和无分页
8. **🟡 M1-M4, M13-M15, M19** — SQL/N+1/异常处理优化

**第三阶段 — 前后端字段名统一**
9. **🟡 M23-M26** — 前端读取字段名与后端 API 字段不匹配
10. **🔵 L24-L26** — 序列化器 `id` vs `user_id` 字段名不统一

**第四阶段 — 打磨**
11. **🟡 M5-M11, M16-M18, M20-M22, M25** — UI/UX 缺陷
12. **🔵 L1-L30** — 代码整洁性 / 文档偏差
