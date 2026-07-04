# 枫落港 (FallingMapleHaven) BUG 审计报告

> 审计日期：2026-07-03
> 审计范围：全部后端 Python 代码 + 前端 Vue/JS 代码 + 配置文件
> 交叉复核确认：已清除 5 个误报，新增 11 个遗漏 Bug
> **总计：56 个 Bug**（Critical 5 / High 19 / Medium 19 / Low 13）

---

## 摘要

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| 🔴 Critical | 5 | 导致功能完全不可用或严重数据安全问题的 Bug |
| 🟠 High | 19 | 导致功能异常、性能严重退化或中等安全隐患的 Bug |
| 🟡 Medium | 19 | 功能不完善、UI/UX 缺陷或潜在风险 |
| 🔵 Low | 13 | 代码风格、轻微优化建议 |

---

## 🔴 Critical 级别

### C1. 文件上传使用普通对象而非 FormData

**文件：** `frontend/src/api/auth.js:10-15`
**描述：** `uploadAvatar` 和 `uploadCover` 将文件作为普通 JS 对象 `{ avatar: file }` 传递，同时显式设置 `Content-Type: multipart/form-data`。Axios 默认将普通对象序列化为 JSON，导致文件被字符串化为 `{}`。
**影响：** 头像和封面图上传完全不可用。
**代码：**
```js
uploadAvatar: (file) => client.post('/auth/avatar/', { avatar: file }, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
// 应改为:
// const fd = new FormData(); fd.append('avatar', file); client.post('/auth/avatar/', fd)
```

### C2. 3 张图片布局中第一张图重复显示，第三张图缺失

**文件：** `frontend/src/components/PostImageGrid.vue:20-21`
**描述：** 3 图网格布局中，大格已显示 `images[0]`，循环 `v-for="(img, i) in [1,2]"` 中 `i=0,1` 又读取 `images[0]` 和 `images[1]`，导致 `images[0]` 出现两次、`images[2]` 永远不显示。
**影响：** 发布 3 张图片时，第三张图片完全看不到。
**代码：**
```html
<div v-for="(img, i) in [1,2]" :key="i">
  <img :src="images[i]" ... />  <!-- 应改为 images[i + 1] -->
</div>
```

### C3. 滚动加载时页码双重递增导致隔页跳过

**文件：** `frontend/src/views/HomePage.vue:51` + `frontend/src/stores/feed.js:22`
**描述：** 滚动处理器手动执行 `feedStore.currentPage++`（line 51），而 `fetchPosts` 内部也执行 `this.currentPage += 1`（feed.js:22）。每次滚动加载都跳过一页数据。
**影响：** 无限滚动加载会跳过一半数据，用户无法看到完整动态流。
**代码：**
```js
// HomePage.vue:51
feedStore.currentPage++   // 手动递增一次
feedStore.fetchPosts(tagParams.value)

// feed.js:22 — fetchPosts 内部又递增一次
this.currentPage += 1    // 总计递增两次
```

### C4. `int()` 转换无异常处理导致 500 错误

**文件：** 至少 10 处
**影响：** 若调用方传入 `?page=abc` 或 `?days=abc`，`int()` 抛出 `ValueError`，返回 500 Internal Server Error。
**受影响位置（共 11 处）：**
- `backend/apps/feed/views.py:57` — `page`
- `backend/apps/profiles/views.py:104` — `page`
- `backend/apps/profiles/views.py:156` — `page`
- `backend/apps/profiles/views.py:189` — `page`
- `backend/apps/chat/views.py:48` — `page`
- `backend/apps/notifications/views.py:20` — `page`
- `backend/apps/groups/views.py:242` — `page`
- `backend/apps/admin_dashboard/views.py:328` — `page`
- `backend/apps/admin_dashboard/views.py:369` — `days`（趋势图参数）
- `backend/apps/admin_dashboard/views.py:510` — `page`
- `backend/apps/admin_dashboard/views.py:545` — `page`

### C5. WebSocket ChatConsumer — 房间订阅仅在连接时设置，新房间不接收消息

**文件：** `backend/apps/chat/consumers.py:19-24`
**描述：** Channel Layer group 订阅仅在 WebSocket `connect()` 时执行。如果用户在 WebSocket 保持打开期间创建了新聊天室或被加入新聊天室，该用户**不会收到新房间的实时消息**，直到断开重连。
**影响：** 实时聊天功能对于新创建的聊天室完全失效。这是 WebSocket 订阅管理的根本性缺陷。
**代码：**
```python
async def connect(self):
    await self.accept()
    room_ids = await self.get_user_room_ids()   # 仅在连接时获取房间列表
    for room_id in room_ids:
        group_name = f"chat_{room_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
    # 没有后续监听新房间加入的机制
```

---

## 🟠 High 级别

