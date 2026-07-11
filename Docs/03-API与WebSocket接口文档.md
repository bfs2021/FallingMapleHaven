# API 与 WebSocket 接口文档 — FallingMapleHaven

> 版本: v1.3（2026-07-09 按代码修正字段/取值）  
> 面向读者: 全栈开发  
> 基础路径: `/api/v1`

---

## 1. 通用规范

### 1.1 响应格式

**成功响应:**
```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

**错误响应:**
```json
{
    "code": 40001,
    "message": "用户名已存在",
    "data": null
}
```

### 1.2 错误码定义

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40003 | 登录凭证无效 / 无权限 |
| 40004 | 资源不存在（用户/帖子/评论等） |
| 40005 | 操作冲突（如重复申请） |
| 50000 | 服务器内部错误 |

> 注：实际代码中未使用 40002、40006 错误码，资源不存在统一使用 40004。

### 1.3 认证方式

- 使用 Django Session 认证（`AuthMiddlewareStack` 用于 WebSocket，Session 中间件用于 REST）
- 前端通过 `credentials: 'include'` 发送请求（axios 默认配置）
- CSRF token 通过 `GET /api/v1/auth/csrf/` 获取，axios 拦截器自动附带

---

## 2. 用户系统 API

### 2.1 注册

```
POST /api/v1/auth/register/
```

**请求体:**
```json
{
    "username": "testuser",
    "password": "Password123!",
    "nickname": "测试用户",
    "email": ""          // 选填
}
```

**密码校验规则:** 最少8位，必须包含字母、数字和至少一个特殊字符 `!@#$%^&*()_+-=[]{}|;':",./<>?~\``

**响应:** 同 `GET /api/v1/auth/me/` 返回格式，包含完整的 `UserSerializer` 字段。

### 2.2 登录

```
POST /api/v1/auth/login/
```

**请求体:**
```json
{
    "username": "testuser",
    "password": "Password123!"
}
```

**响应:** 同 `GET /api/v1/auth/me/` 返回格式，包含完整的 `UserSerializer` 字段。

### 2.3 退出登录

```
POST /api/v1/auth/logout/
```

**响应:** 标准成功响应

### 2.4 获取当前用户信息

```
GET /api/v1/auth/me/
```

**响应:**
```json
{
    "code": 0,
    "data": {
        "user_id": 1,
        "username": "testuser",
        "nickname": "测试用户",
        "avatar_url": "/media/avatars/default.png",
        "cover_url": null,
        "bio": "你好世界",
        "email": "",
        "real_name": "张三",
        "show_real_name": false,
        "visitor_public": true,
        "date_joined": "2026-01-01T00:00:00Z",
        "is_admin": false,
        "unread_count": 3
    }
}
```

### 2.5 更新个人信息

```
PATCH /api/v1/auth/me/
```

**请求体:** (所有字段可选)
```json
{
    "nickname": "新昵称",
    "bio": "新签名",
    "email": "user@example.com",
    "real_name": "张三",
    "show_real_name": true,
    "visitor_public": false
}
```

### 2.6 修改密码

```
POST /api/v1/auth/change-password/
```

**请求体:**
```json
{
    "old_password": "OldPass123!",
    "new_password": "NewPass456!"
}
```

### 2.7 上传头像

```
POST /api/v1/auth/avatar/
```

**请求体:** multipart/form-data, 字段名 `avatar`

### 2.8 上传封面

```
POST /api/v1/auth/cover/
```

**请求体:** multipart/form-data, 字段名 `cover_image`

### 2.9 获取 CSRF Token

```
GET /api/v1/auth/csrf/
```

**响应:**
```json
{
    "code": 0,
    "data": {
        "csrfToken": "xxx"
    }
}
```

---

## 3. 用户主页 API

### 3.1 获取用户主页信息

```
GET /api/v1/profiles/{username_or_id}/
```

> 路径参数支持用户名（字符串）或用户 ID（数字）。

