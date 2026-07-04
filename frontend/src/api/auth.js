import client from './client'

export const authApi = {
  register: (data) => client.post('/auth/register/', data),
  login: (data) => client.post('/auth/login/', data),
  logout: () => client.post('/auth/logout/'),
  me: () => client.get('/auth/me/'),
  updateMe: (data) => client.patch('/auth/me/', data),
  changePassword: (data) => client.post('/auth/change-password/', data),
  uploadAvatar: (file) => {
    const fd = new FormData()
    fd.append('avatar', file)
    return client.post('/auth/avatar/', fd)
  },
  uploadCover: (file) => {
    const fd = new FormData()
    fd.append('cover_image', file)
    return client.post('/auth/cover/', fd)
  },
}
