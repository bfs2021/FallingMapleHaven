# 枫落港 (FallingMapleHaven) 全栈联合审计报告

> 审计日期：2026-07-04
> 审计方式：全栈代码逐行审查 + 双 subagent 交叉复核
> 审查范围：全部 74 个 API 端点对、123+ 源文件、数据流与组件交互
> **总计：57 个 Bug**（Critical 6 / High 20 / Medium 18 / Low 13）

## 摘要

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| 🔴 Critical | 6 | 功能完全不可用或严重数据安全 |
| 🟠 High | 20 | 功能异常/性能严重退化/中等安全隐患 |
| 🟡 Medium | 18 | 功能不完善/UI 缺陷/潜在风险 |
| 🔵 Low | 13 | 代码风格/轻微优化建议 |

## 交叉复核已排除的误报

| 原编号 | 说明 | 排除原因 |
|--------|------|---------|
| ~~M8~~ | 点赞 TOCTOU 竞态 | Django `UniqueConstraint(post, user)` 在 DB 层级序列化冲突，`get_or_create` 兜底 |
| ~~M11~~ | 登录页开放重定向 | Vue Router 4 是客户端路由，`router.push()` 无法跳转到外域，仅匹配 404 兜底路由 |
| ~~M19~~ | AdminPermissionMixin 不防重入 | `check_admin` 是无状态检查，每次返回新 Response 是正常模式，不存在共享状态 |
| ~~L9~~ | 5+ 图片无最大高度 | `grid-cols-3` + `h-32` + `object-cover` 已限制高度，6 图仅两行 ~264px |

---

## 🔴 Critical 级别

### C1. 文件上传使用普通对象而非 FormData

**文件：** `frontend/src/api/auth.js:10-15`
**描述：** `uploadAvatar`/`uploadCover` 将文件作为 JS 对象 `{ avatar: file }` 传递，显式设置 `Content-Type: multipart/form-data` 但 Axios 默认序列化 JSON，文件被字符串化为 `{}`。
**影响：** 头像和封面图上传完全不可用。

### C2. 3 张图片布局中第一张图重复显示，第三张图缺失

**文件：** `frontend/src/components/PostImageGrid.vue:20-21`
**描述：** `v-for="(img, i) in [1,2]"` 中 `i` 为数组索引 `0,1`，分别取 `images[0]`（与大格重复）和 `images[1]`，`images[2]` 永远不显示。
**影响：** 发布 3 张图片时第三张不可见。

### C3. 滚动加载时页码双重递增导致隔页跳过

**文件：** `frontend/src/views/HomePage.vue:51` + `frontend/src/stores/feed.js:22`
**描述：** 滚动处理器 `feedStore.currentPage++`(HomePage:51) 与 `fetchPosts()` 内部 `this.currentPage += 1`(feed.js:22) 双重递增。请求页码为 1→3→5→7…，偶数页全部跳过。
**影响：** 无限滚动丢失一半数据。

### C4. `int()` 转换无异常处理导致 500 错误

**文件：** 共 11 处
**影响：** `?page=abc` 或 `?days=abc` 抛出 `ValueError`，返回 500。
**位置：** `feed/views.py:57`、`profiles/views.py:104/156/189`、`chat/views.py:48`、`notifications/views.py:20`、`groups/views.py:242`、`admin_dashboard/views.py:328/369/510/545`

### C5. WebSocket ChatConsumer 房间订阅仅在连接时执行

**文件：** `backend/apps/chat/consumers.py:19-24`
**描述：** Channel Layer group 订阅仅在 `connect()` 时执行。WebSocket 保持打开期间新创建/加入的房间不加入 group。
**影响：** 新聊天室的实时消息完全不送达。

### C6. `UserSerializer.get_unread_count` — 每次序列化触发 COUNT 查询

**文件：** `backend/apps/accounts/serializers.py:106-108`
**描述：** 每个 `UserSerializer` 实例化都执行一次 `Notification.objects.filter(recipient=user, is_read=False).count()`。在管理后台用户列表（`AdminUserListView`）等返回多用户的场景中，线性放大为 N+1 查询。
**影响：** 1000 个用户 = 1000 次额外 COUNT 查询。

---

## 🟠 High 级别