**响应:**
```json
{
    "code": 0,
    "data": {
        "user_id": 1,
        "nickname": "测试用户",
        "avatar_url": "/media/avatars/1.jpg",
        "cover_url": "/media/covers/1.jpg",
        "bio": "签名文字",
        "real_name": "张三",
        "show_real_name": false,
        "date_joined": "2026-01-01T00:00:00Z",
        "visitor_count": 42,
        "visitor_public": true,
        "layout_config": null,
        "friend_status": "self",
        "plugins": [
            {
                "type": "quiz",
                "name": "默契问答",
                "icon": "heart",
                "route": "/profile/1/plugins/quiz",
                "data": { "friend_count": 3, "top_friends": [...] }
            }
        ]
    }
}
```

> 用户数据**扁平化**在 `data` 顶层（无 `user` 嵌套对象）。`plugins` 通过 `PluginRegistry.get_profile_plugins()` 实时返回已启用插件的数据。  
> `friend_status` 取值：`self`（本人）/ `accepted`（好友）/ `none`（无关系）/ `pending_sent`（已发送申请）/ `pending_received`（收到申请）。

### 3.2 管理员查看/编辑用户主页

```
GET/PATCH /api/v1/profiles/{username_or_id}/admin/
```

> 仅管理员可访问。路径参数支持用户名（字符串）或用户 ID（数字）。GET 返回用户 Profile 完整信息，PATCH 更新配置字段。

### 3.3 获取用户的动态列表

```
GET /api/v1/profiles/{username_or_id}/posts/
```

**参数:** `?page=1&page_size=10`

**响应:** 分页的动态列表

### 3.4 获取访客足迹

```
GET /api/v1/profiles/{username_or_id}/visitors/
```

**参数:** `?page=1&page_size=20`

**权限控制:**
- 如果目标用户的 `profile.visitor_public = false`，则非本人访问返回 403
- 本人始终可查看自己的足迹

**响应:**
```json
{
    "code": 0,
    "data": {
        "total": 42,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "user_id": 2,
                "nickname": "访客A",
                "avatar_url": "/media/avatars/2.jpg",
                "visited_at": "2026-06-22T14:30:00Z"
            }
        ]
    }
}
```

> 分页字段使用 `total` 而非 `count`，且包含 `page` 和 `page_size`。访客字段名为 `user_id`/`avatar_url`。

### 3.5 留言板

**获取留言列表:**
```
GET /api/v1/profiles/{username_or_id}/guestbook/
```

**参数:** `?page=1&page_size=20`

**响应:**
```json
{
    "code": 0,
    "data": {
        "total": 10,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 1,
                "user": {
                    "user_id": 2,
                    "nickname": "访客A",
                    "avatar_url": "/media/avatars/2.jpg"
                },
                "content": "来看看你！",
                "reply": "谢谢来访～",
                "replied_at": "2026-06-22T15:00:00Z",
                "created_at": "2026-06-22T14:30:00Z"
            }
        ]
    }
}
```

> 分页字段使用 `total/page/page_size`。作者信息嵌套在 `user` 对象中，字段名为 `avatar_url`。

**发表留言:**
```
POST /api/v1/profiles/{username_or_id}/guestbook/create/
```
```json
{
    "content": "来看看你！"
}
```

**回复留言 (主人):**
```
POST /api/v1/profiles/guestbook/{entry_id}/reply/
```
```json
{
    "reply": "谢谢来访～"
}
```

**删除留言 (主人):**
```
DELETE /api/v1/profiles/guestbook/{entry_id}/delete/
```

---

## 4. 好友系统 API

### 4.1 发送好友申请

```
POST /api/v1/friends/request/
```

**请求体:**
```json
{
    "to_user_id": 2
}
```

### 4.2 处理好友申请

```
POST /api/v1/friends/handle/
```

**请求体:**
```json
{
    "request_id": 1,          // 与 from_user_id 二选一
    "from_user_id": 2,        // 选填，通过对方用户ID处理（与 request_id 二选一）
    "action": "accept"        // accept / reject
}
```

### 4.3 解除好友

```
POST /api/v1/friends/unfriend/
```

**请求体:**
```json
{
    "friend_id": 2
}
```

### 4.4 获取好友列表

```
GET /api/v1/friends/
```

### 4.5 获取收到的申请

```
GET /api/v1/friends/requests/
```

### 4.6 搜索用户

```
GET /api/v1/friends/search/?q=关键词
```

---

## 5. 动态/广场 API

### 5.1 发布动态

```
POST /api/v1/posts/create/
```

