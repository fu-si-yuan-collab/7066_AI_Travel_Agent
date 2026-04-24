import { useState } from 'react'
import { authApi } from '../api'
import { useStore } from '../store'
import toast from 'react-hot-toast'
import { Plane, Mail, Lock, User } from 'lucide-react'

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useStore((s) => s.setAuth)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'register') {
        await authApi.register(email, password, nickname)
        toast.success('Account created! Please log in.')
        setMode('login')
      } else {
        const res = await authApi.login(email, password)
        setAuth({ token: res.data.access_token, user: { email, nickname: nickname || email.split('@')[0], id: '' } })
        toast.success('Welcome back!')
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Something went wrong'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Gradient background */}
      <div className="absolute inset-0 gradient-bg opacity-90" />
      <div className="absolute inset-0" style={{ backgroundImage: 'url(https://images.unsplash.com/photo-1488085061387-422e29b40080?w=1600&q=80)', backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.15 }} />

      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/20 backdrop-blur mb-4">
            <Plane className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">AI Travel Agent</h1>
          <p className="text-white/70 mt-1">Your personal travel concierge</p>
        </div>

        {/* Card */}
        <div className="glass rounded-2xl shadow-2xl p-8">
          <div className="flex rounded-xl bg-gray-100 p-1 mb-6">
            {(['login', 'register'] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${mode === m ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}>
                {m === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && (
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input value={nickname} onChange={(e) => setNickname(e.target.value)}
                  placeholder="Nickname" className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm" />
              </div>
            )}
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                placeholder="Email" className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm" />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                placeholder="Password" className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl gradient-bg text-white font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-60">
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
