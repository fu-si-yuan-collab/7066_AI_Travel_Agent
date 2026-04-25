import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Message, UserPreference, AuthState } from '../types'

interface AppStore {
  // Auth
  auth: AuthState
  setAuth: (auth: AuthState) => void
  logout: () => void

  // Chat
  messages: Message[]
  threadId: string | null
  isLoading: boolean
  addMessage: (msg: Message) => void
  updateMessage: (id: string, patch: Partial<Message>) => void
  setLoading: (v: boolean) => void
  setThreadId: (id: string) => void
  clearChat: () => void

  // Preferences
  preferences: UserPreference | null
  setPreferences: (p: UserPreference) => void

  // Active tab
  activeTab: 'chat' | 'trips' | 'hotels' | 'preferences' | 'docs'
  setActiveTab: (t: AppStore['activeTab']) => void
}

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      auth: { token: null, user: null },
      setAuth: (auth) => {
        localStorage.setItem('token', auth.token ?? '')
        set({ auth })
      },
      logout: () => {
        localStorage.removeItem('token')
        set({ auth: { token: null, user: null }, messages: [], threadId: null })
      },

      messages: [],
      threadId: null,
      isLoading: false,
      addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
      updateMessage: (id, patch) => set((s) => ({
        messages: s.messages.map((m) => m.id === id ? { ...m, ...patch } : m),
      })),
      setLoading: (v) => set({ isLoading: v }),
      setThreadId: (id) => set({ threadId: id }),
      clearChat: () => set({ messages: [], threadId: null }),

      preferences: null,
      setPreferences: (p) => set({ preferences: p }),

      activeTab: 'chat',
      setActiveTab: (t) => set({ activeTab: t }),
    }),
    { name: 'travel-agent-store', partialize: (s) => ({ auth: s.auth }) }
  )
)