**请求体:** multipart/form-data
```
content: "今天的夕阳好美"
visibility: "public"       // public / friends / private
topic_tag: "分享"          // 话题标签
group_id: 1                // 选填，发到指定兴趣小组
sync_to_profile: false     // 选填，是否同步到个人主页时间线，默认 false
images: [File, File, ...]  // 最多9张
files: [File, File, ...]   // 可选
```

### 5.2 获取广场动态

```
GET /api/v1/posts/
```

**参数:** `?page=1&page_size=20&topic=话题&visibility=public`

### 5.3 获取单个动态

```
GET /api/v1/posts/{post_id}/
```

### 5.4 删除动态

```
DELETE /api/v1/posts/{post_id}/delete/
```

### 5.5 点赞/取消点赞

```
POST /api/v1/posts/{post_id}/like/
```

**响应:**
```json
{
    "code": 0,
    "data": {
        "is_liked": true,
        "like_count": 10
    }
}
```

### 5.6 获取评论列表

```
GET /api/v1/posts/{post_id}/comments/
```

### 5.7 发表评论

```
POST /api/v1/posts/{post_id}/comments/create/
```

**请求体:**
```json
{
    "content": "好漂亮！",
    "parent": null      // 选填，回复某条评论时传父评论 ID
}
```

### 5.8 删除评论

```
DELETE /api/v1/posts/comments/{comment_id}/delete/
```

---

## 6. 聊天系统 API

### 6.1 获取聊天列表

```
GET /api/v1/chat/rooms/
```

**响应:**
```json
{
    "code": 0,
    "data": [
        {
            "id": 1,
            "name": "张三",
            "room_type": "private",
            "is_group": false,
            "last_message": "好的明天见",
            "last_message_at": "2026-06-22T14:30:00Z",
            "unread_count": 2,
            "other_user": {
                "user_id": 2,
                "nickname": "张三",
                "avatar_url": "/media/avatars/2.jpg"
            },
            "member_count": null
        }
    ]
}
```

> `other_user` 仅私聊房间返回非 null，包含对方的 `user_id`、`nickname`、`avatar_url`。
> `member_count` 仅群聊房间返回非 null，为群成员总数。
> `is_group` = `true` 表示群聊房间。

### 6.2 获取房间消息历史

```
GET /api/v1/chat/rooms/{room_id}/messages/
```

**参数:** `?page=1&page_size=50`

### 6.3 创建私聊房间

```
POST /api/v1/chat/rooms/create/
```

**请求体:**
```json
{
    "type": "private",
    "member_ids": [2]
}
```

**响应:** 返回 room_id，如房间已存在则返回现有房间

### 6.4 创建群聊

```
POST /api/v1/chat/rooms/create/
```

**请求体:**
```json
{
    "type": "group",
    "name": "高中同学群",
    "member_ids": [2, 3, 4]
}
```

### 6.5 发送消息 (REST 后备)

```
POST /api/v1/chat/rooms/{room_id}/messages/send/
```

**请求体:**
```json
{
    "content": "你好！",
    "msg_type": "text"
}
```

> 注: 正常情况下通过 WebSocket 发送消息，此接口作为后备/历史同步

---

## 7. WebSocket 聊天协议

### 7.1 连接

```
WebSocket URL: ws://host/ws/chat/
```

认证方式：通过 Django Channels `AuthMiddlewareStack` 复用当前登录会话，不使用 `token` 查询参数。

### 7.2 消息格式

所有 WebSocket 消息使用 JSON 格式:

**客户端 → 服务器:**
```json
{
    "type": "send_message",
    "room_id": 1,
    "content": "你好！",
    "msg_type": "text"
}
```

**服务器 → 客户端 (广播):**
```json
{
    "type": "new_message",
    "data": {
        "message_id": 100,
        "room_id": 1,
        "sender_id": 1,
        "sender_nickname": "测试用户",
        "sender_avatar": "/media/avatars/1.jpg",
        "content": "你好！",
        "msg_type": "text",
        "created_at": "2026-06-22T14:30:00Z"
    }
}
```

### 7.3 事件列表

| type (客户端→服务端) | 说明 |
|---------------------|------|
| send_message | 发送消息 |

| type (服务端→客户端) | 说明 |
|---------------------|------|
| new_message | 新消息 |