### H1. 普通 staff 可提升任意用户为 staff（权限越级）

**文件：** `backend/apps/admin_dashboard/views.py:69`
**描述：** `AdminUserUpdateView` 只检查 `is_staff` 权限，未限制 `is_staff` 字段只能由 superuser 修改。普通 staff 可互相授予 staff 权限。

### H2. 管理后台列表视图无分页

**文件：** `backend/apps/admin_dashboard/views.py:52` 及多处
**影响：** 用户/帖子/评论数量上万时，单次查询返回全部数据，可能导致 OOM 或响应超时。

### H3. 聊天室列表序列化器导致 5+ N+1 查询

**文件：** `backend/apps/chat/serializers.py:21`
**描述：** 每个 `get_name`、`get_last_message`、`get_unread_count` 等 SerilizerMethodField 都发起独立 SQL。20 个聊天室产生 100+ 条查询。

### H4. 点赞/评论数量使用 `.count()` 忽略预取缓存

**文件：** `backend/apps/feed/serializers.py:58`
**描述：** `.count()` 始终发起 COUNT 查询，即使数据已被 `prefetch_related` 加载。应使用 `len(obj.comments.all())` 或 `annotate(Count(...))`。

**同类问题：** `frontend 评论区无分页`（README 中已标注）

### H5. 访客足迹无去重/限流

**文件：** `backend/apps/profiles/views.py:74`
**描述：** 每次刷新个人主页都创建一个新的 `VisitRecord`，频繁刷新产生大量垃圾数据。

### H6. 匿名提问箱在数据库层面存储提问者身份

**文件：** `backend/apps/plugins/questions/models.py:9`
**描述：** `AnonymousQuestion.sender` 以明文 FK 存储发送者 ID，任何有 DB 访问权限者都能查询到提问者身份。

### H7. 未使用的变量 `answered_ids`

**文件：** `backend/apps/plugins/quizzes/views.py:132`
**描述：** `answered_ids` QuerySet 被计算但从未使用，表明存在缺失的逻辑步骤。

### H8. 任何已认证用户可向任意小组发布动态（未校验成员身份）

**文件：** `backend/apps/feed/views.py:121`
**描述：** 发布动态时若传入 `group_id`，不做任何成员身份校验。非小组成员可向私密小组发帖。
**代码：**
```python
group_id = serializer.validated_data.get("group_id")
# 缺少: if group_id and not GroupMember.objects.filter(group_id=group_id, user=request.user).exists():
```

### H9. `needsTruncation` 不是计算属性

**文件：** `frontend/src/components/PostCard.vue:33`
**描述：** 使用 `const` 常量而非 `computed`，当 `post.content` 变化时不会重新计算。

### H10. 直接修改组件 Prop：`props.post.comment_count -= 1`

**文件：** `frontend/src/components/PostCard.vue:60`
**描述：** 在子组件中直接修改 prop 内部属性，违反 Vue 单向数据流原则。

### H11. WebSocket 消息未做来源验证

**文件：** `frontend/src/stores/chat.js:67`
**描述：** `JSON.parse(event.data)` 后直接信任所有字段，未验证 `event.origin` 或检查连接来源。

### H12. 相对时间函数无输入验证

**文件：** `frontend/src/utils/time.js:3`
**描述：** 当 `dateString` 为 `null`/`undefined`/空字符串时，`new Date().getTime()` 返回 `NaN`，所有时间戳显示为 "NaN分钟前"。

### H13. 管理后台插件图标为非受支持的表情符号

**文件：** `frontend/src/plugins/questions/index.js:10`
**描述：** `adminSidebar.icon` 设置为 `'🕵️'`，但 `Icon` 组件中不存在该图标映射，侧边栏图标不显示。

### H14. Axios 拦截器绕过 Pinia store action 直接置空 user

**文件：** `frontend/src/api/client.js:56`
**描述：** 401 响应处理中直接 `authStore.user = null`，绕过 `authStore.logout()` action，无法触发 WebSocket 断开等副作用。

### H15. `UserPostListView` — 完全缺失 select_related / prefetch_related（N+1 黑洞）

**文件：** `backend/apps/profiles/views.py:131,160`
**描述：** 无 `select_related("author")`、无 `prefetch_related("images", "comments", "likes")`。每个 Post 的 `author`、`images`、`comments`、`likes` 都触发独立查询。每页 20 条动态 → ~80+ 额外 SQL。
```python
posts = Post.objects.filter(author=user).filter(...).select_related("group")
# 缺少: .select_related("author").prefetch_related("images", "comments", "likes")
```

### H16. `GroupPostsView` — 无 select_related / prefetch_related

**文件：** `backend/apps/groups/views.py:240-247`
**描述：** 小组动态列表同样缺少预取，同 H15 N+1 问题。

