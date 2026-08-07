# 枫落港 (FallingMapleHaven)

## 简介

枫落港是一个面向高中同学及社交圈朋友的轻量社交平台。在这里，每个人都能拥有自己专属的个人主页，记录和分享生活日常；可以与好友实时聊天、在广场上互动；还可以通过默契问答、匿名提问箱等趣味插件增进彼此的了解。

项目的名称"枫落港"取自秋叶飘落、归港停泊之意，希望为朋友们提供一个温暖、私密的线上空间。

---

## 功能详情

### 用户系统

支持用户名注册与登录，注册后自动创建个人主页。用户可以修改昵称、头像、封面背景图、个人签名、真实姓名等资料。密码修改需要验证旧密码，保障账户安全。

### 个人主页

每位用户都有一个独立的个人主页，包含资料卡区域（头像、昵称、签名、封面图）、动态时间线（按时间倒序展示该用户发布的所有动态）、插件入口区（展示已启用的互动工具卡片）和留言板（访客可留言，主人可回复或删除）。访问他人主页时会留下访客足迹，用户可以选择是否公开自己的足迹列表。

### 社交广场

广场聚合了所有公开和好友可见的动态，按时间倒序排列，支持分页加载。用户可以发布图文动态（最多 9 张图片 + 文件附件），并控制可见范围为公开、仅好友或仅自己。动态支持话题标签（如闲聊、分享、求助等），可按话题筛选浏览。用户可以对动态点赞（可取消）和发表评论，评论支持嵌套回复。

### 好友系统

用户可以通过搜索找到其他用户并发送好友申请，对方可以同意或拒绝。好友关系采用双向确认机制，解除好友则为单向操作。好友列表按昵称排序展示。

### 即时聊天

支持私聊和群聊两种模式。私聊无需好友关系即可发起，群聊需要创建时选择成员。所有消息通过 WebSocket 实时推送，延迟低。消息记录持久化存储，可回溯历史。聊天列表按最后消息时间排序，并显示未读消息数。

### 互动插件

采用可插拔架构，当前提供四款插件：

- **默契问答**：主页主人创建测试（发布后固定 10 道单选题），登录用户或未登录访客均可参与答题，答完进入答卷榜查看排名。
- **匿名提问箱**：任意用户可向目标用户匿名提问，目标用户可以选择公开回答或不回答。
- **关系匹配**：完成 40 题基础测试生成个人画像，通过分享链接或短码邀请另一位参与者，系统自动生成两人关系类型与八维对比报告。
- **留言板**：访客可在主页留言，主人可回复或删除。

### 通知系统

系统支持多种通知类型：好友请求、好友请求接受、动态点赞、动态评论、评论回复、插件动态（默契问答/关系匹配）、匿名提问以及小组相关通知。所有通知按时间倒序排列，区分已读/未读状态，导航栏显示未读总数角标。

### 兴趣小组

用户可以创建兴趣小组，设置名称、简介、封面图以及是否公开可见。公开小组可直接加入，私密小组需申请。组长可以修改小组信息、移除成员、转让组长或解散小组。小组拥有独立的动态时间线（仅组内成员可见）和聊天室。

### 访客浏览模式

未登录用户可以浏览公开内容（广场动态、个人主页公开资料、公开小组列表等），参与交互（发布动态、点赞评论、发送消息等）则需要登录。这降低了新用户的了解门槛，同时保护了私密数据。

---

## 技术栈

### 前端

- **Vue 3** + Composition API：组件化开发，逻辑复用灵活
- **Pinia**：全局状态管理（auth、feed、chat、friend 四个 Store）
- **Vue Router 4**：前端路由，支持导航守卫
- **Tailwind CSS 3**：原子化样式，秋叶主题色板扩展
- **lucide-vue-next**：SVG 图标库
- **Vite 5**：开发服务器热更新 + 生产构建
- **axios**：HTTP 客户端，自动处理 CSRF Token 和 Session 凭证

### 后端

- **Django 5**：核心业务逻辑与 ORM
- **Django REST Framework 3.15+**：RESTful API
- **Django Channels 4**：WebSocket 实时通信
- **daphne**：ASGI 服务器
- **PostgreSQL 16**：关系数据库
- **Redis 7**：Channel Layer 与消息代理
- **django-cors-headers**：跨域支持