---

## 8. 兴趣小组 API

### 8.1 创建小组

```
POST /api/v1/groups/create/
```

**请求体:**
```json
{
    "name": "篮球爱好者",
    "description": "喜欢打篮球的一起约球",
    "is_public": true
}
```

### 8.2 获取小组列表

```
GET /api/v1/groups/
```

### 8.3 获取小组详情

```
GET /api/v1/groups/{group_id}/
```

### 8.4 加入小组

```
POST /api/v1/groups/{group_id}/join/
```

### 8.5 退出小组

```
POST /api/v1/groups/{group_id}/leave/
```

### 8.6 管理成员 (组长)

```
POST /api/v1/groups/{group_id}/members/{user_id}/
```

**请求体:**
```json
{
    "action": "remove"    // remove / promote_admin / demote_admin
}
```

### 8.7 更新小组信息 (组长)

```
PATCH /api/v1/groups/{group_id}/update/
```

### 8.8 获取小组动态

```
GET /api/v1/groups/{group_id}/posts/
```

### 8.9 解散小组 (组长/管理员)

```
POST /api/v1/groups/{group_id}/delete/
```

> 仅组长或管理员可操作。解散后自动删除关联聊天室、动态中的小组关联。

### 8.10 转让组长 (组长)

```
POST /api/v1/groups/{group_id}/transfer/
```

**请求体:**
```json
{
    "new_owner_id": 2
}
```

> 仅组长可操作。将小组组长转让给另一名成员。

### 8.11 查看加入申请 (组长/管理员)

```
GET /api/v1/groups/{group_id}/join-requests/
```

> 返回待处理的加入申请列表，仅组长或管理员可查看。

### 8.12 处理加入申请 (组长/管理员)

```
POST /api/v1/groups/{group_id}/join-requests/{request_id}/handle/
```

**请求体:**
```json
{
    "action": "approved"      // approved / rejected
}
```

> 仅组长或管理员可操作。`approved` 通过申请并将用户加入小组，`rejected` 拒绝申请。

---

## 9. 互动插件 API

> 通用响应格式：所有插件端点统一返回 `{"code": 0, "message": "success", "data": ...}`。

### 9.1 默契问答

> 出题只能向好友进行，目标必须是自己的好友（双向 accepted）。

**给好友出题:**
```
POST /api/v1/plugins/quiz/questions/
```
```json
// Request
{
    "target_user_id": 2,
    "question": "我最喜欢的颜色是？",
    "correct_answer": "蓝色"
}
```
```json
// Response 201
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 1,
        "from_user": {
            "user_id": 1,
            "nickname": "张三",
            "avatar_url": null
        },
        "target_user": 2,
        "question": "我最喜欢的颜色是？",
        "created_at": "2026-07-09T12:00:00Z",
        "has_answered": false
    }
}
```

**获取我收到的题目:**
```
GET /api/v1/plugins/quiz/questions/received/
```
**参数:** `?answered=true|false` 可选，默认 `false`（未回答）。`true` 返回已答题目。

```json
// Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "total": 3,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 1,
                "from_user": { "user_id": 2, "nickname": "李四", "avatar_url": null },
                "target_user": 1,
                "question": "我最喜欢的颜色是？",
                "created_at": "2026-07-09T12:00:00Z",
                "has_answered": false
            }
        ]
    }
}
```

**答题:**
```
POST /api/v1/plugins/quiz/questions/{question_id}/answer/
```
```json
// Request
{
    "answer": "红色"
}
```
```json
// Response 201
{
    "code": 0,
    "message": "success",
    "data": {
        "is_correct": false,
        "correct_answer": "蓝色",
        "match_score": 80.0
    }
}
```

**获取我与某好友的匹配度:**
```
GET /api/v1/plugins/quiz/result/{friend_user_id}/
```
```json
// Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "friend_id": 2,
        "total_questions": 5,
        "correct_count": 4,
        "match_score": 80.0,
        "updated_at": "2026-07-09T12:05:00Z"
    }
}
```

**删除题目:**
```
DELETE /api/v1/plugins/quiz/questions/{question_id}/delete/
```
```json
// Response 200
{
    "code": 0,
    "message": "success",
    "data": null
}
```

