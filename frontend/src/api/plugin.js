import client from './client'

export const pluginApi = {
  getSummary: () => client.get('/plugins/summary/'),
  getProfileCards: (userId) => client.get(`/plugins/profile-cards/${userId}/`),
}

export const quizApi = {
  publicTests: (ownerId, params) => client.get(`/plugins/quiz/users/${ownerId}/tests/`, { params }),
  myTests: (params) => client.get('/plugins/quiz/my/tests/', { params }),
  createTest: (data) => client.post('/plugins/quiz/my/tests/', data),
  myTestDetail: (testId) => client.get(`/plugins/quiz/my/tests/${testId}/`),
  updateDraftTest: (testId, data) => client.patch(`/plugins/quiz/my/tests/${testId}/`, data),
  publishTest: (testId) => client.post(`/plugins/quiz/my/tests/${testId}/publish/`, {}),
  deleteTest: (testId) => client.delete(`/plugins/quiz/my/tests/${testId}/`),
  publicTestDetail: (testId) => client.get(`/plugins/quiz/tests/${testId}/`),
  submitTest: (testId, data) => client.post(`/plugins/quiz/tests/${testId}/submissions/`, data),
  leaderboard: (testId, params) => client.get(`/plugins/quiz/tests/${testId}/leaderboard/`, { params }),
  mySubmissions: (params) => client.get('/plugins/quiz/my/submissions/', { params }),
  questionBank: (params) => client.get('/plugins/quiz/question-bank/', { params }),
}

export const relationMatchApi = {
  getHome: (ownerId) => client.get(`/plugins/relation-match/users/${ownerId}/`),
  getTestDetail: () => client.get('/plugins/relation-match/tests/current/'),
  submitTest: (data) => client.post('/plugins/relation-match/tests/current/submissions/', data),
  matchProfile: (shareCode, data) => client.post(`/plugins/relation-match/shares/${shareCode}/match/`, data),
  getPairResult: (pairId) => client.get(`/plugins/relation-match/pairs/${pairId}/`),
  myPairs: (params) => client.get('/plugins/relation-match/my/pairs/', { params }),
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