---

## 快速开始

### 准备工作

确保你的开发环境已安装：

- Python 3.10 或更高版本
- Node.js 18 或更高版本
- Docker 与 Docker Compose（用于运行 PostgreSQL 和 Redis）

### 第一步：启动基础设施

项目依赖 PostgreSQL 和 Redis，通过 Docker Compose 一键启动：

```bash
cd docker
docker compose up -d
```

该命令会在后台启动 PostgreSQL 16（监听端口 5432）和 Redis 7（监听端口 6379），数据持久化存储在 Docker 卷中。

### 第二步：配置并启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux / Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 执行数据库迁移
python manage.py migrate

# 启动开发服务器
python manage.py runserver
```

后端启动后访问 `http://localhost:8000`，API 基础路径为 `/api/v1`。

### 第三步：配置并启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:5173`。Vite 已配置开发代理，`/api`、`/ws`、`/media` 前缀的请求会自动转发到 Django 后端，无需额外配置跨域。

### 验证

打开浏览器访问 `http://localhost:5173`，可以看到枫落港的首页。注册一个新账号，即可开始体验所有功能。

---

## 项目结构

```
枫落港/ (FallingMapleHaven)
│
├── backend/                               # Django 后端项目
│   ├── config/                            # 项目配置
│   │   ├── settings/
│   │   │   ├── base.py                    # 基础配置（数据库、中间件、认证等）
│   │   │   ├── dev.py                     # 开发环境配置
│   │   │   └── prod.py                    # 生产环境配置
│   │   ├── urls.py                        # 根路由注册
│   │   ├── asgi.py                        # Channels ASGI 入口
│   │   └── wsgi.py                        # WSGI 入口
│   │
│   ├── apps/                              # Django 应用
│   │   ├── accounts/                      # 用户系统——注册、登录、资料管理
│   │   ├── profiles/                      # 个人主页——Profile、访客足迹、留言板
│   │   ├── friends/                       # 好友系统——申请、确认、解除
│   │   ├── feed/                          # 动态广场——Post、Comment、Like
│   │   ├── chat/                          # 聊天系统——ChatRoom、Message、WebSocket Consumer
│   │   ├── groups/                        # 兴趣小组——创建、加入、管理
│   │   ├── plugins/                       # 插件系统——BasePlugin、默契问答、匿名提问箱、关系匹配
│   │   ├── notifications/                 # 通知系统——多类型通知
│   │   ├── admin_dashboard/
│   │   └── common/                        # 公共工具——异常处理
│   │
│   ├── media/                             # 用户上传的头像、封面、动态图片等
│   ├── static/                            # 收集的静态文件
│   ├── manage.py                          # Django 管理脚本
│   └── requirements.txt                   # Python 依赖清单
│
├── frontend/                              # Vue 3 前端项目
│   └── src/
│       ├── api/                           # API 请求层
│       │   ├── client.js                  # axios 实例、CSRF 拦截、统一错误处理
│       │   ├── auth.js                    # 用户认证相关 API
│       │   ├── posts.js                   # 动态相关 API
│       │   ├── profiles.js                # 个人主页相关 API
│       │   ├── chat.js                    # 聊天相关 API
│       │   ├── friends.js                 # 好友相关 API
│       │   ├── notifications.js           # 通知相关 API
│       │   ├── plugin.js                  # 插件相关 API
│       │   └── admin.js
│       │
│       ├── stores/                        # Pinia 状态管理
│       │   ├── auth.js                    # 用户登录态与信息
│       │   ├── feed.js                    # 广场动态列表与话题筛选
│       │   ├── chat.js                    # 聊天列表、WebSocket 连接、消息缓存
│       │   └── friend.js                  # 好友列表与申请管理
│       │
│       ├── router/                        # 路由配置
│       │   ├── index.js                   # 主路由表 + 导航守卫
│       │   └── admin.js
│       │
│       ├── views/                         # 页面组件（共 16 个）
│       │   ├── HomePage.vue               # 首页——广场动态流
│       │   ├── LoginPage.vue              # 登录页
│       │   ├── RegisterPage.vue           # 注册页
│       │   ├── ProfilePage.vue            # 个人主页
│       │   ├── SettingsPage.vue           # 个人设置
│       │   ├── ChatListPage.vue           # 聊天列表
│       │   ├── ChatRoomPage.vue           # 聊天室
│       │   ├── FriendsPage.vue            # 好友管理
│       │   ├── NotificationsPage.vue      # 通知列表
│       │   ├── GroupListPage.vue          # 小组列表
│       │   ├── GroupDetailPage.vue        # 小组详情
│       │   ├── QuizPage.vue               # 默契问答
│       │   ├── QuestionBoxPage.vue        # 匿名提问箱
│       │   ├── GuestbookPage.vue          # 留言板
│       │   ├── NotFoundPage.vue           # 404 页面
│       │   └── admin/
│       │
│       ├── components/                    # 公共组件（共 19 个）
│       │   ├── NavBar.vue                 # 桌面端顶部导航
│       │   ├── MobileTabBar.vue           # 手机端底部导航
│       │   ├── PostCard.vue               # 动态卡片
│       │   ├── PostCreateCard.vue         # 动态发布表单
│       │   ├── AvatarImage.vue            # 头像显示
│       │   ├── FriendButton.vue           # 好友操作按钮
│       │   ├── PluginEntryGrid.vue        # 插件入口卡片区
│       │   ├── CommentSection.vue         # 评论区
│       │   ├── PostActions.vue            # 点赞/评论按钮
│       │   ├── PostImageGrid.vue          # 图片九宫格
│       │   ├── MessageBubble.vue          # 聊天消息气泡
│       │   ├── GuestbookBoard.vue         # 留言板组件
│       │   ├── ConfirmDialog.vue          # 全局确认弹窗
│       │   ├── ToastContainer.vue         # 全局 Toast 提示
│       │   ├── TabBar.vue                 # 标签页切换栏
│       │   ├── ToggleSwitch.vue           # 开关组件
│       │   ├── BottomSheet.vue            # 底部弹出面板
│       │   ├── Icon.vue                   # 图标统一封装
│       │   └── SelectField.vue            # 下拉选择框
│       │
│       ├── plugins/                       # 前端插件注册
│       │   ├── registry.js                # PluginRegistry 类
│       │   ├── quiz/index.js              # 默契问答插件注册
│       │   └── questions/index.js         # 匿名提问箱插件注册
│       │
│       ├── composables/                   # 组合式函数
│       │   ├── useToast.js                # Toast 提示
│       │   └── useConfirm.js              # 确认对话框
│       │
│       ├── utils/                         # 工具函数
│       │   └── time.js                    # 时间格式化
│       │
│       └── assets/                        # 全局样式
│           └── main.css                   # Tailwind 入口 + 自定义样式
│
├── docker/
│   └── docker-compose.yml                 # PostgreSQL 16 + Redis 7
│
├── Docs/                                  # 设计文档（16 份）
├── Plans/                                 # 开发规划（5 份）
├── AGENTS.md                              # AI 助手配置
└── README.md                              # 本文件
```

