import { Toaster } from 'react-hot-toast'
import { useStore } from './store'
import AuthPage from './components/AuthPage'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import TripsPanel from './components/TripsPanel'
import HotelsPanel from './components/HotelsPanel'
import PreferencesPanel from './components/PreferencesPanel'
import RightPanel from './components/RightPanel'

function MainContent() {
  const activeTab = useStore((s) => s.activeTab)
  return (
    <div className="flex-1 overflow-hidden">
      {activeTab === 'chat' && <ChatPanel />}
      {activeTab === 'trips' && <TripsPanel />}
      {activeTab === 'hotels' && <HotelsPanel />}
      {activeTab === 'preferences' && <PreferencesPanel />}
    </div>
  )
}

export default function App() {
  const token = useStore((s) => s.auth.token)

  if (!token) return (
    <>
      <AuthPage />
      <Toaster position="top-right" />
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <MainContent />
      <RightPanel />
      <Toaster position="top-right" toastOptions={{ className: 'text-sm' }} />
    </div>
  )
}