### H1. 普通 staff 可随意授予其他用户 staff 权限

**文件：** `backend/apps/admin_dashboard/views.py:69`
**描述：** `allowed_fields = {"is_active", "is_staff"}` 未限制只能由 superuser 修改 `is_staff`。任何 staff 可将普通用户或另一 staff 提升为 staff。
**影响：** 权限体系完全失效。

### H2. 好友排行榜 API 因字段名错误直接 500

**文件：** `backend/apps/plugins/quizzes/views.py:207-210`
**描述：** `QuizLeaderboardView` 使用 `Q(sender=request.user)` 和 `Q(receiver=request.user)`，但 `Friendship` 模型字段是 `from_user`/`to_user`。运行时抛出 `FieldError`。
**影响：** 默契问答"好友排行"标签页完全不可用。

### H3. 管理后台列表视图无分页

**文件：** `backend/apps/admin_dashboard/views.py:35-53` 等多处
**描述：** 用户列表、帖子列表、评论列表、日志列表均返回全量数据。
**影响：** 数据量上万时导致 OOM 或响应超时。

### H4. 聊天室列表序列化器 N+1（5+ 因子）

**文件：** `backend/apps/chat/serializers.py:21-59`
**描述：** 6 个 SerializerMethodField 各发起独立 SQL，其中 `get_last_message` 和 `get_last_message_at` 还重复查询。20 个聊天室产生 100+ 条 SQL。

### H5. 点赞/评论数 `.count()` 忽略预取缓存

**文件：** `backend/apps/feed/serializers.py:58`
**描述：** `.count()` 始终发起 COUNT 查询，即使数据已被 `prefetch_related` 加载。

### H6. 访客足迹无去重/限流

**文件：** `backend/apps/profiles/views.py:74`
**描述：** 每次刷新个人主页生成一条新 `VisitRecord`。频繁刷新产生大量垃圾数据。

### H7. 任何已认证用户可向任意小组发布动态

**文件：** `backend/apps/feed/views.py:121-122`
**描述：** `PostCreateView` 接受 `group_id` 但**不做任何成员身份校验**。非成员可向任何私密小组发帖。此外，**不验证 group 是否存在**，无效 `group_id` 触发 FK IntegrityError → 500。

### H8. 直接修改组件 Prop：`props.post.comment_count -= 1`

**文件：** `frontend/src/components/PostCard.vue:60-62`
**描述：** 子组件直接修改 prop 嵌套属性，违反 Vue 单向数据流。

### H9. 相对时间函数无输入验证

**文件：** `frontend/src/utils/time.js:3`
**描述：** `dateString` 为 `null`/`undefined`/`""` 时 `new Date()` 返回 `NaN`，所有时间戳显示 "NaN分钟前"。

### H10. 管理后台插件图标为非受支持的表情符号

**文件：** `frontend/src/plugins/questions/index.js:10`
**描述：** `icon: '🕵️'` 非 `lucide-vue-next` 图标名，侧边栏不显示。

### H11. Axios 401 拦截器绕过 Pinia store action

**文件：** `frontend/src/api/client.js:56`
**描述：** `authStore.user = null` 绕过 `authStore.logout()`，不触发 WebSocket 断开等副作用。

### H12. `PostListView` 缺少 `select_related("group")`

**文件：** `backend/apps/feed/views.py:62`
**描述：** `PostListView` 使用 `.select_related("author").prefetch_related("images", "comments", "likes")` 但缺失 `.select_related("group")`。`PostSerializer.get_group()` 访问 `obj.group.name` 时每个带 `group_id` 的 post 都触发一次额外查询。

### H13. `VisitorListView` 缺少 `select_related("visitor")`

**文件：** `backend/apps/profiles/views.py:109`
**描述：** `VisitorSerializer` 访问 `obj.visitor.id`/`nickname`/`avatar`，但 queryset 无 `select_related("visitor")`。

### H14. `UserPostListView` 完全缺失预取（N+1 黑洞）

**文件：** `backend/apps/profiles/views.py:131,160`
**描述：** 无 `select_related("author")`、无 `prefetch_related("images", "comments", "likes")`。每页 20 条动态 → ~80+ 额外 SQL。

