import { MessageSquare, Map, Hotel, Settings, LogOut, Plane, Compass } from 'lucide-react'
import { useStore } from '../store'

const navItems = [
  { id: 'chat', icon: MessageSquare, label: 'AI Chat' },
  { id: 'trips', icon: Map, label: 'My Trips' },
  { id: 'hotels', icon: Hotel, label: 'Hotels' },
  { id: 'preferences', icon: Settings, label: 'Preferences' },
] as const

export default function Sidebar() {
  const { activeTab, setActiveTab, auth, logout } = useStore()

  return (
    <aside className="w-64 min-h-screen flex flex-col bg-white border-r border-gray-100 shadow-sm">
      {/* Logo */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center">
            <Plane className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-gray-900 text-sm">AI Travel Agent</div>
            <div className="text-xs text-gray-400">Your concierge</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === id
                ? 'gradient-bg text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}>
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </nav>

      {/* Inspiration shortcut */}
      <div className="p-4">
        <div className="rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 p-4 border border-blue-100">
          <div className="flex items-center gap-2 mb-2">
            <Compass className="w-4 h-4 text-blue-500" />
            <span className="text-xs font-semibold text-blue-700">Explore Ideas</span>
          </div>
          <p className="text-xs text-gray-500">Discover trending destinations</p>
        </div>
      </div>

      {/* User */}
      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold">
            {auth.user?.nickname?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 truncate">{auth.user?.nickname}</div>
            <div className="text-xs text-gray-400 truncate">{auth.user?.email}</div>
          </div>
          <button onClick={logout} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-red-500 transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