---

## 路由与权限

| 路径 | 页面 | 访客 | 登录用户 |
|------|------|------|----------|
| `/` | 广场动态流 | 可浏览公开动态 | 全部动态 |
| `/login` | 登录页 | 可访问 | 重定向到首页 |
| `/register` | 注册页 | 可访问 | 重定向到首页 |
| `/profile/:userId` | 个人主页 | 公开资料 | 全部资料 |
| `/profile/:userId/plugins/quiz` | 默契问答 | 跳转登录 | 可访问 |
| `/profile/:userId/plugins/question-box` | 匿名提问箱 | 跳转登录 | 可访问 |
| `/profile/:userId/guestbook` | 留言板 | 跳转登录 | 可访问 |
| `/friends` | 好友管理 | 跳转登录 | 可访问 |
| `/chat` | 聊天列表 | 跳转登录 | 可访问 |
| `/chat/:roomId` | 聊天室 | 跳转登录 | 可访问 |
| `/groups` | 小组列表 | 公开小组 | 全部小组 |
| `/groups/:groupId` | 小组详情 | 跳转登录 | 可访问 |
| `/settings` | 个人设置 | 跳转登录 | 可访问 |
| `/notifications` | 通知列表 | 跳转登录 | 可访问 |

---

## API 接口一览

