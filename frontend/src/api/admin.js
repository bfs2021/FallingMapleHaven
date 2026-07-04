import client from './client'

export const adminApi = {
  users: (params) => client.get('/admin/users/', { params }),
  updateUser: (id, data) => client.patch(`/admin/users/${id}/`, data),
  posts: () => client.get('/admin/posts/'),
  deletePost: (id) => client.delete(`/admin/posts/${id}/`),
  comments: () => client.get('/admin/comments/'),
  deleteComment: (id) => client.delete(`/admin/comments/${id}/`),
  anonymousQuestions: () => client.get('/admin/anonymous-questions/'),
  plugins: () => client.get('/admin/plugins/'),
  updatePlugin: (id, data) => client.patch(`/admin/plugins/${id}/`, data),
  settings: () => client.get('/admin/settings/'),
  updateSettings: (settings) => client.patch('/admin/settings/', { settings }),
  stats: () => client.get('/admin/stats/'),
  groups: () => client.get('/admin/groups/'),
  deleteGroup: (id) => client.delete(`/admin/groups/${id}/`),
  groupPosts: (id) => client.get(`/admin/groups/${id}/posts/`),
  logs: (params = {}) => client.get('/admin/logs/', { params }),
  logActions: () => client.get('/admin/logs/actions/'),
  trends: (days = 7) => client.get('/admin/trends/', { params: { days } }),
}
