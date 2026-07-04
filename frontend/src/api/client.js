import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

let csrfPromise = null

function getCookie(name) {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

function isUnsafeMethod(method = 'get') {
  return ['post', 'put', 'patch', 'delete'].includes(method.toLowerCase())
}

async function ensureCsrfToken() {
  if (getCookie('csrftoken')) return
  if (!csrfPromise) {
    csrfPromise = axios.get('/api/v1/auth/csrf/', { withCredentials: true })
      .finally(() => { csrfPromise = null })
  }
  await csrfPromise
}

client.interceptors.request.use(async (config) => {
  if (isUnsafeMethod(config.method)) {
    await ensureCsrfToken()
  }
  const csrf = getCookie('csrftoken')
  if (csrf) {
    config.headers['X-CSRFToken'] = csrf
  }
  return config
})

client.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      const { useAuthStore } = await import('@/stores/auth')
      const authStore = useAuthStore()
      authStore.logout().catch(() => {})
    }
    return Promise.reject(error)
  }
)

export default client