所有 API 基础路径为 `/api/v1`，采用 Session 认证。请求和响应格式统一为：

```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

### 认证模块

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/auth/register/` | 用户注册（用户名、密码、昵称、邮箱选填） |
| POST | `/auth/login/` | 用户登录 |
| POST | `/auth/logout/` | 退出登录 |
| GET | `/auth/me/` | 获取当前用户信息 |
| PATCH | `/auth/me/` | 更新个人信息（昵称、签名、邮箱等） |
| POST | `/auth/change-password/` | 修改密码（需旧密码验证） |
| POST | `/auth/avatar/` | 上传头像（multipart/form-data） |
| POST | `/auth/cover/` | 上传封面（multipart/form-data） |
| GET | `/auth/csrf/` | 获取 CSRF Token |

### 个人主页模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/profiles/{username_or_id}/` | 获取用户主页信息 |
| GET | `/profiles/{id}/posts/` | 获取用户的动态列表 |
| GET | `/profiles/{id}/visitors/` | 获取访客足迹 |
| GET | `/profiles/{id}/guestbook/` | 获取留言列表 |
| POST | `/profiles/{id}/guestbook/create/` | 发表留言 |
| POST | `/profiles/guestbook/{id}/reply/` | 回复留言（主人） |
| DELETE | `/profiles/guestbook/{id}/delete/` | 删除留言（主人） |

### 好友模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/friends/` | 获取好友列表 |
| POST | `/friends/request/` | 发送好友申请 |
| GET | `/friends/requests/` | 获取收到的申请列表 |
| POST | `/friends/handle/` | 处理好友申请（同意/拒绝） |
| POST | `/friends/unfriend/` | 解除好友关系 |
| GET | `/friends/search/` | 搜索用户 |

### 动态模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/posts/` | 获取广场动态列表 |
| POST | `/posts/create/` | 发布动态（multipart/form-data） |
| GET | `/posts/{id}/` | 获取单个动态详情 |
| DELETE | `/posts/{id}/delete/` | 删除自己的动态 |
| POST | `/posts/{id}/like/` | 点赞/取消点赞 |
| GET | `/posts/{id}/comments/` | 获取评论列表 |
| POST | `/posts/{id}/comments/create/` | 发表评论 |
| DELETE | `/posts/comments/{id}/delete/` | 删除自己的评论 |

### 聊天模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/chat/rooms/` | 获取聊天列表 |
| POST | `/chat/rooms/create/` | 创建私聊/群聊房间 |
| GET | `/chat/rooms/{room_id}/messages/` | 获取消息历史 |
| POST | `/chat/rooms/{room_id}/messages/send/` | 发送消息（REST 后备） |
| WS | `/ws/chat/` | WebSocket 实时聊天 |

### 小组模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/groups/` | 获取小组列表 |
| POST | `/groups/create/` | 创建小组 |
| GET | `/groups/{id}/` | 获取小组详情 |
| PATCH | `/groups/{id}/update/` | 更新小组信息（组长） |
| POST | `/groups/{id}/join/` | 加入小组 |
| POST | `/groups/{id}/leave/` | 退出小组 |
| POST | `/groups/{id}/members/{user_id}/` | 管理成员（组长） |
| GET | `/groups/{id}/posts/` | 获取小组动态 |

### 插件模块

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/plugins/quiz/questions/` | 给好友出题 |
| GET | `/plugins/quiz/questions/received/` | 我收到的题目 |
| POST | `/plugins/quiz/questions/{id}/answer/` | 答题 |
| GET | `/plugins/quiz/result/{friend_id}/` | 获取与好友的匹配度 |
| DELETE | `/plugins/quiz/questions/{id}/delete/` | 删除题目 |
| POST | `/plugins/question-box/` | 匿名提问 |
| GET | `/plugins/question-box/inbox/` | 我收到的提问 |
| POST | `/plugins/question-box/{id}/answer/` | 回答提问 |
| DELETE | `/plugins/question-box/{id}/delete/` | 删除提问 |

### 通知模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/notifications/` | 获取通知列表 |
| POST | `/notifications/{id}/read/` | 标记单条已读 |
| POST | `/notifications/read-all/` | 全部标记已读 |
| GET | `/notifications/unread-count/` | 获取未读数 |