**好友排行榜:**
```
GET /api/v1/plugins/quiz/leaderboard/
```
返回当前用户与所有好友的匹配度排名，按匹配度降序、答题数降序排列。

```json
// Response 200
{
    "code": 0,
    "data": {
        "rankings": [
            { "rank": 1, "friend_id": 2, "nickname": "李四", "avatar_url": null, "match_score": 92.0, "total_questions": 13, "correct_count": 11 },
            { "rank": 2, "friend_id": 3, "nickname": "王五", "avatar_url": null, "match_score": 85.0, "total_questions": 8, "correct_count": 6 }
        ],
        "avg_match_rate": 75.0,
        "total_friends": 6
    }
}
```

### 9.2 匿名提问箱

**发起提问（向他人匿名提问）:**
```
POST /api/v1/plugins/question-box/
```
```json
// Request
{
    "recipient_id": 1,
    "content": "你最近在看什么书？",
    "is_public": true
}
```
`is_public` 选填，默认 `true`。

```json
// Response 201
{
    "code": 0,
    "message": "success",
    "data": {
        "id": 1
    }
}
```

**获取我的提问箱（他人向我提问）:**
```
GET /api/v1/plugins/question-box/inbox/
```
**参数:** `?answered=true|false` 可选，筛选已回答/未回答的提问。

```json
// Response 200
{
    "code": 0,
    "message": "success",
    "data": {
        "total": 2,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 1,
                "content": "你最近在看什么书？",
                "answer": null,
                "is_answered": false,
                "is_public": true,
                "created_at": "2026-07-09T12:00:00Z",
                "answered_at": null
            }
        ]
    }
}
```
> 提问者信息不暴露 —— `sender` 字段不返回，实现匿名。

**回答提问:**
```
POST /api/v1/plugins/question-box/{question_id}/answer/
```
```json
// Request
{
    "answer": "最近在看《百年孤独》"
}
```
```json
// Response 200
{
    "code": 0,
    "message": "success"
}
```
> 仅收件人（recipient）可以回答。

**删除提问:**
```
DELETE /api/v1/plugins/question-box/{question_id}/delete/
```
```json
// Response 200
{
    "code": 0,
    "message": "success"
}
```
> 仅收件人（recipient）可以删除自己收到的提问。

### 9.3 插件摘要

返回所有已注册插件的全局摘要，用于 `/plugins` 独立页面展示。

```
GET /api/v1/plugins/summary/
```

```json
{
    "code": 0,
    "data": [
        {
            "type": "quiz",
            "name": "默契问答",
            "icon": "help-circle",
            "description": "和朋友互相出题测试默契度",
            "data": {
                "avg_match_rate": 75.5,
                "best_friend_id": 2,
                "best_friend_name": "李四",
                "best_match_rate": 92.0,
                "total_friends_answered": 6
            },
            "is_active": true,
            "route": "/plugins"
        },
        {
            "type": "question_box",
            "name": "匿名提问箱",
            "icon": "message-question",
            "description": "任何人都可以匿名向你提问",
            "data": {
                "total_questions": 15,
                "unanswered_count": 3
            },
            "is_active": true,
            "route": "/plugins"
        }
    ]
}
```

### 9.4 个人主页插件卡片

返回某用户主页的插件卡片数据（含访客视角动态数据，如 A 看 B 主页时显示 A 与 B 的匹配度）。

```
GET /api/v1/plugins/profile-cards/{username_or_id}/
```

```json
{
    "code": 0,
    "data": [
        {
            "type": "quiz",
            "name": "默契问答",
            "icon": "help-circle",
            "description": "和朋友互相出题测试默契度",
            "data": {
                "match_score": 87.0,
                "total_questions": 13,
                "correct_count": 11
            },
            "route": "/profile/123/plugins/quiz"
        },
        {
            "type": "guestbook",
            "name": "留言板",
            "icon": "message-square",
            "description": "给我留言",
            "data": { "total_messages": 12 },
            "route": "/profile/123/guestbook"
        }
    ]
}
```

---

## 10. 通知系统 API

### 10.1 获取通知列表

```
GET /api/v1/notifications/
```

**参数:** `?page=1&page_size=20&unread_only=true`

