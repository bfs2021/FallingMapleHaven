import { pluginRegistry } from '../registry'
import AdminAnonymousQuestions from '@/views/admin/AdminAnonymousQuestionsPage.vue'

pluginRegistry.register({
  type: 'question_box',
  name: '匿名提问箱',
  icon: 'message-question',
  route: { path: '/profile/:userId/plugins/question-box', name: 'QuestionBoxPage' },
  adminRoute: { path: 'anonymous-questions', name: 'AdminAnonymousQuestions', component: AdminAnonymousQuestions },
  adminSidebar: { name: '提问箱管理', icon: 'helpCircle' },
})