---



## 主题设计

枫落港的界面采用秋叶主题色，通过 Tailwind CSS 扩展色板实现。核心色彩如下：

| 色值 | CSS 类 | 用途 |
|------|--------|------|
| `#C73B1D` | `maple-600` | 导航栏背景、主要按钮、关键强调元素 |
| `#F5A623` | `maple-400` | 悬停状态、标签、次要强调 |
| `#FFF8F0` | `maple-50` | 页面主背景色 |
| `#FFFFFF` | `white` | 卡片背景、内容容器 |
| `#2D2D2D` | `text-primary` | 正文文字 |
| `#8C8C8C` | `text-secondary` | 辅助文字、占位符 |
| `#E8DDD4` | `border` | 边框、分割线 |

Tailwind 配置见 `frontend/tailwind.config.js`，其中还定义了自定义阴影（card、float、modal）、字体（Noto Sans SC）和动画效果（fade-in、slide-up、scale-in 等）。

---

## 可用命令

### 后端 (backend/)

| 命令 | 说明 |
|------|------|
| `python manage.py runserver` | 启动开发服务器（默认 8000 端口） |
| `python manage.py migrate` | 执行数据库迁移 |
| `python manage.py makemigrations` | 生成迁移文件 |
| `python manage.py shell` | 进入 Django Shell |

### 前端 (frontend/)

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器（热更新，默认 5173 端口） |
| `npm run build` | 构建生产版本 |
| `npm run preview` | 预览生产构建结果 |

---

## 文档索引

项目完整文档位于 `Docs/` 目录下：

| 文件 | 内容 |
|------|------|
| `01-PRD-需求规格说明书.md` | 完整的产品需求定义，包含功能详情、用户故事和优先级矩阵 |
| `02-技术架构与数据库设计.md` | 系统架构图、技术选型理由、全部 27 张数据库表结构 |
| `03-API与WebSocket接口文档.md` | 全部 REST API 端点的请求/响应格式，WebSocket 消息协议 |
| `04-前端设计规范.md` | 主题色板、字体规范、路由表、组件树、Pinia Store 设计 |
| `05-插件系统设计.md` | 后端插件基类与注册器、前端 PluginRegistry、数据契约 |
| `06-开发任务书与验收标准.md` | 分 7 个 Milestone 的开发任务分配与验收 checklist |
| `07-访客公开浏览功能设计方案.md` | 未登录访客的访问权限矩阵及交互行为定义 |

开发规划文档位于 `Plans/` 目录下：

| 文件 | 内容 |
|------|------|
| `01-迭代路线图.md` | 7 个 Milestone 的时间线与依赖关系 |
| `02-环境搭建指南.md` | 本地开发环境搭建的详细步骤 |
| `03-开发协作规范.md` | 分支策略、代码审查流程、提交规范 |
| `04-实现进度跟踪.md` | 各模块的实现进度记录 |
| `05-文档一致性审查与修正.md` | 文档与实际代码的偏差记录 |

---

## 开发约定

- **分支策略**：当前开发在 `BugFixer` 分支上进行（基于 `main`）
- **后端架构**：Django 5 + DRF，Session 认证，统一响应格式 `{code, message, data}`
- **前端架构**：Vue 3 Composition API + Tailwind CSS，使用 `@/` 路径别名指向 `src/`
- **组件规范**：公共组件统一放在 `src/components/`，使用 `card-base`、`btn-primary`、`btn-secondary`、`btn-ghost`、`input-base`、`skeleton`、`page-title` 等设计系统类
- **确认弹窗**：统一使用 `useConfirm()` composable 配合全局 `<ConfirmDialog />` 组件
- **开关组件**：统一使用 `<ToggleSwitch v-model="..." />`

详细规范请查看 `AGENTS.md` 与 `Docs/04-前端设计规范.md`。

---

## 未完成

以下为主要待完善项目：

| 问题 | 说明 |
|------|------|
| 评论区无分页 | CommentListView 未实现分页，长动态评论区加载全部评论，性能有待优化 |

---

## 许可证

[MIT](./LICENSE)

Copyright (c) 2026 RL-RedLeaf

---

> 项目代码中以 `FallingMapleHaven` 作为英文项目名，`枫落港` 为其中文名称。
