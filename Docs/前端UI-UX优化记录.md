# 前端 UI/UX 优化记录

> 分支: `UIUX` | 日期: 2026-06-29

---

## 一、设计系统

### 1.1 Tailwind 配置新增

| 类别 | 新增内容 | 文件 |
|------|---------|------|
| 圆角 | `xl: 12px`, `2xl: 16px` | `tailwind.config.js` |
| 阴影 | `card: 0 2px 8px`, `float: 0 2px 12px`, `modal: 0 8px 32px` | `tailwind.config.js` |
| 字号 | `page-title: 24px Bold`, `card-title: 18px Semibold`, `body: 15px`, `aux: 13px`, `tag: 12px Medium` | `tailwind.config.js` |
| 动画 | `fade-in`, `slide-up`, `slide-in-right`, `scale-in`, `pulse-soft` | `tailwind.config.js` |

### 1.2 CSS 组件类

在 `main.css` 的 `@layer components` 中定义了以下可复用类：

| 类名 | 用途 | 包含 |
|------|------|------|
| `card-base` | 卡片容器 | 白色背景、圆角 16px、边框、卡片阴影、hover 浮动阴影 |
| `btn-primary` | 主要按钮 | 枫叶红背景、白色文字、hover/active/disabled 状态 |
| `btn-secondary` | 次要按钮 | 枫叶红边框、枫叶红文字、hover 浅色背景 |
| `btn-ghost` | 幽灵按钮 | 灰色文字、hover 枫叶色 |
| `input-base` | 输入框 | 边框、聚焦 ring、过渡动画 |
| `skeleton` | 骨架屏 | 灰色背景、脉冲动画 |
| `page-container` | 页面容器 | 最大宽度、居中、内边距 |
| `page-title` | 页面标题 | 30px Bold 枫叶色 |
| `tab-nav` / `tab-btn` | Tab 导航 | 枫叶色背景、圆角容器、激活态白色卡片 |

### 1.3 全局样式

