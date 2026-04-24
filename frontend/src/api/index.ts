import axios from 'axios'

// In production (Vercel), VITE_API_BASE_URL points to the Railway backend.
// In local dev, it falls back to '/api/v1' which is proxied by Vite to localhost:8000.
const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const api = axios.create({
  baseURL,
  headers: {
    // Bypass ngrok browser warning page when using ngrok tunnel
    'ngrok-skip-browser-warning': 'true',
  },
})

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
  create: (data: {
    destination: string; start_date?: string; end_date?: string
    budget?: number; currency?: string; travel_style?: string
  }) => api.post('/trips', data),
}

export const prefsApi = {
  get: () => api.get('/preferences'),
  update: (data: Partial<{ preferred_travel_style: string; preferred_transport: string; preferred_hotel_stars: number; preferred_cuisine: string; daily_budget_low: number; daily_budget_high: number; currency: string }>) =>
    api.put('/preferences', data),
}

export default api
