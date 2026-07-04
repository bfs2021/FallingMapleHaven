import client from './client'

export const pluginApi = {
  getSummary: () => client.get('/plugins/summary/'),
  getProfileCards: (userId) => client.get(`/plugins/profile-cards/${userId}/`),
  getQuizLeaderboard: () => client.get('/plugins/quiz/leaderboard/'),
}

export const quizApi = {
  create: (data) => client.post('/plugins/quiz/questions/', data),
  received: () => client.get('/plugins/quiz/questions/received/'),
  answer: (id, answer) => client.post(`/plugins/quiz/questions/${id}/answer/`, { answer }),
  result: (friendId) => client.get(`/plugins/quiz/result/${friendId}/`),
}

export const questionBoxApi = {
  ask: (data) => client.post('/plugins/question-box/', data),
  inbox: () => client.get('/plugins/question-box/inbox/'),
  answer: (id, answer) => client.post(`/plugins/question-box/${id}/answer/`, { answer }),
  delete: (id) => client.delete(`/plugins/question-box/${id}/delete/`),
}

export const groupApi = {
  list: () => client.get('/groups/'),
  detail: (id) => client.get(`/groups/${id}/`),
  create: (data) => client.post('/groups/create/', data, {
    headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {},
  }),
  update: (id, data) => client.patch(`/groups/${id}/update/`, data, {
    headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {},
  }),
  join: (id) => client.post(`/groups/${id}/join/`),
  leave: (id) => client.post(`/groups/${id}/leave/`),
  manageMember: (id, userId, action) => client.post(`/groups/${id}/members/${userId}/`, { action }),
  posts: (id, params) => client.get(`/groups/${id}/posts/`, { params }),
  delete: (id) => client.post(`/groups/${id}/delete/`),
  transfer: (id, data) => client.post(`/groups/${id}/transfer/`, data),
  joinRequests: (id) => client.get(`/groups/${id}/join-requests/`),
  handleJoinRequest: (id, requestId, action) => client.post(`/groups/${id}/join-requests/${requestId}/handle/`, { action }),
}