### H17. `CommentListView` — 评论作者 N+1 查询

**文件：** `backend/apps/feed/views.py:274-276`
**描述：** `CommentSerializer.get_user()` 访问 `author.nickname`、`author.avatar`，无 `select_related("author")`。50 条评论 → 50+ 额外 SQL。

### H18. `RoomMessagesView` — 消息发送者 N+1 查询

**文件：** `backend/apps/chat/views.py:47-53`
**描述：** `MessageSerializer` 访问 `sender.id`、`sender.nickname`、`sender.avatar`，无 `select_related("sender")`。

### H19. `GuestbookListView` — 留言作者 N+1 查询

**文件：** `backend/apps/profiles/views.py:187-196`
**描述：** `GuestbookEntrySerializer.get_user()` 访问 `obj.author`，无 `select_related("author")`。

---

## 🟡 Medium 级别

### M1. 应使用 ImageField 而非 FileField

**文件：** `backend/apps/accounts/models.py:10`，`backend/apps/feed/models.py:46`
**影响：** 头像、封面、PostImage 使用 `FileField`，缺失图片格式验证和 `width`/`height` 属性。

### M2. PIL `Image.verify()` 验证不充分

**文件：** `backend/apps/accounts/views.py:177`
**描述：** `verify()` 只检查文件头，可被"多语种"文件绕过。且无文件大小限制。

### M3. 批量通知创建使用逐条 `create()` 而非 `bulk_create`

**文件：** `backend/apps/feed/views.py:148`、`groups/views.py:136`、`groups/views.py:380`
**影响：** 大群组中会产生大量 SQL INSERT。

### M4. ChatRoom 私聊查重未校验成员数量

**文件：** `backend/apps/chat/views.py:93`
**描述：** 双 filter 模式可能返回包含超过 2 人的错误聊天室。

### M5. WebSocket 消息静默截断 2000 字符

**文件：** `backend/apps/chat/consumers.py:42`
**描述：** 超过 2000 字符的消息被静默截断，发送方无任何通知。

### M6. 匿名提问未校验接收方是否开启该插件

**文件：** `backend/apps/plugins/questions/views.py:28`
**描述：** 全局插件可能已启用，但特定用户可能不希望接收匿名提问，无 opt-out 机制。

### M7. 通知内容无内容过滤

**文件：** `backend/apps/plugins/questions/views.py:35`
**描述：** 匿名提问的前 100 字符直接存入通知，无 HTML 剥离或内容审查。

### M8. 默认密钥不安全

**文件：** `backend/config/settings/base.py:11`
**描述：** `SECRET_KEY` 硬编码默认值 `"django-insecure-change-me-in-production"`。

### M9. 点赞接口存在 TOCTOU 竞态条件

**文件：** `backend/apps/feed/views.py:247`
**描述：** 两次并发请求可能同时通过 `get_or_create` 创建 Like，然后其中一个被 `delete`，导致状态不一致。

### M10. `type` 字段遮蔽 Python 内置函数

**文件：** `backend/apps/chat/models.py:12`
**描述：** 字段名 `type` 遮蔽了 Python 内置的 `type()` 函数。

### M11. 路由守卫未在所有路由上初始化 Session

**文件：** `frontend/src/router/index.js:102`
**描述：** 部分公共路由（`/`、`/profile/:userId`、`/groups`）不触发 `ensureSession`，可能导致已登录用户短暂看到访客视图。

### M12. 登录/注册页存在开放重定向漏洞

**文件：** `frontend/src/views/LoginPage.vue:28`、`RegisterPage.vue:58`
**描述：** `router.push(route.query.next)` 直接将 URL 查询参数作为跳转目标。

### M13. 插件视图响应格式不一致（未使用 `api_response` 辅助函数）

**文件：** `backend/apps/plugins/questions/views.py:42-45`，`backend/apps/plugins/quizzes/views.py:43-46`
**描述：** 插件 API 直接返回 `Response({"code": 0/1, "message": "..."})`，而非使用统一的 `api_response()` 函数，响应结构与系统其他部分不一致。

### M14. `PostDetailView` — 未校验小组动态的可见性权限

**文件：** `backend/apps/feed/views.py:161-204`
**描述：** `PostDetailView` 检查 `visibility` 属性（PUBLIC/FRIENDS/PRIVATE），但当动态属于私密小组时，未校验当前用户是否为小组成员。

### M15. `FriendButton` 的 `userId` prop 类型声明与使用不一致

**文件：** `frontend/src/components/FriendButton.vue:6` + `frontend/src/views/ProfilePage.vue:183`
**描述：** `FriendButton` 声明 `userId: { type: Number }`，但 `ProfilePage` 可能传入字符串类型的用户名（路由参数未强转数字），触发 Vue prop 类型警告。