### H15. `GroupPostsView` 无预取

**文件：** `backend/apps/groups/views.py:240-247`
**描述：** 同 H14 N+1 问题。

### H16. `CommentListView` 评论作者 N+1

**文件：** `backend/apps/feed/views.py:274-276`
**描述：** 无 `select_related("author")`。

### H17. `RoomMessagesView` 消息发送者 N+1

**文件：** `backend/apps/chat/views.py:47-53`
**描述：** 无 `select_related("sender")`。

### H18. `GuestbookListView` 留言作者 N+1

**文件：** `backend/apps/profiles/views.py:187-196`
**描述：** 无 `select_related("author")`。

### H19. `AdminQuizQuestionsView` 循环内查询 N+1

**文件：** `backend/apps/admin_dashboard/views.py:188`
**描述：** `QuizAnswer.objects.filter(question=q).first()` 在 `for q in questions` 循环内执行。100 个题目 = 100 次额外查询。

### H20. `GroupDetailView` 暴露私密小组信息

**文件：** `backend/apps/groups/views.py:61-73`
**描述：** `GroupDetailView` 仅检查 `IsAuthenticated`，未校验当前用户是否为私密小组的成员。任何已认证用户可查看任意私密小组的成员列表、描述等信息。`GroupListView` 对已认证用户也不过滤私密小组。

---

## 🟡 Medium 级别

### M1. 应使用 ImageField 而非 FileField

**文件：** `backend/apps/accounts/models.py:10`、`feed/models.py:46`
**影响：** 头像、封面、PostImage 使用 `FileField`，无图片格式显式验证。

### M2. PIL `Image.verify()` 验证不充分

**文件：** `backend/apps/accounts/views.py:177`
**描述：** `verify()` 只检查文件头，可被合成的图片文件绕过。

### M3. 批量通知使用逐条 `create()` 而非 `bulk_create`

**文件：** `backend/apps/feed/views.py:148`、`groups/views.py:136`、`groups/views.py:380`

### M4. WebSocket 消息静默截断 2000 字符

**文件：** `backend/apps/chat/consumers.py:42`
**描述：** 超长消息在 consumer 截断，发送方无通知。REST API 端无此限制。

### M5. 匿名提问未校验接收方是否开启该插件

**文件：** `backend/apps/plugins/questions/views.py:28`
**描述：** 全局启用后用户无法 opt-out。

### M6. 通知内容无内容过滤

**文件：** `backend/apps/plugins/questions/views.py:39`
**描述：** 匿名提问前 100 字符直接存入通知，无 HTML 剥离。

### M7. 默认密钥不安全

**文件：** `backend/config/settings/base.py:11`
**描述：** `SECRET_KEY` 硬编码默认值 `"django-insecure-change-me-in-production"`。

### M8. `type` 字段遮蔽 Python 内置函数

**文件：** `backend/apps/chat/models.py:12`

### M9. 路由守卫未在所有路由上初始化 Session

**文件：** `frontend/src/router/index.js:114`
**描述：** 公共路由 `/`、`/profile/:userId`、`/groups` 不触发 `ensureSession`。

### M10. `PostDetailView` 未校验小组动态可见性

**文件：** `backend/apps/feed/views.py:161-204`
**描述：** 检查 `visibility` 但未校验当前用户是否为所属私密小组成员。

### M11. `FriendButton` 的 `userId` prop 类型声明与使用不一致

**文件：** `frontend/src/components/FriendButton.vue:6` + `frontend/src/views/ProfilePage.vue:198`
**描述：** 声明 `Number` 但 `ProfilePage` 可能传入字符串。

### M12. `ensureSession` 模块级 Promise 可导致永久挂起

**文件：** `frontend/src/stores/auth.js:37`
**描述：** `sessionInitPromise.finally()` 重置仅在 Promise 完成/拒绝后执行。

### M13. 通知轮询全量刷新丢失滚动位置

**文件：** `frontend/src/views/NotificationsPage.vue:44`
**描述：** 每 30 秒拉取全量通知列表替换页面数据。

### M14. `fetchNotifications` 的 `res.data` 回退逻辑不安全

**文件：** `frontend/src/views/NotificationsPage.vue:63`
**描述：** `res.data?.results || res.data || []` 若 `res.data` 是无 `results` 的对象，会将对象展开到数组。

