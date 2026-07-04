import { pluginRegistry } from '../registry'
import AdminQuizPage from '@/views/admin/AdminQuizPage.vue'

pluginRegistry.register({
  type: 'quiz',
  name: '默契问答',
  icon: 'help-circle',
  route: { path: '/profile/:userId/plugins/quiz', name: 'QuizPage' },
  adminRoute: { path: 'quiz', name: 'AdminQuiz', component: AdminQuizPage },
  adminSidebar: { name: '问答管理', icon: 'puzzle' },
})