### M16. `ensureSession` 的模块级 Promise 在 `fetchMe` 永不完成时可导致永久挂起

**文件：** `frontend/src/stores/auth.js:37`
**描述：** `sessionInitPromise` 的 `.finally()` 重置仅在 Promise 完成/拒绝后执行。如果 `fetchMe` 因网络问题永远处于 pending 状态，所有后续 `ensureSession()` 调用将永久挂起。

### M17. 通知轮询每次请求全量列表（丢失滚动位置）

**文件：** `frontend/src/views/NotificationsPage.vue:44`
**描述：** 每隔 30 秒同时拉取全量通知列表和未读数，会刷新列表丢失用户滚动位置。

### M18. `fetchNotifications` 的 `res.data` 回退逻辑不安全

**文件：** `frontend/src/views/NotificationsPage.vue:63`
**描述：** `const results = res.data?.results || res.data || []`——若 `res.data` 是不含 `results` 的对象（如 `{ unread_count: 5 }`），会将对象属性展开到数组。

### M19. 管理后台插件列表页引用不存在的 `description` 字段

**文件：** `frontend/src/views/admin/AdminPluginsPage.vue:77` + `backend/apps/plugins/models.py`
**描述：** `AdminPluginsPage` 模板中渲染 `{{ plugin.description || '暂无描述' }}`，但 `Plugin` 模型没有 `description` 字段——只有 `name`、`type`、`is_active`、`config`、`created_at`。结果所有插件始终显示"暂无描述"。

---

## 🔵 Low 级别

### L1. 硬编码特殊字符集重复定义

**文件：** `backend/apps/accounts/views.py:141` 和 `serializers.py:27`

### L2. 方法内重复导入 `timezone` / `Count` / `TruncDate`

**文件：** `backend/apps/admin_dashboard/views.py:357, 363`

### L3. 信号处理函数定义在 `models.py` 而非 `signals.py`

**文件：** `backend/apps/accounts/models.py:22`

### L4. 管理后台手动序列化而非使用 Serializer 类

**文件：** `backend/apps/admin_dashboard/views.py:518`

### L5. `UserSearchSerializer` 暴露冗余字段 `avatar` 和 `avatar_url`

**文件：** `backend/apps/friends/serializers.py:25`

### L6. `GroupMember.role` 使用原始列表而非 `TextChoices`

**文件：** `backend/apps/groups/models.py:32`

### L7. `member_count` 使用 `or` 表达式处理 0 值

**文件：** `backend/apps/groups/serializers.py:51`

### L8. `setUnreadCount` 每次创建新对象导致引用失效

**文件：** `frontend/src/stores/auth.js:65`

### L9. 5+ 图片布局无最大高度约束

**文件：** `frontend/src/components/PostImageGrid.vue:29`
**描述：** `grid-cols-3` 布局中 6 张图会创建很高的纵向块。

### L10. 管理后台 hover-only 按钮在触屏设备不可见

**文件：** `frontend/src/views/admin/AdminUsersPage.vue:23`

### L11. `JSON.stringify` 直接用于模板，每次重渲染执行

**文件：** `frontend/src/views/admin/AdminLogsPage.vue:135`

### L12. 评论区 `deletingIds` 每次替换对象引用导致不必要的响应式检查

**文件：** `frontend/src/components/CommentSection.vue:46`

### L13. DRF 异常处理器对字段级错误返回次优错误信息

**文件：** `backend/apps/common/exceptions.py:8`
**描述：** `ValidationError` 时 `response.data` 可能是嵌套字典，`.get("detail")` 返回 `None`，回退到 `str(exc)`。不会崩溃但错误信息不友好。

---

## 数据流分析

### `api_response` 统一响应格式

所有后端视图使用 `api_response()` 辅助函数（`backend/apps/common/utils.py`）:
```python
def api_response(data=None, code=0, message="success", status=200):
    return Response({"code": code, "message": message, "data": data}, status=status)
```

这意味着：
- 每个响应体都包含 `code`、`message`、`data` 三个顶层字段
- `data` 字段内才是实际的负载（分页结果、用户信息等）

### 前端响应链

```js
// Axios response 对象
response = { data: { code: 0, message: "success", data: { results: [...], ... } }, status: 200, ... }

// client.js:51 拦截器解包
(response) => response.data
// 此时 res = { code: 0, message: "success", data: { results: [...], ... } }

// 各 Store 中的 res.data
res.data          // → { results: [...], ... }     ✓ 正确访问到 data 字段内的负载
res.data.results  // → [...]                        ✓ 正确访问到分页结果
```

**结论：** `client.js` 的拦截器解包设计虽然令人困惑，但在 `api_response` 的 `data` 嵌套结构下**功能上是正确的**。这不是 Bug。但易读性差，后续维护者容易误解。

---
