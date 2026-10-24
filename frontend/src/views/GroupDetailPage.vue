<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { groupApi } from '@/api/plugin'
import { postApi } from '@/api/posts'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import PostCard from '@/components/PostCard.vue'
import AvatarImage from '@/components/AvatarImage.vue'
import TabBar from '@/components/TabBar.vue'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import SelectField from '@/components/SelectField.vue'
import Icon from '@/components/Icon.vue'
import { relativeTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { confirm } = useConfirm()
const groupId = computed(() => Number(route.params.groupId))

const group = ref(null)
const posts = ref([])
const members = ref([])
const activeTab = ref('posts')
const loading = ref(true)
const joining = ref(false)
const hasPendingRequest = ref(false)
const newPostContent = ref('')
const syncToProfile = ref(false)
const submittingPost = ref(false)
const postPage = ref(1)
const hasMorePosts = ref(true)
const loadingPosts = ref(false)

const showEditModal = ref(false)
const editForm = ref({ name: '', description: '', is_public: true })
const editCoverFile = ref(null)
const editing = ref(false)
const editError = ref('')

const showTransferModal = ref(false)
const transferSelectedId = ref(null)
const transferring = ref(false)

const memberSubTab = ref('list')
const joinRequestsList = ref([])
const loadingJoinRequests = ref(false)
const handlingRequestId = ref(null)

const isMember = computed(() => {
  if (!group.value?.members) return false
  return group.value.members.some(m => m.user_id === authStore.user?.user_id)
})

const isOwner = computed(() => {
  return group.value?.owner?.user_id === authStore.user?.user_id
})

const currentUserMembership = computed(() => {
  if (!group.value?.members) return null
  return group.value.members.find(m => m.user_id === authStore.user?.user_id) || null
})

const isAdmin = computed(() => {
  return currentUserMembership.value?.role === 'admin' && !isOwner.value
})

const canManageRequests = computed(() => {
  return isOwner.value || isAdmin.value
})

const toast = useToast()

onMounted(() => {
  fetchGroup()
})

watch(() => route.params.groupId, () => {
  postPage.value = 1
  hasMorePosts.value = true
  posts.value = []
  fetchGroup()
})

async function fetchGroup() {
  loading.value = true
  try {
    const res = await groupApi.detail(groupId.value)
    group.value = res.data
    members.value = res.data?.members || []
    if (isMember.value) {
      await fetchPosts(true)
    }
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

watch(memberSubTab, (val) => {
  if (val === 'requests' && canManageRequests.value) {
    fetchJoinRequests()
  }
})

async function fetchJoinRequests() {
  loadingJoinRequests.value = true
  try {
    const res = await groupApi.joinRequests(groupId.value)
    joinRequestsList.value = res.data || []
  } catch { /* ignore */ } finally {
    loadingJoinRequests.value = false
  }
}

async function handleRequestAction(request, action) {
  handlingRequestId.value = request.id
  try {
    await groupApi.handleJoinRequest(groupId.value, request.id, action)
    toast.success(action === 'approved' ? '已同意申请' : '已拒绝申请')
    await fetchJoinRequests()
    await fetchGroup()
  } catch { /* ignore */ } finally {
    handlingRequestId.value = null
  }
}

async function fetchPosts(reset = false) {
  if (loadingPosts.value) return
  loadingPosts.value = true
  try {
    if (reset) postPage.value = 1
    const res = await groupApi.posts(groupId.value, { page: postPage.value, page_size: 20 })
    const results = res.data?.results ?? res.data ?? []
    if (reset) {
      posts.value = results
    } else {
      posts.value.push(...results)
    }
    if (res.data) {
      hasMorePosts.value = res.data.page * res.data.page_size < res.data.total
    } else {
      hasMorePosts.value = false
    }
    if (!reset) postPage.value += 1
  } catch { /* ignore */ } finally {
    loadingPosts.value = false
  }
}

async function handleJoin() {
  joining.value = true
  try {
    const isPublicGroup = group.value?.is_public
    await groupApi.join(groupId.value)
    await fetchGroup()
    toast.success(isPublicGroup ? '已加入小组' : '申请已发送，等待审核')
    if (!isPublicGroup) hasPendingRequest.value = true
  } catch (e) {
    toast.error(e.response?.data?.message || '操作失败')
  } finally {
    joining.value = false
  }
}

async function handleLeave() {
  joining.value = true
  try {
    await groupApi.leave(groupId.value)
    await fetchGroup()
    toast.success('已退出小组')
  } catch { /* ignore */ } finally {
    joining.value = false
  }
}

function onPostDeleted(postId) {
  posts.value = posts.value.filter(p => p.id !== postId)
}

function onLikeUpdated({ postId, is_liked, like_count }) {
  const post = posts.value.find(p => p.id === postId)
  if (post) {
    post.is_liked = is_liked
    post.like_count = like_count
  }
}

function openEditModal() {
  editForm.value = {
    name: group.value?.name || '',
    description: group.value?.description || '',
    is_public: group.value?.is_public ?? true,
  }
  editCoverFile.value = null
  editError.value = ''
  showEditModal.value = true
}

async function handleEditGroup() {
  if (!editForm.value.name.trim()) return
  editing.value = true
  editError.value = ''
  try {
    const formData = new FormData()
    formData.append('name', editForm.value.name)
    formData.append('description', editForm.value.description)
    formData.append('is_public', editForm.value.is_public)
    if (editCoverFile.value) {
      formData.append('cover_image', editCoverFile.value)
    }
    await groupApi.update(groupId.value, formData)
    showEditModal.value = false
    toast.success('小组信息已更新')
    await fetchGroup()
  } catch (e) {
    editError.value = e.response?.data?.message || '更新失败'
  } finally {
    editing.value = false
  }
}

async function handleManageMember(member, action) {
  try {
    await groupApi.manageMember(groupId.value, member.user_id, action)
    const msgs = {
      remove: '已移除成员',
      promote_admin: '已设为管理员',
      demote_admin: '已取消管理员',
    }
    toast.success(msgs[action] || '操作成功')
    await fetchGroup()
  } catch { /* ignore */ }
}

async function handleTransfer() {
  if (!transferSelectedId.value) return
  transferring.value = true
  try {
    await groupApi.transfer(groupId.value, { new_owner_id: transferSelectedId.value })
    showTransferModal.value = false
    transferSelectedId.value = null
    toast.success('已转让组长')
    await fetchGroup()
  } catch { /* ignore */ } finally {
    transferring.value = false
  }
}

async function handleDeleteGroup() {
  const ok = await confirm({
    title: '解散小组',
    message: '确定要解散该小组？此操作不可恢复。小组动态将被保留但不再归属于该小组。',
    confirmText: '解散',
    variant: 'danger',
  })
  if (!ok) return
  try {
    await groupApi.delete(groupId.value)
    toast.success('小组已解散')
    router.push('/groups')
  } catch { /* ignore */ }
}

function getRole(member) {
  if (member.user_id === group.value?.owner?.user_id) return '组长'
  if (member.role === 'admin') return '管理员'
  return '成员'
}

async function submitGroupPost() {
  if (!newPostContent.value.trim() || submittingPost.value) return
  submittingPost.value = true
  try {
    const formData = new FormData()
    formData.append('content', newPostContent.value.trim())
    formData.append('group_id', groupId.value)
    formData.append('sync_to_profile', syncToProfile.value)
    await postApi.create(formData)
    newPostContent.value = ''
    await fetchPosts(true)
    toast.success('已发布到小组')
  } catch { /* ignore */ } finally {
    submittingPost.value = false
  }
}
</script>

<template>
  <div v-if="loading" class="max-w-4xl mx-auto px-4 pb-8">
    <div class="skeleton h-48 w-full rounded-b-2xl"></div>
    <div class="px-4 -mt-8 relative z-10">
      <div class="card-base p-5 space-y-3">
        <div class="skeleton h-7 w-48"></div>
        <div class="skeleton h-4 w-full"></div>
        <div class="skeleton h-4 w-64"></div>
        <div class="skeleton h-10 w-28 rounded-lg"></div>
      </div>
    </div>
    <div class="px-4 mt-6">
      <div class="skeleton h-10 w-full rounded-xl"></div>
      <div class="mt-4 space-y-4">
        <div class="skeleton h-32 w-full rounded-2xl"></div>
        <div class="skeleton h-32 w-full rounded-2xl"></div>
      </div>
    </div>
  </div>

  <div v-else-if="group" class="max-w-4xl mx-auto px-4 pb-8">
    <div class="relative w-full rounded-b-2xl overflow-hidden h-48 bg-gradient-to-r from-maple-600 to-maple-400">
      <img v-if="group.cover_url" :src="group.cover_url" class="w-full h-full object-cover" />
    </div>

    <div class="px-4 -mt-8 relative z-10">
      <div class="card-base p-5">
        <div class="flex items-start justify-between">
          <div class="min-w-0 flex-1">
            <h1 class="text-xl font-bold text-text-primary">{{ group.name }}</h1>
            <p v-if="group.description" class="text-sm text-text-secondary mt-1 line-clamp-3">{{ group.description }}</p>
            <div class="flex items-center gap-4 mt-3 text-xs text-text-secondary">
              <span>创建者: {{ group.owner?.nickname }}</span>
              <span>{{ group.member_count || members.length }} 名成员</span>
              <span v-if="!group.is_public" class="px-1.5 py-0.5 bg-gray-100 rounded">私密</span>
            </div>
          </div>
          <div v-if="isOwner" class="flex items-center gap-2 ml-4">
            <button @click="openEditModal" class="p-2.5 text-text-secondary hover:text-maple-600 hover:bg-maple-50 rounded-lg transition-colors active:scale-[0.97] cursor-pointer" title="编辑小组">
              <Icon name="edit" :size="18" />
            </button>
            <button @click="showTransferModal = true" class="px-3 py-2 text-xs font-medium text-maple-600 border border-maple-600 rounded-lg hover:bg-maple-50 transition-colors active:scale-[0.97] cursor-pointer">
              转让组长
            </button>
            <button @click="handleDeleteGroup" class="px-3 py-2 text-xs font-medium text-red-500 border border-red-400 rounded-lg hover:bg-red-50 transition-colors active:scale-[0.97] cursor-pointer">
              解散小组
            </button>
          </div>
        </div>
        <div v-if="!isOwner && !hasPendingRequest" class="mt-4 flex items-center gap-3">
          <button
            @click="isMember ? handleLeave() : handleJoin()"
            :disabled="joining"
            class="flex-1"
            :class="isMember ? 'btn-secondary px-5' : 'btn-primary px-5'"
          >
            {{ joining ? '处理中...' : isMember ? '退出小组' : group.is_public ? '加入小组' : '申请加入' }}
          </button>
          <button
            v-if="isMember && group.chat_room_id"
            @click="router.push('/chat/' + group.chat_room_id)"
            class="btn-secondary px-5 flex-1 justify-center"
          >
            <Icon name="messageCircle" :size="16" /> 进入聊天室
          </button>
        </div>
        <button
          v-else-if="!isOwner && hasPendingRequest"
          disabled
          class="mt-4 px-5 py-2.5 text-sm rounded-lg bg-gray-200 text-text-secondary cursor-not-allowed"
        >
          已申请
        </button>
      </div>
    </div>

    <div class="px-4 mt-6">
      <TabBar
        :tabs="[{ key: 'posts', label: '动态' }, { key: 'members', label: '成员' }]"
        :activeKey="activeTab"
        @update:activeKey="activeTab = $event"
      />

      <div v-if="activeTab === 'posts'" class="mt-4 space-y-4">
        <div v-if="!isMember" class="text-center text-text-secondary py-8">
          加入小组后即可查看组内动态
        </div>
        <template v-else>
          <div class="card-base p-4">
            <textarea
              v-model="newPostContent"
              rows="3"
              placeholder="分享到小组..."
              class="input-base resize-none rounded-xl"
            />
            <div class="flex items-center justify-between mt-2">
              <label class="flex items-center gap-2 text-xs text-text-secondary w-fit cursor-pointer select-none">
                <ToggleSwitch v-model="syncToProfile" />
                <span>同步到个人主页</span>
              </label>
              <button
                @click="submitGroupPost"
                :disabled="submittingPost || !newPostContent.trim()"
                class="btn-primary px-5"
              >
                {{ submittingPost ? '发布中...' : '发布' }}
              </button>
            </div>
          </div>

          <div v-if="!posts.length" class="text-center py-12 text-text-secondary">
            <Icon name="fileText" :size="40" class="mx-auto mb-2 text-maple-300" />
            <p>暂无动态</p>
          </div>
          <PostCard v-for="post in posts" :key="post.id" :post="post" :showActions="true" @deleted="onPostDeleted" @like-updated="onLikeUpdated" />
          <button
            v-if="hasMorePosts"
            @click="fetchPosts(false)"
            :disabled="loadingPosts"
            class="w-full text-center text-sm text-maple-600 hover:text-maple-700 py-3 transition-colors active:scale-[0.97] cursor-pointer"
          >
            {{ loadingPosts ? '加载中...' : '加载更多动态' }}
          </button>
        </template>
      </div>

      <div v-if="activeTab === 'members'" class="mt-4">
        <div v-if="canManageRequests" class="flex gap-4 mb-4 border-b border-border">
          <button
            @click="memberSubTab = 'list'"
            class="px-3 py-2 text-sm font-medium transition-colors active:scale-[0.97] cursor-pointer"
            :class="memberSubTab === 'list' ? 'text-maple-600 border-b-2 border-maple-600' : 'text-text-secondary hover:text-text-primary'"
          >
            成员列表
          </button>
          <button
            @click="memberSubTab = 'requests'"
            class="px-3 py-2 text-sm font-medium transition-colors active:scale-[0.97] cursor-pointer"
            :class="memberSubTab === 'requests' ? 'text-maple-600 border-b-2 border-maple-600' : 'text-text-secondary hover:text-text-primary'"
          >
            加入申请
          </button>
        </div>

        <div v-if="memberSubTab === 'list'" class="space-y-3">
          <div v-for="m in members" :key="m.user_id" class="flex items-center gap-3 py-2">
            <AvatarImage :user="m" size="md" />
            <div class="flex-1 min-w-0">
              <span class="text-sm font-medium text-text-primary">{{ m.nickname }}</span>
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="getRole(m) === '组长' ? 'bg-maple-100 text-maple-600' : getRole(m) === '管理员' ? 'bg-amber-50 text-amber-600' : 'bg-gray-100 text-text-secondary'">
              {{ getRole(m) }}
            </span>
            <div v-if="m.user_id !== authStore.user?.user_id" class="flex items-center gap-1">
              <template v-if="isOwner">
                <button
                  v-if="m.role === 'member' || (!m.role && m.user_id !== group.owner?.user_id)"
                  @click="handleManageMember(m, 'promote_admin')"
                  class="px-2.5 py-2 text-xs text-maple-600 hover:bg-maple-50 rounded-md transition-colors active:scale-[0.97] cursor-pointer"
                >
                  设为管理员
                </button>
                <button
                  v-if="m.role === 'admin'"
                  @click="handleManageMember(m, 'demote_admin')"
                  class="px-2.5 py-2 text-xs text-amber-600 hover:bg-amber-50 rounded-md transition-colors active:scale-[0.97] cursor-pointer"
                >
                  取消管理员
                </button>
                <button
                  @click="handleManageMember(m, 'remove')"
                  class="px-2.5 py-2 text-xs text-red-500 hover:bg-red-50 rounded-md transition-colors active:scale-[0.97] cursor-pointer"
                >
                  移除成员
                </button>
              </template>
              <template v-else-if="isAdmin && m.role !== 'admin' && m.user_id !== group.owner?.user_id">
                <button
                  @click="handleManageMember(m, 'remove')"
                  class="px-2.5 py-2 text-xs text-red-500 hover:bg-red-50 rounded-md transition-colors active:scale-[0.97] cursor-pointer"
                >
                  移除成员
                </button>
              </template>
            </div>
          </div>
          <div v-if="!members.length" class="text-center py-12 text-text-secondary">
            <Icon name="users" :size="40" class="mx-auto mb-2 text-maple-300" />
            <p>暂无成员</p>
          </div>
        </div>

        <div v-else class="space-y-3">
          <div v-if="loadingJoinRequests" class="text-center text-text-secondary py-8">加载中...</div>
          <div v-else-if="!joinRequestsList.length" class="text-center py-12 text-text-secondary">
            <Icon name="mail" :size="40" class="mx-auto mb-2 text-maple-300" />
            <p>暂无待处理的申请</p>
          </div>
          <div v-for="req in joinRequestsList" :key="req.id" class="flex items-center gap-3 py-2">
            <AvatarImage :user="req.applicant" size="md" />
            <div class="flex-1 min-w-0">
              <span class="text-sm font-medium text-text-primary">{{ req.applicant?.nickname }}</span>
              <p class="text-xs text-text-secondary">{{ relativeTime(req.created_at) }}</p>
            </div>
            <button
              @click="handleRequestAction(req, 'approved')"
              :disabled="handlingRequestId === req.id"
              class="px-3 py-2 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors active:scale-[0.97] disabled:active:scale-100 disabled:opacity-50 cursor-pointer"
            >
              {{ handlingRequestId === req.id ? '处理中...' : '同意' }}
            </button>
            <button
              @click="handleRequestAction(req, 'rejected')"
              :disabled="handlingRequestId === req.id"
              class="px-3 py-2 text-xs font-medium text-red-600 border border-red-400 rounded-lg hover:bg-red-50 transition-colors active:scale-[0.97] disabled:active:scale-100 disabled:opacity-50 cursor-pointer"
            >
              {{ handlingRequestId === req.id ? '处理中...' : '拒绝' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <BottomSheet :show="showEditModal" title="编辑小组" @close="showEditModal = false">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">名称</label>
          <input
            v-model="editForm.name"
            type="text"
            placeholder="输入小组名称"
            class="input-base"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">简介</label>
          <textarea
            v-model="editForm.description"
            rows="3"
            placeholder="小组简介（可选）"
            class="input-base resize-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-text-primary mb-1">封面图（可选）</label>
          <label class="flex items-center gap-2 px-3 py-2.5 border border-border rounded-lg text-sm text-text-secondary cursor-pointer hover:bg-maple-50 transition-colors">
            <input type="file" accept="image/*" @change="e => editCoverFile = e.target.files[0] || null" class="hidden" />
            <span>{{ editCoverFile ? editCoverFile.name : '选择封面图片' }}</span>
          </label>
        </div>
        <label class="flex items-center justify-between w-full cursor-pointer select-none">
          <span class="text-sm text-text-primary">公开小组（任何人都可加入）</span>
          <ToggleSwitch v-model="editForm.is_public" />
        </label>
      </div>
      <p v-if="editError" class="text-red-500 text-sm mt-2">{{ editError }}</p>
      <div class="flex gap-3 mt-6 justify-end">
        <button
          @click="showEditModal = false"
          class="btn-ghost"
        >
          取消
        </button>
        <button
          @click="handleEditGroup"
          :disabled="editing || !editForm.name.trim()"
          class="btn-primary px-5"
        >
          {{ editing ? '保存中...' : '保存' }}
        </button>
      </div>
    </BottomSheet>

    <BottomSheet :show="showTransferModal" title="转让组长" @close="showTransferModal = false">
      <p class="text-sm text-text-secondary mb-4">选择新的组长：</p>
      <SelectField
        v-model="transferSelectedId"
        :options="[{ value: null, label: '请选择成员' }, ...members.filter(m => m.user_id !== group.owner?.user_id).map(m => ({ value: m.user_id, label: m.nickname }))]"
      />
      <div class="flex gap-3 mt-6 justify-end">
        <button
          @click="showTransferModal = false"
          class="btn-ghost"
        >
          取消
        </button>
        <button
          @click="handleTransfer"
          :disabled="transferring || !transferSelectedId"
          class="btn-primary px-5"
        >
          {{ transferring ? '转让中...' : '确认转让' }}
        </button>
      </div>
    </BottomSheet>
  </div>

  <div v-else class="max-w-4xl mx-auto px-4 py-16 text-center text-text-secondary">
    <Icon name="alertCircle" :size="48" class="mx-auto mb-3 text-maple-300" />
    <p>小组不存在</p>
  </div>
</template>
