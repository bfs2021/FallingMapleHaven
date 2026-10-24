import { pluginRegistry } from '../registry'
import AdminRelationMatchPage from '@/views/admin/AdminRelationMatchPage.vue'

pluginRegistry.register({
  type: 'relation_match',
  name: '关系匹配',
  icon: 'heartHandshake',
  route: { path: '/profile/:userId/plugins/relation-match', name: 'RelationMatchPage' },
  adminRoute: { path: 'relation-match', name: 'AdminRelationMatch', component: AdminRelationMatchPage },
  adminSidebar: { name: '关系匹配管理', icon: 'puzzle' },
})