### M15. 小组列表 `get_is_member` 每人每次查询

**文件：** `backend/apps/groups/serializers.py:29-31`
**描述：** `obj.members.filter(user_id=request.user.id).exists()` 对列表中每个小组触发一次查询。`GroupDetailSerializer:53-56` 相同问题。

### M16. `needsTruncation` 不是计算属性

**文件：** `frontend/src/components/PostCard.vue:33`
**描述：** 使用 `const` 常量，`post.content` 变化时不重新计算截断状态。

### M17. WebSocket 消息未做来源验证

**文件：** `frontend/src/stores/chat.js:67`
**描述：** `JSON.parse(event.data)` 后直接信任所有字段，未验证 `event.origin`。防御纵深缺口，实际利用需配合 XSS。

### M18. 匿名提问收件箱无分页

**文件：** `backend/apps/plugins/questions/views.py:57`
**描述：** `AnonymousQuestion.objects.filter(recipient=request.user)` 返回全量数据，无分页限制。

---

## 🔵 Low 级别

### L1. 硬编码特殊字符集重复定义

**文件：** `backend/apps/accounts/views.py:141` 和 `serializers.py:27`

### L2. 方法内重复导入 `timezone`/`Count`/`TruncDate`

**文件：** `backend/apps/admin_dashboard/views.py:394-396`

### L3. 信号处理函数定义在 `models.py` 而非 `signals.py`

**文件：** `backend/apps/accounts/models.py:22`

### L4. 管理后台手动序列化未使用 Serializer 类

**文件：** `backend/apps/admin_dashboard/views.py:518` 等多处

### L5. `UserSearchSerializer` 暴露冗余 `avatar` + `avatar_url`

**文件：** `backend/apps/friends/serializers.py:25`

### L6. `GroupMember.role` 使用原始列表而非 `TextChoices`

**文件：** `backend/apps/groups/models.py:32`

### L7. `member_count` 使用 `or` 表达式处理 0 值

**文件：** `backend/apps/groups/serializers.py:51`
**描述：** `getattr(obj, 'member_count', None) or obj.members.count()` 在 `member_count=0` 时触发额外查询。

### L8. `setUnreadCount` 每次创建新对象导致引用失效

**文件：** `frontend/src/stores/auth.js:65-68`

### L9. 管理后台 hover-only 按钮在触屏设备不可见

**文件：** `frontend/src/views/admin/AdminUsersPage.vue:23`

### L10. `JSON.stringify` 直接用于模板

**文件：** `frontend/src/views/admin/AdminLogsPage.vue:135`

### L11. DRF 异常处理器对字段级错误返回次优信息

**文件：** `backend/apps/common/exceptions.py:8`
**描述：** `ValidationError` 嵌套字典时 `.get("detail")` 返回 `None`，回退到 `str(exc)`。

### L12. import 写在方法体内（PEP 8 违规）

**文件：** `backend/apps/feed/views.py:139-140`

### L13. SiteLog 审计日志记录 `request.data` 而非过滤后字段

**文件：** `backend/apps/admin_dashboard/views.py:78`
**描述：** `detail={"changes": request.data}` 记录所有传入字段，包括未在 `allowed_fields` 中的字段，审计记录失真。

---

## 前后端 API 端点对照验证

已验证全部 74 个端点对的 URL、HTTP 方法、请求体格式、响应结构均一致。

| 后端 App | 端点数 | 前端对应 | 一致性 |
|---------|--------|---------|-------|
| accounts | 8 | `auth.js` | ✓ |
| profiles | 8 | `profiles.js` | ✓ |
| friends | 6 | `friends.js` | ✓ |
| feed | 8 | `posts.js` | ✓ |
| chat | 4 | `chat.js` | ✓ |
| notifications | 4 | `notifications.js` | ✓ |
| groups | 12 | `plugin.js` (groupApi) | ✓ |
| plugins | 13 | `plugin.js` / `admin.js` | ✓ |
| admin_dashboard | 17 | `admin.js` | ✓ |

**结论：** 无前后端路由不匹配，无 HTTP 方法冲突，无请求/响应格式不一致。