| 规则 | 说明 |
|------|------|
| `*:focus-visible` | 全局可见焦点环 (2px solid #C73B1D) |
| `button:focus-visible` | 按钮焦点环 |
| `.scrollbar-hide` | 隐藏滚动条（保留滚动功能） |
| 字体抗锯齿 | `-webkit-font-smoothing: antialiased` |
| 页面过渡 | App.vue 的 `<RouterView>` 包裹 `<Transition name="page">`，fade + slide |

---

## 二、SVG 图标系统

### 2.1 依赖

```json
"dependencies": {
  "lucide-vue-next": "^0.x"
}
```

### 2.2 Icon 组件

`frontend/src/components/Icon.vue` — 统一图标封装

- **Props**: `name` (图标名), `size` (默认 20)
- **Props**: `name` (图标名), `size` (默认 20), `fill` (默认 "none", 用于 heart 等可填充图标)
- **覆盖范围**: 50+ 常用图标 (home, user, heart, bell, settings 等)
- **特点**: SVG 矢量图标，支持主题色继承，无锯齿，跨平台一致

所有页面已从 emoji 迁移至 SVG 图标：

| 页面 | 替换位置 |
|------|---------|
| NavBar | 导航链接图标、下拉菜单 |
| MobileTabBar | 底部 Tab 图标 |
| PostCard | 附件、点赞、评论图标 |
| HomePage | 空状态插图、访客提示 |
| LoginPage | 密码切换、Loading spinner |
| RegisterPage | 密码切换、提示图标 |
| ProfilePage | 插件卡片、访客、留言板、空状态 |
| NotificationsPage | 通知类型图标、已读/未读指示器、空状态 |

---

## 三、新增组件

### 3.1 ToggleSwitch.vue

路径: `frontend/src/components/ToggleSwitch.vue`

标准开关组件，符合无障碍规范：

```vue
<ToggleSwitch v-model="someBoolean" />
```

| 特性 | 说明 |
|------|------|
| 交互 | 点击切换，`v-model` 双向绑定 |
| 尺寸 | 轨道 44×24px，圆球 20×20px |
| 对齐 | `absolute` 定位，OFF=`left-0.5`(2px)，ON=`left-[22px]`(22px) |
| 无障碍 | `role="switch"`, `aria-checked`, `focus-visible` 焦点环 |
| 禁用 | 支持 `disabled` prop |

应用于 SettingsPage 的"公开真实姓名"和"足迹对外可见"开关。

### 3.2 BottomSheet.vue

路径: `frontend/src/components/BottomSheet.vue`

全屏底部弹出面板（Mobile Bottom Sheet），适用于手机端表单/弹窗：

```vue
<BottomSheet :show="visible" title="标题" @close="visible = false">
  <YourForm />
</BottomSheet>
```

| 特性 | 说明 |
|------|------|
| 响应式 | 手机端（<768px）全屏底部滑入；桌面端居中缩放弹出 |
| 关闭 | 点击遮罩、按 Escape、点击关闭按钮均可关闭 |
| 动画 | 手机端 `transform: translateY(100%) → 0`；桌面端 `scale(0.9) → 1` |
| 标题栏 | 顶部显示拖拽手柄（线）和标题，移动端带关闭按钮 |
| 投射 | 使用 `<Teleport to="body">` 避免 z-index/嵌套问题 |

应用于 HomePage 创建动态表单（手机端）。

### 3.3 PostCreateCard.vue

路径: `frontend/src/components/PostCreateCard.vue`

创建动态的完整表单组件，从 HomePage 抽取：

```vue
<PostCreateCard @close="showCreateForm = false" />
```

| 特性 | 说明 |
|------|------|
| 状态 | 内容/图片/可见性/话题标签/提交中 |
| 图片 | 支持多选（最多 9 张）、预览、悬停删除 |
| 发布 | FormData 提交，含 loading 状态 |
| 关闭 | 发布成功或点击取消触发 `close` 事件 |

HomePage 中：桌面端 inline 展开，手机端嵌入 BottomSheet。

### 3.4 PluginEntryGrid.vue

路径: `frontend/src/components/PluginEntryGrid.vue`

插件入口卡片横向滚动网格：

```vue
<PluginEntryGrid :plugins="list" @navigate="goToPlugin" />
```

| Props | 类型 | 说明 |
|-------|------|------|
| `plugins` | `Array<{name, icon, desc, route}>` | 插件卡片列表 |
| `@navigate` | emit | 点击卡片时触发，参数为 `plugin` 对象 |

从 ProfilePage 抽取，替换 inline 插件循环。

### 3.5 GuestbookBoard.vue

路径: `frontend/src/components/GuestbookBoard.vue`

留言板面板（ProfilePage Tab 内嵌版）：

```vue
<GuestboardBoard
  :userId="id"
  :entries="entries"
  :isOwner="isOwner"
  :isGuest="isGuest"
  @update:entries="entries = $event"
/>
```

| Props | 类型 | 说明 |
|-------|------|------|
| `userId` | Number/String | 留言板归属用户 |
| `entries` | Array | 留言列表（双向绑定 via `@update:entries`） |
| `isOwner` | Boolean | 是否本人（显示回复/删除） |
| `isGuest` | Boolean | 是否游客（显示登录提示） |

功能包含：新增留言、主人回复、主人删除、TransitionGroup 列表动画、空状态。

---

## 四、页面优化详情

### 4.1 App.vue

- `<RouterView>` 添加 `<Transition name="page">`，页面切换淡入淡出 + 垂直偏移

### 4.2 HomePage 广场

| 改进 | 说明 |
|------|------|
| 骨架屏 | 首次加载显示 3 个卡片骨架，含头像/文字占位 |
| 创建表单 | 桌面端 inline 展开（动画）、手机端 BottomSheet 全屏底部弹出 |
| 发布表单抽取 | 完整表单逻辑抽至 `PostCreateCard.vue` 独立组件 |
| 瀑布流布局 | 桌面端（≥768px）使用两组独立 flex 列（`leftPosts`/`rightPosts` 奇偶交错分配），避免 CSS `columns` 先填充左列再溢出的不均衡问题；gap-6 间距，每列 `flex-col gap-5`；入场逐张错开 60ms 淡入上滑（`animate-stagger-fade-in`） |
| 空状态 | SVG 插图 + 引导文字 |
| 话题标签 | `transition-all` + 激活态阴影 |
| 访客提示 | SVG 插图替代纯文本 |

### 4.3 LoginPage / RegisterPage 登录注册

| 改进 | 说明 |
|------|------|
| 品牌标识 | 顶部添加"枫"字 Logo 装饰块 |
| 表单标签 | 添加 `id` + `for` 关联，`autocomplete` 属性 |
| 加载状态 | 按钮内嵌 spinner 动画 |
| 密码切换 | emoji → SVG 图标 (`eye`/`eyeOff`) |
| 错误提示 | 包裹 `<Transition name="fade">` 动画 |
| 入口动画 | 卡片 `animate-scale-in` 弹入 |

### 4.4 ProfilePage 个人主页

| 改进 | 说明 |
|------|------|
| 骨架屏 | 加载时显示封面/头像/文字骨架 |
| 插件卡片 | emoji → SVG 图标 + 抽取为 `PluginEntryGrid.vue` 组件 |
| 留言板 | 抽取为 `GuestbookBoard.vue` 独立组件（含回复/删除/TranstitionGroup） |
| 访客列表 | 分割线样式 + 空状态插图 |
| 用户不存在 | SVG 插图替代纯文字 |
| 删除按钮 | 添加垃圾箱图标 |

### 4.5 NotificationsPage 通知

| 改进 | 说明 |
|------|------|
| 骨架屏 | 加载时 5 个骨架项 |
| 通知图标 | 彩色圆底 + 类型对应 SVG 图标 |
| 未读指示器 | 右侧小红点 (已读隐藏) |
| 已读/未读区分 | 已读: 浅色背景 + 灰色文字；未读: 白色背景 + 加粗文字 + 卡片阴影 |
| 全部已读按钮 | 添加勾选图标 |
| 空状态 | SVG 插图 |

### 4.6 SettingsPage 个人设置

| 改进 | 说明 |
|------|------|
| 开关组件 | 内联代码 → `ToggleSwitch` 组件 |

### 4.7 其他

- **PostCard**: 使用 `card-base` 类，附件/点赞/评论图标迁移；PostActions 全部替换为 SVG 图标（`Icon name="heart" fill` 支持已点赞填充色）
- **交互设计**: 详见下方第七节
- **NavBar**: 桌面导航链接添加 SVG 图标，下拉菜单 `Transition` 动画
- **MobileTabBar**: 底部导航 tab 图标替换，触控区域增大

---

## 五、组件树（当前）

```
App.vue
├── NavBar.vue                   # 顶部导航 (桌面端, md+)
├── <RouterView>                 # 页面内容 (含 Transition 动画)
│   ├── HomePage.vue
│   │   ├── PostCreateCard.vue   # ★ 新增 (创建动态表单，桌面内联/手机BottomSheet)
│   │   │   ├── AvatarImage.vue
│   │   │   └── Icon.vue
│   │   ├── BottomSheet.vue      # ★ 新增 (Mobile底部弹窗)
│   │   ├── PostCard.vue
│   │   │   ├── AvatarImage.vue
│   │   │   ├── Icon.vue
│   │   │   ├── PostImageGrid.vue
│   │   │   ├── PostActions.vue
│   │   │   └── CommentSection.vue
│   │   └── … (骨架屏/空状态/话题)
│   ├── LoginPage.vue            # Icon.vue
│   ├── RegisterPage.vue         # Icon.vue
│   ├── ProfilePage.vue
│   │   ├── PluginEntryGrid.vue  # ★ 新增 (插件入口卡片)
│   │   ├── GuestbookBoard.vue   # ★ 新增 (留言板面板)
│   │   ├── AvatarImage.vue
│   │   ├── FriendButton.vue
│   │   └── TabBar.vue
│   ├── SettingsPage.vue
│   │   ├── AvatarImage.vue
│   │   ├── ToggleSwitch.vue     # ★ 新增
│   │   └── Icon.vue
│   ├── FriendsPage.vue
│   │   ├── AvatarImage.vue
│   │   ├── FriendButton.vue
│   │   └── Icon.vue
│   ├── NotificationsPage.vue    # Icon.vue
│   └── …
├── MobileTabBar.vue             # 底部导航 (手机端, <md)
├── ToastContainer.vue           # 全局提示
└── Icon.vue                     # ★ 新增 (SVG图标封装)
```

---

## 六、未完成项

| 项 | 优先级 | 说明 |
|----|--------|------|
| ChatRoomPage 组件抽取（MessageList/MessageInput/ChatHeader） | 低 | 当前 MessageBubble 已抽取，剩余在页面内联 |
| AdminSidebar / 后台组件抽取 | 低 | 管理后台侧边栏和头部为内联 |
| `useNotificationStore` | 低 | 设计规范标记为不阻塞 |
| `usePluginStore` | 低 | 设计规范标记为不阻塞 |
| Avatar.vue 头像是像独立组件 | 低 | 已有 AvatarImage.vue，但规范要求 `Avatar.vue` |
| Quiz 匹配度分母算法 | 待定 | 产品决策待确认 |

---

## 七、交互设计（参考小红书风格）

### 7.1 PostCard 卡片 hover

| 元素 | 效果 |
|------|------|
| 卡片整体 | 上浮 6px（`-translate-y-1.5`），阴影从 `card` 加深为 `0 8px 28px rgba(0,0,0,0.10)`，过渡 0.2s ease-out |
| 左侧装饰 | `border-l-[3px]` 透明 → hover 变 `maple-600`，类似书签标记，暗示可交互 |
| 头像 | `group-hover/card:scale-105` 微缩放 5%，视觉反馈 |
| 用户名 | `hover:text-maple-600` 变色 |

### 7.2 PostImageGrid 图片 hover

| 效果 | 说明 |
|------|------|
| 缩放 | 每张图包裹 `overflow-hidden` 容器，hover 时 `scale-105` 平滑放大 |
| 过渡 | `transition-transform duration-300 ease-out` |

### 7.3 点赞动画

| 效果 | 说明 |
|------|------|
| 点击触发 | `animate-like-pop`：0→scale(1.3)→scale(1)，350ms |
| 保护 | `select-none` 防止快速连点时选中文字 |
| 状态 | 未点赞 `fill="none"`，已点赞 `fill="currentColor"` + `text-red-500` |

### 7.4 瀑布流入场动画

| 效果 | 说明 |
|------|------|
| 逐张淡入 | `animate-stagger-fade-in`，opacity 0→1 + translateY(16px)→0 |
| 错开间隔 | 每张 `index * 40ms`（手机端）或 `index * 60ms`（桌面端双列） |
| 滚动加载 | 新加载卡片仅新 DOM 元素触发动画，已有卡片不受影响 |

---

## 八、管理后台优化（2026-06-29）

### 8.1 AdminDashboard 布局重做

| 改进 | 说明 |
|------|------|
| 头部 | `bg-gradient-to-r from-maple-800 to-maple-700` 枫叶渐变主题，左侧汉堡菜单按钮+盾牌图标+标题，右侧"返回前台"链接 |
| 侧边栏 | 左侧 56px 宽白色面板，`border-r border-border` 分割，内置 6 项+插件动态注册项 |
| 导航动效 | 激活态粗枫叶色左竖条（`absolute left-0 w-1 h-5 bg-maple-600 rounded-r-full`）+ `bg-maple-50` 背景，hover 缩放图标 |
| 移动导航 | `<md` 通过 `fixed inset-0 z-40` 半透明遮罩 + 右侧滑入面板，`animate-slide-in-right` 动画 |
| 页面过渡 | `<RouterView>` 包裹 `<Transition name="page">`，淡入+上滑（8px）0.2s |
| 图标 | Emoji → SVG 图标：`barChart` / `users` / `fileText` / `puzzle` / `settings` / `scrollText` |

### 8.2 AdminStatsPage 数据统计

| 改进 | 说明 |
|------|------|
| 统计卡片 | Emoji → SVG 图标（`users`/`activity`/`fileText`/`messageCircle`/`send`），渐变圆底 `bg-gradient-to-br`，白色图标 |
| 骨架屏 | 加载时 5 个骨架卡片（skeleton 头像+文字） |
| 柱状图颜色 | 使用设计系统色（`bg-maple-500`/`bg-purple-500`/`bg-orange-500`/`bg-blue-500`/`bg-green-500`/`bg-pink-500`），圆角 `rounded-full` |
| 入场动画 | 卡片 `animate-fade-in` 错开 `60ms`，趋势图区域 `animate-fade-in` |
| Tab 按钮 | 使用 `tab-btn`/`tab-btn-active`/`tab-btn-inactive` 类 |

### 8.3 表格页面统一优化

| 页面 | 改进 |
|------|------|
| AdminUsersPage | `card-base` 包裹表格，表头 `bg-maple-50/60`，状态标签圆角 + 状态点，行 hover `bg-maple-50/40`，骨架屏/空状态（`users` 图标），入场每行错开 30ms |
| AdminPostsPage | 同上 + 删除按钮使用 `trash2` SVG 图标 `btn-ghost`，TabBar 保留 |
| AdminLogsPage | 筛选栏使用 `card-base` + `input-base` + `btn-primary`（含 `search` 图标），分页使用 `btn-secondary` + `chevronLeft`/`chevronRight` 图标，骨架屏 5 行 |
| AdminAnonymousQuestionsPage | `page-title` 类补回，表头 `bg-maple-50/60`，状态标签（已回答绿色/未回答黄色+状态点），行 hover + 入场动画，骨架屏+空状态 |

### 8.4 AdminPluginsPage 插件管理

| 改进 | 说明 |
|------|------|
| 开关 | 内联 switch → `ToggleSwitch.vue` 组件 |
| 卡片 | `card-base` + `hover:shadow-md hover:-translate-y-0.5` 悬浮效果，入口 `animate-fade-in` 错开 50ms |
| 图标 | 卡片标题前加 `puzzle` SVG 图标 |
| 骨架屏 | 6 个卡片骨架（网格布局 `grid-cols-1/2/3`） |
| 空状态 | `puzzle` 图标 + 文字 |

### 8.5 AdminSettingsPage 站点设置

| 改进 | 说明 |
|------|------|
| 表单控件 | 所有输入框 `input-base` 替代内联 focus 样式 |
| 注册开关 | Checkbox → `ToggleSwitch.vue`，行列布局 |
| 按钮 | 内联按钮 → `btn-primary` + `check` 图标，保存成功 `check` 图标 + 绿色文字 |
| 骨架屏 | 加载时 4 个骨架输入行 |
| 容器 | `card-base max-w-lg` |

### 8.6 Icon.vue 新增图标

| 图标名 | Lucide 组件 |
|--------|------------|
| `barChart` | BarChart3 |
| `activity` | Activity |
| `puzzle` | Puzzle |
| `scrollText` | ScrollText |

### 8.7 组件树 (admin)

```
AdminDashboard.vue
├── Icon.vue
├── navItems (内置6项 + pluginRegistry.getAdminSidebarItems())
│   ├── stats     → barChart
│   ├── users     → users
│   ├── posts     → fileText
│   ├── plugins   → puzzle
│   ├── settings  → settings
│   └── logs      → scrollText
└── <RouterView v-slot="{ Component }">
    ├── AdminStatsPage.vue            # SVG 卡片 + 骨架屏 + 柱状图
    ├── AdminUsersPage.vue            # card-base 表格 + 骨架屏
    ├── AdminPostsPage.vue            # TabBar + card-base 表格
    ├── AdminPluginsPage.vue          # ToggleSwitch + card-base 网格
    ├── AdminSettingsPage.vue         # input-base + ToggleSwitch
    ├── AdminLogsPage.vue             # 筛选 + card-base 表格 + 分页
    └── AdminAnonymousQuestionsPage.vue # card-base 表格 + 状态标签
```

---

## 九、第二轮优化：交互反馈与视觉打磨（2026-06-29）

### 9.1 main.css 增强

| 改进 | 说明 |
|------|------|
| `card-base:active` | 按下缩放 `scale-[0.97]`（之前 0.99 几乎不可感知） |
| `btn-primary`/`btn-secondary`/`btn-ghost` | 按下缩放 `scale-[0.97]` + `inline-flex items-center gap-1.5` 图标文字对齐 |
| `.skeleton` | 新增伪元素 shimmer 光泽效果（`linear-gradient` 滑动动画），不再只是灰色脉冲 |
| `.table-header` | 工具类定义 `sticky top-0 z-10`，应用至所有表格 |

### 9.2 所有表格页统一优化

| 改进 | 适用页面 |
|------|---------|
| 表头粘性 | `thead` 添加 `table-header`，滚动时列标题固定不消失 |
| `scope="col"` | 所有 `th` 补充无障碍属性 |
| 行 hover 浮现操作 | `tr` 加 `group`，操作按钮 `opacity-0 group-hover:opacity-100`，减少视觉噪音 |
| 原生 confirm 替换 | 详见 9.6 |
| 空状态美化 | 图标增大至 40px，补充引导文字（如"当有新用户注册时，他们将显示在此处"） |

### 9.3 AdminStatsPage 增强

| 改进 | 说明 |
|------|------|
| 统计卡片 hover | 缩放 1.02 + 上浮 0.5 像素，鼠标悬停有抬起感 |
| 柱状图渐变色 | 从纯色（`bg-maple-500`）改为渐变（`bg-gradient-to-r from-maple-400 to-maple-600`），所有 6 类柱状图同理 |
| 柱状入场动画 | 每行柱状条错开 30ms 淡入（`animate-fade-in` + `animationDelay`） |

### 9.4 AdminDashboard 侧边栏

| 改进 | 说明 |
|------|------|
| 活跃指示条 | 从 `v-if` 直接消失/出现改为 `opacity` + `scale-y` 过渡切换，有渐隐渐现效果 |

### 9.5 搁置项（工程量较大，后续再做）

| 搁置项 | 涉及范围 | 说明 |
|--------|---------|------|
| 暗色模式 (Dark Mode) | 全部 8 个 admin 页面 + tailwind.config.js | 所有页面无 `dark:` 类，需逐个添加全局语义化颜色 token |
| 表单内联验证 | AdminSettingsPage | 数字/URL/扩展名字段需添加即时校验 + 错误提示 |
| 分页页码按钮 | AdminLogsPage | 从纯"上一页/下一页"升级为带页码按钮和跳转输入 |
| 搜索/筛选控件 | AdminUsersPage / AdminPostsPage / AdminLogsPage | 功能缺失，需添加搜索框/筛选器逻辑 |
| 原生 confirm() 替换 | AdminPostsPage | 改成 Modal 确认弹窗，涉及新增 Dialog 组件 |
| 日志 JSON 格式化 | AdminLogsPage | `JSON.stringify` 原始输出改为可展开/语法高亮 |

---

## 十、原生控件替换（2026-06-29）

### 10.1 ConfirmDialog 组件

路径: `frontend/src/components/ConfirmDialog.vue`

枫叶主题确认弹窗，替代浏览器原生 `confirm()`：

```vue
const { confirm } = useConfirm()
if (!await confirm({ title: '删除', message: '...', variant: 'danger', confirmText: '删除' })) return
```

| 特性 | 说明 |
|------|------|
| 响应式 | `<Teleport to="body">` 避免 z-index 嵌套，遮罩 `bg-black/40 backdrop-blur-sm` |
| 动画 | `<Transition name="confirm">` + 卡片 `animate-scale-in` |
| 变体 | `variant="danger"` 时图标/按钮红色；`default` 时枫叶色 |
| 无障碍 | `role="alertdialog"`, `aria-modal="true"`, `aria-labelledby` |
| 关闭 | 点击遮罩 / Escape 键 = 取消 |
| 全局注册 | 在 `App.vue` 加载 `<ConfirmDialog />` |

### 10.2 useConfirm composable

路径: `frontend/src/composables/useConfirm.js`

模块级单例状态管理：

```js
const dialogState = reactive({ visible, title, message, confirmText, cancelText, variant })
let resolveCallback = null
```

| 方法 | 说明 |
|------|------|
| `confirm(options)` | 返回 `Promise<boolean>`，打开弹窗 |
| `resolveConfirm(value)` | 内部调用，关闭弹窗并 resolve Promise |

### 10.3 替换 native confirm() 记录

| 文件 | 行号 | 原代码 | 替换为 |
|------|------|--------|--------|
| `CommentSection.vue` | 42 | `window.confirm('确认删除这条评论？')` | `confirm({ variant: 'danger', confirmText: '删除' })` |
| `PostCard.vue` | 46 | `window.confirm('确认删除这条动态？')` | 同上 |
| `GuestbookBoard.vue` | 49 | `confirm('确认删除这条留言？')` | 同上 |
| `AdminPostsPage.vue` | 31,41 | `confirm('确认删除...')` | 同上 |
| `ProfilePage.vue` | 125 | `window.confirm(确认${action}此用户？)` | `confirm({ title: \`${action}用户\`, variant: action==='封禁'?'danger':'default' })` |

### 10.4 QuizPage 原生控件样式化

| 元素 | 行号 | 原样式 | 改为 |
|------|------|--------|------|
| `<select>` 选择好友 | 108 | inline focus 样式 | `input-base` |
| `<input>` 题目 | 120 | inline focus 样式 | `input-base` |
| `<input>` 正确答案 | 129 | inline focus 样式 | `input-base` |
| `<button>` 提交题目 | 139 | inline maple 样式 | `btn-primary` |
| `<select>` 匹配好友 | 183 | inline focus 样式 | `input-base` |
| `<input>` 输入答案 | 159,163 | inline focus 样式 | `input-base` |
| `<button>` 提交答案 | 168 | inline maple 样式 | `btn-primary` |
| 题目卡片容器 | 154 | `bg-white rounded-xl border` | `card-base` |

### 10.5 自定义下拉菜单（SelectField 组件取代原生 select）

原生 `<select>` 被完全替换为自定义下拉组件 `SelectField.vue`：

| 改进 | 说明 |
|------|------|
| 架构 | 移除 `<select>`/`<option>`，改为 `<button>` + `<div role="listbox">` 弹出面板 |
| 选项面板 | 不再由浏览器渲染系统原生下拉，改为绝对定位弹出面板，完全受 Tailwind 样式控制 |
| 关闭方式 | `document click` 外部检测 + Escape 键，面板关闭后焦点回到触发按钮 |
| 键盘支持 | Enter/Space 开合、Escape 关闭 |
| 无障碍 | 按钮 `aria-haspopup="listbox"`/`:aria-expanded`；选项 `role="option"`/`:aria-selected` |
| 选中态 | 当前选中项高亮：`bg-maple-50 text-maple-700 font-medium` |
| 动画 | `Transition name="drop"`：淡入 + 向下位移 |

替换文件：

| 文件 | 说明 |
|------|------|
| `AdminLogsPage.vue` | 操作类型筛选，`options` 含"全部"默认项 |
| `PostCreateCard.vue` | 可见性（公开/仅好友/私密）+ 话题选择（含"选择话题"占位）|
| `QuizPage.vue` | 创建题目 + 匹配度两个好友选择，`friends.map()` 转换 option 格式 |

### 10.6 复选框替换

| 文件 | 原控件 | 改为 |
|------|--------|------|
| `GroupListPage.vue` | `<input type="checkbox">` 公开小组 | `ToggleSwitch v-model="createForm.is_public"` |

### 10.7 NavBar 下拉菜单优化

| 改进 | 说明 |
|------|------|
| 关闭方式 | 移除`fixed inset-0` 全屏透明遮罩，改用 `document.addEventListener('click', ...)` 点击外部检测，不再阻塞页面交互 |
| 键盘支持 | `onMounted`/`onUnmounted` 监听 Escape 键关闭，聚焦回到触发按钮 |
| 无障碍 | 按钮添加 `aria-haspopup="true"` 和 `:aria-expanded`；菜单项添加 `role="menu"`/`role="menuitem"` |
| 箭头指示 | 按钮右侧添加 `chevronDown` 图标，展开时 `rotate-180` 旋转 |
| 小三角 | 菜单上方 `absolute -top-1.5 right-6` 旋转 45° 白色小方块，仿气泡指示 |
| 按反馈 | 按钮 `active:scale-[0.97]` 按下缩放 |
| 交互增强 | 菜单项 hover 时加粗文字：`hover:text-maple-700` |

## 11. 移动端 UI/UX 修复计划

### 11.1 紧急（影响功能可用性）

| 优先级 | 问题 | 文件 | 修复方案 |
|--------|------|------|----------|
| P0 | `safe-area-bottom` class 未定义 | `MobileTabBar.vue` + `main.css` | 在 `main.css` 定义 `.safe-area-bottom { padding-bottom: env(safe-area-inset-bottom); }` |
| P0 | 评论输入框/发送按钮触控区过小（~28px） | `CommentSection.vue` | `py-1.5` 改为 `py-2.5`，确保高度 >= 44px |
| P0 | 删除图片按钮仅 24×24px | `PostCreateCard.vue` | 扩大至 `w-8 h-8`（32px）或 `w-10 h-10`（40px） |

### 11.2 重要（触控体验优化）

| 优先级 | 问题 | 文件 | 修复方案 |
|--------|------|------|----------|
| P1 | 设计系统按钮/输入框缺少 `min-height: 44px` | `main.css` | 给 `btn-primary`、`btn-secondary`、`btn-ghost`、`input-base` 添加 `min-h-11`（44px） |
| P1 | BottomSheet 移动端无最大高度限制 | `BottomSheet.vue` | 无 `md:` 前缀时添加 `max-h-[90dvh]` |
| P1 | 聊天页发送/返回按钮 < 44px | `ChatRoomPage.vue` | 发送按钮 `py-2.5`→`py-3`；返回按钮 `w-8 h-8`→`w-10 h-10` |
| P1 | 首页标签筛选按钮 36px | `HomePage.vue` | `min-h-[36px]`→`min-h-[44px]` |
| P1 | 设置页保存/换头像按钮过小 | `SettingsPage.vue` | `py-2`→`py-2.5`，`py-1.5`→`py-2.5` |
| P1 | PostCard 删除按钮无触控区 | `PostCard.vue` | 添加 `px-2 py-1` 最小触控区 |

### 11.3 次要（体验细节）

| 优先级 | 问题 | 文件 | 修复方案 |
|--------|------|------|----------|
| P2 | BottomSheet 关闭按钮 32px | `BottomSheet.vue` | `w-8 h-8`→`w-10 h-10` |
| P2 | ProfilePage 后台按钮 26px | `ProfilePage.vue` | 使用 `btn-ghost` 或添加 padding |
| P2 | 标签滚动无溢出渐变提示 | `HomePage.vue` | 在 `overflow-x-auto` 容器添加左右渐变遮罩 |
| P2 | 设置页标签不联动 ToggleSwitch | `SettingsPage.vue` | 标签添加 `@click` 或使用 `label for` 关联 |
| P2 | 设置页密码字段无显示切换 | `SettingsPage.vue` | 添加 show/hide 密码切换按钮 |
| P2 | 全局缺少 safe-area 适配 | `App.vue` / 各页面 | 在固定/底部元素添加 `pb-[env(safe-area-inset-bottom)]` |

### 11.4 各文件改动清单

```
mobile/  (移动端修复计划)
├── main.css
│   ├── + .safe-area-bottom { ... }
│   ├── + btn-primary: min-h-11
│   ├── + btn-secondary: min-h-11
│   ├── + btn-ghost: min-h-11
│   └── + input-base: min-h-11
├── MobileTabBar.vue
│   └── + safe-area-bottom class 定义
├── CommentSection.vue
│   ├── input: py-1.5 → py-2.5
│   └── send button: py-1.5 → py-2.5
├── PostCreateCard.vue
│   └── image remove button: w-6 h-6 → w-8 h-8
├── BottomSheet.vue
│   ├── + max-h-[90dvh] (no md:)
│   └── close button: w-8 h-8 → w-10 h-10
├── ChatRoomPage.vue
│   ├── send button: py-2.5 → py-3
│   └── back button: w-8 h-8 → w-10 h-10
├── HomePage.vue
│   ├── tag button: min-h-[36px] → min-h-[44px]
│   └── + scroll fade gradient (可选)
├── SettingsPage.vue
│   ├── save button: py-2 → py-2.5
│   ├── cover/avatar button: py-1.5 → py-2.5
│   └── + password visibility toggle
├── PostCard.vue
│   └── delete button: + px-2 py-1
└── ProfilePage.vue
    └── admin button: + btn-ghost or extra padding
```
