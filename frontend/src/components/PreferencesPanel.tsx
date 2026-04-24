import { useEffect, useState } from 'react'
import { prefsApi } from '../api'
import { useStore } from '../store'
import toast from 'react-hot-toast'
import { Brain, Save, Sliders } from 'lucide-react'
import type { UserPreference } from '../types'

const STYLES = ['budget', 'balanced', 'luxury']
const TRANSPORTS = ['any', 'flight', 'train', 'driving']
const CUISINES = ['Chinese', 'Japanese', 'Italian', 'Thai', 'Local', 'Vegetarian']

export default function PreferencesPanel() {
  const { preferences, setPreferences } = useStore()
  const [form, setForm] = useState<Partial<UserPreference>>({
    preferred_travel_style: 'balanced',
    preferred_transport: 'any',
    preferred_hotel_stars: 3,
    preferred_cuisine: '',
    daily_budget_low: 300,
    daily_budget_high: 1000,
    currency: 'CNY',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    prefsApi.get().then((r) => {
      if (r.data) { setPreferences(r.data); setForm(r.data) }
    }).catch(() => {})
  }, [setPreferences])

  useEffect(() => {
    if (preferences) setForm(preferences)
  }, [preferences])

  const save = async () => {
    setSaving(true)
    try {
      const r = await prefsApi.update(form as Parameters<typeof prefsApi.update>[0])
      setPreferences(r.data)
      toast.success('Preferences saved!')
    } catch {
      toast.error('Failed to save preferences')
    } finally {
      setSaving(false)
    }
  }

  const learnedTags = preferences?.learned_tags ?? {}

  return (
    <div className="h-full overflow-y-auto scrollbar-hide p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-1">Travel Preferences</h2>
        <p className="text-sm text-gray-500">The AI learns from your choices to personalise every trip</p>
      </div>

      {/* AI Memory card */}
      {Object.keys(learnedTags).length > 0 && (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-2xl p-5 border border-purple-100 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-purple-500" />
            <span className="font-semibold text-purple-800 text-sm">AI Memory</span>
            <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">Learned from your trips</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(learnedTags).map(([tag, score]) => (
              <div key={tag} className="flex items-center gap-1.5 bg-white rounded-lg px-3 py-1.5 shadow-sm border border-purple-100">
                <span className="text-xs font-medium text-gray-700">{tag}</span>
                <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-400 rounded-full" style={{ width: `${(score as number) * 100}%` }} />
                </div>
                <span className="text-xs text-gray-400">{Math.round((score as number) * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-5">
        {/* Travel style */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <Sliders className="w-4 h-4 text-blue-500" />
            <h3 className="font-semibold text-gray-900 text-sm">Travel Style</h3>
          </div>
          <div className="flex gap-2">
            {STYLES.map((s) => (
              <button key={s} onClick={() => setForm((f) => ({ ...f, preferred_travel_style: s }))}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium capitalize transition-all ${form.preferred_travel_style === s ? 'gradient-bg text-white shadow-md' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}>
                {s === 'budget' ? '💰 Budget' : s === 'balanced' ? '⚖️ Balanced' : '✨ Luxury'}
              </button>
            ))}
          </div>
        </div>

        {/* Transport */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 text-sm mb-4">Preferred Transport</h3>
          <div className="flex flex-wrap gap-2">
            {TRANSPORTS.map((t) => (
              <button key={t} onClick={() => setForm((f) => ({ ...f, preferred_transport: t }))}
                className={`px-4 py-2 rounded-xl text-sm font-medium capitalize transition-all ${form.preferred_transport === t ? 'gradient-bg text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}>
                {t === 'flight' ? '✈️ Flight' : t === 'train' ? '🚄 Train' : t === 'driving' ? '🚗 Drive' : '🌐 Any'}
              </button>
            ))}
          </div>
        </div>

        {/* Hotel stars */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 text-sm mb-4">Hotel Stars: {form.preferred_hotel_stars}★</h3>
          <input type="range" min={1} max={5} step={0.5} value={form.preferred_hotel_stars ?? 3}
            onChange={(e) => setForm((f) => ({ ...f, preferred_hotel_stars: +e.target.value }))}
            className="w-full accent-blue-500" />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1★ Budget</span><span>3★ Standard</span><span>5★ Luxury</span>
          </div>
        </div>

        {/* Budget */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 text-sm mb-4">Daily Budget (CNY)</h3>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">Min</label>
              <input type="number" value={form.daily_budget_low ?? 300}
                onChange={(e) => setForm((f) => ({ ...f, daily_budget_low: +e.target.value }))}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">Max</label>
              <input type="number" value={form.daily_budget_high ?? 1000}
                onChange={(e) => setForm((f) => ({ ...f, daily_budget_high: +e.target.value }))}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
        </div>

        {/* Cuisine */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-900 text-sm mb-4">Favourite Cuisine</h3>
          <div className="flex flex-wrap gap-2">
            {CUISINES.map((c) => {
              const selected = (form.preferred_cuisine ?? '').includes(c)
              return (
                <button key={c} onClick={() => setForm((f) => {
                  const current = (f.preferred_cuisine ?? '').split(',').filter(Boolean)
                  const next = selected ? current.filter((x) => x !== c) : [...current, c]
                  return { ...f, preferred_cuisine: next.join(',') }
                })}
                  className={`px-3 py-1.5 rounded-xl text-sm transition-all ${selected ? 'gradient-bg text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}>
                  {c}
                </button>
              )
            })}
          </div>
        </div>

        <button onClick={save} disabled={saving}
          className="w-full py-3 rounded-xl gradient-bg text-white font-semibold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-60 shadow-md">
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  )
}
