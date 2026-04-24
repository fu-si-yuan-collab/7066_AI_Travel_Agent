import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const authApi = {
  register: (email: string, password: string, nickname: string) =>
    api.post('/users/register', { email, password, nickname }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/users/login', { email, password }),
}

export const chatApi = {
  send: (message: string, thread_id?: string) =>
    api.post<{ reply: string; thread_id: string; trip_plan: unknown }>('/chat', { message, thread_id }),
}

export const tripsApi = {
  list: () => api.get('/trips'),
}

export const prefsApi = {
  get: () => api.get('/preferences'),
  update: (data: Partial<{ preferred_travel_style: string; preferred_transport: string; preferred_hotel_stars: number; preferred_cuisine: string; daily_budget_low: number; daily_budget_high: number; currency: string }>) =>
    api.put('/preferences', data),
}

export default api