当前通知类型与代码 `Notification.Type` 保持一致：`system`、`friend_request`、`friend_accepted`、`comment`、`like`、`reply`、`quiz_invite`、`anonymous_question`、`group_join_request`、`group_request_approved`、`group_request_rejected`、`group_member_joined`、`group_new_post`。

### 10.2 标记已读

```
POST /api/v1/notifications/{id}/read/
```

### 10.3 全部标记已读

```
POST /api/v1/notifications/read-all/
```

### 10.4 获取未读通知数

```
GET /api/v1/notifications/unread-count/
```

---

## 11. 管理后台 API

### 11.1 用户管理

```
GET /api/v1/admin/users/                      # 用户列表（支持 ?search=关键词）
PATCH /api/v1/admin/users/{user_id}/           # 修改用户状态（is_active / is_staff）
```

### 11.2 内容管理

```
GET /api/v1/admin/posts/                      # 动态列表(含匿名者)
DELETE /api/v1/admin/posts/{post_id}/          # 删除动态
GET /api/v1/admin/comments/                   # 评论列表
DELETE /api/v1/admin/comments/{comment_id}/    # 删除评论
GET /api/v1/admin/anonymous-questions/         # 匿名提问追溯
GET /api/v1/admin/quiz/questions/              # 问答管理（所有题目+作答状态）
```

> 匿名提问追溯接口返回数据包含 `real_sender` 字段，前端入口为 `/admin/anonymous-questions`。
> 问答管理接口返回数据包含题目、出题人、目标人、已答状态、是否正确等信息，前端入口为 `/admin/quiz`。

**群组管理:**
```
GET /api/v1/admin/groups/                        # 小组列表（支持 ?search=关键词，分页返回）
DELETE /api/v1/admin/groups/{group_id}/           # 删除小组（同时清理关联聊天室和动态）
GET /api/v1/admin/groups/{group_id}/posts/        # 查看小组内所有动态
```

> 群组管理接口返回数据包含 `id`、`name`、`description`、`cover_url`、`is_public`、`creator_name`、`member_count`、`created_at`。
> 群组动态接口返回 `id`、`author_name`、`content`、`created_at`。

### 11.3 站点设置

```
GET /api/v1/admin/settings/                   # 获取所有设置
PATCH /api/v1/admin/settings/                  # 更新设置
```

**可用配置键:**
| 键 | 类型 | 说明 |
|------|------|------|
| `allow_register` | boolean | 是否允许新用户注册 |
| `site_notice` | string | 站点公告内容 |
| `site_name` | string | 网站名称，默认 `FallingMapleHaven` |
| `site_logo` | string | Logo URL 路径 |
| `site_favicon` | string | Favicon URL 路径 |
| `max_file_size` | int | 最大文件上传大小(MB) |
| `allowed_extensions` | string | 允许上传的文件扩展名，逗号分隔 |

> `PATCH` 请求体格式: `{ "settings": { "allow_register": false, "site_notice": "维护中" } }`

### 11.4 插件管理

```
GET /api/v1/admin/plugins/                    # 插件列表
PATCH /api/v1/admin/plugins/{plugin_id}/       # 启停插件
```

### 11.5 统计数据

```
GET /api/v1/admin/stats/                      # 概览数据
```

返回:
```json
{
    "total_users": 10,
    "total_posts": 100,
    "total_comments": 50,
    "total_messages": 200,
    "active_users_today": 5
}
```

### 11.6 趋势数据

```
GET /api/v1/admin/trends/?days=7              # 注册/发帖/消息/评论/足迹/好友趋势
```

### 11.7 操作日志

```
GET /api/v1/admin/logs/                       # 日志列表（支持 ?action=&user_id=&page=）
GET /api/v1/admin/logs/actions/               # 所有日志操作类型列表
```

### 11.8 插件配置

```
GET /api/v1/admin/plugins/configs/            # 插件注册的管理侧边栏配置
```

---

## 12. 文件上传通用接口

> 当前版本中不包含独立的 `upload` 应用。文件上传通过各功能模块的专用接口实现：
> - 头像上传: `POST /api/v1/auth/avatar/`
> - 封面上传: `POST /api/v1/auth/cover/`
> - 动态图片: `POST /api/v1/posts/create/` (multipart, 字段 `images`)
> - 动态文件: `POST /api/v1/posts/create/` (multipart, 字段 `files`)
