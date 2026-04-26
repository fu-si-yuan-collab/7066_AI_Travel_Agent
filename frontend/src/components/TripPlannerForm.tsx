import { useState, useEffect } from 'react'
import { MapPin, Calendar, Wallet, Heart, Hotel, Navigation, ChevronRight, Sparkles } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────
interface TripFormData {
  destination: string
  origin: string
  departDate: string
  returnDate: string
  travelers: string
  totalBudget: string
  travelStyle: 'budget' | 'balanced' | 'luxury'
  interests: string[]
  hotelArea: string
  hotelStars: string
  specialRequests: string
}

const INTEREST_OPTIONS = [
  { id: 'food', label: '🍜 Local Food', sub: 'Street food, restaurants' },
  { id: 'culture', label: '🏛️ Culture', sub: 'Temples, museums, history' },
  { id: 'nature', label: '🌿 Nature', sub: 'Parks, hiking, scenery' },
  { id: 'shopping', label: '🛍️ Shopping', sub: 'Markets, malls, souvenirs' },
  { id: 'nightlife', label: '🌃 Nightlife', sub: 'Bars, clubs, night markets' },
  { id: 'art', label: '🎨 Art & Design', sub: 'Galleries, installations' },
  { id: 'adventure', label: '🧗 Adventure', sub: 'Sports, outdoor activities' },
  { id: 'wellness', label: '🧘 Wellness', sub: 'Spa, yoga, relaxation' },
]

const STYLE_OPTIONS = [
  { id: 'budget', label: '💰 Budget', desc: 'Hostels, street food, free attractions' },
  { id: 'balanced', label: '⚖️ Balanced', desc: '3-4 star hotels, mix of dining' },
  { id: 'luxury', label: '✨ Luxury', desc: '5-star hotels, fine dining' },
] as const

// ─── Build structured prompt from form data ───────────────────────────────────
function buildPrompt(f: TripFormData): string {
  const nights = f.departDate && f.returnDate
    ? Math.max(1, Math.round((new Date(f.returnDate).getTime() - new Date(f.departDate).getTime()) / 86400000))
    : '?'

  const interestLabels = INTEREST_OPTIONS
    .filter(o => f.interests.includes(o.id))
    .map(o => o.label.replace(/^[^\s]+\s/, ''))  // strip emoji
    .join(', ')

  return `I'm planning a trip with the following details:

- Destination: ${f.destination}
- Departure city: ${f.origin || 'not specified'}
- Travel dates: ${f.departDate} → ${f.returnDate} (${nights} nights)
- Travelers: ${f.travelers} people
- Total budget: ¥${f.totalBudget} CNY (¥${Math.round(Number(f.totalBudget) / Number(f.travelers))} per person)
- Travel style: ${f.travelStyle}
- Interests: ${interestLabels || 'general sightseeing'}
- Hotel preference: ${f.hotelArea ? f.hotelArea + ' area, ' : ''}${f.hotelStars}-star
${f.specialRequests ? `- Special requests: ${f.specialRequests}` : ''}

Please provide:
1. Complete day-by-day itinerary with timed schedule
2. Hotel recommendations with multi-platform price comparison
3. Transport routes between attractions with exact lines and fares
4. Weather forecast and packing tips
5. Full budget breakdown (flights / hotel / meals / activities / transport)`
}

// ─── TripPlannerForm ──────────────────────────────────────────────────────────
interface Props {
  onSubmit: (prompt: string) => void
  isLoading: boolean
}

export default function TripPlannerForm({ onSubmit, isLoading }: Props) {
  const [step, setStep] = useState(0)  // 0=destination, 1=dates&people, 2=style, 3=interests, 4=details
  const [form, setForm] = useState<TripFormData>({
    destination: '', origin: '', departDate: '', returnDate: '',
    travelers: '2', totalBudget: '', travelStyle: 'balanced',
    interests: [], hotelArea: '', hotelStars: '3', specialRequests: '',
  })

  const set = (k: keyof TripFormData, v: string | string[]) =>
    setForm(f => ({ ...f, [k]: v }))

  // Auto-detect user location to pre-fill origin field
  useEffect(() => {
    if (!form.origin && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&format=json&accept-language=zh`
          )
          const data = await res.json()
          const city = data.address?.city || data.address?.town || data.address?.county || ''
          if (city) set('origin', city)
        } catch { /* silent fail */ }
      }, () => { /* permission denied – silent fail */ })
    }
  }, [])

  const toggleInterest = (id: string) =>
    set('interests', form.interests.includes(id)
      ? form.interests.filter(i => i !== id)
      : [...form.interests, id])

  const canNext = [
    form.destination.trim().length > 0,
    !!(form.departDate && form.returnDate && form.travelers),
    true,
    form.interests.length > 0,
    form.totalBudget.trim().length > 0,
  ][step]

  const steps = ['Destination', 'Dates & People', 'Travel Style', 'Interests', 'Budget & Details']

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center mx-auto mb-3 shadow-lg">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Plan Your Trip</h2>
        <p className="text-sm text-gray-500 mt-1">Fill in the details for a precise AI-generated itinerary</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-1.5 mb-6">
        {steps.map((_s, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
              i < step ? 'gradient-bg text-white' :
              i === step ? 'bg-blue-100 text-blue-600 ring-2 ring-blue-400' :
              'bg-gray-100 text-gray-400'
            }`}>
              {i < step ? '✓' : i + 1}
            </div>
            {i < steps.length - 1 && <div className={`w-4 h-px ${i < step ? 'bg-blue-400' : 'bg-gray-200'}`} />}
          </div>
        ))}
      </div>

      {/* Form card */}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

        {/* Step 0: Destination */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <MapPin className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800">Where are you going?</h3>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1.5 block">Destination *</label>
              <input value={form.destination} onChange={e => set('destination', e.target.value)}
                placeholder="e.g. Tokyo, Japan / 东京 / Chiang Mai"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1.5 block">Departure city</label>
              <input value={form.origin} onChange={e => set('origin', e.target.value)}
                placeholder="e.g. Beijing / 北京 / Shanghai"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
        )}

        {/* Step 1: Dates & People */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800">When & who?</h3>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Departure date *</label>
                <input type="date" value={form.departDate} onChange={e => set('departDate', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Return date *</label>
                <input type="date" value={form.returnDate} onChange={e => set('returnDate', e.target.value)}
                  min={form.departDate}
                  className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1.5 block">Number of travellers *</label>
              <div className="flex gap-2">
                {['1', '2', '3', '4', '5+'].map(n => (
                  <button key={n} onClick={() => set('travelers', n === '5+' ? '5' : n)}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      form.travelers === (n === '5+' ? '5' : n)
                        ? 'gradient-bg text-white shadow-md' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                    }`}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Travel Style */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Hotel className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800">What's your travel style?</h3>
            </div>
            <div className="space-y-2">
              {STYLE_OPTIONS.map(s => (
                <button key={s.id} onClick={() => set('travelStyle', s.id)}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all text-left ${
                    form.travelStyle === s.id
                      ? 'border-blue-400 bg-blue-50' : 'border-gray-100 hover:border-gray-200 bg-white'
                  }`}>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-800">{s.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
                  </div>
                  {form.travelStyle === s.id && (
                    <div className="w-5 h-5 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xs">✓</span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Interests */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Heart className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800">What are you into? <span className="text-gray-400 font-normal text-xs">(pick at least 1)</span></h3>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {INTEREST_OPTIONS.map(o => {
                const selected = form.interests.includes(o.id)
                return (
                  <button key={o.id} onClick={() => toggleInterest(o.id)}
                    className={`p-3 rounded-xl border-2 text-left transition-all ${
                      selected ? 'border-blue-400 bg-blue-50' : 'border-gray-100 hover:border-gray-200 bg-white'
                    }`}>
                    <p className="text-sm font-medium text-gray-800">{o.label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{o.sub}</p>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Step 4: Budget & Details */}
        {step === 4 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Wallet className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-gray-800">Budget & preferences</h3>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1.5 block">
                Total budget (CNY ¥) * — for all {form.travelers} traveller(s)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">¥</span>
                <input type="number" value={form.totalBudget} onChange={e => set('totalBudget', e.target.value)}
                  placeholder="e.g. 10000"
                  className="w-full border border-gray-200 rounded-xl pl-8 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              {form.totalBudget && Number(form.totalBudget) > 0 && (
                <p className="text-xs text-blue-500 mt-1">
                  = ¥{Math.round(Number(form.totalBudget) / Number(form.travelers)).toLocaleString()} per person
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Hotel area</label>
                <input value={form.hotelArea} onChange={e => set('hotelArea', e.target.value)}
                  placeholder="e.g. Shinjuku / 古城区"
                  className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Hotel stars</label>
                <div className="flex gap-1">
                  {['2', '3', '4', '5'].map(s => (
                    <button key={s} onClick={() => set('hotelStars', s)}
                      className={`flex-1 py-2.5 rounded-xl text-xs font-medium transition-all ${
                        form.hotelStars === s ? 'gradient-bg text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                      }`}>
                      {s}★
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1.5 block">Special requests <span className="text-gray-400">(optional)</span></label>
              <textarea value={form.specialRequests} onChange={e => set('specialRequests', e.target.value)}
                placeholder="e.g. vegetarian meals, wheelchair accessible, travelling with kids..."
                rows={2}
                className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none" />
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex gap-3 mt-6">
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)}
              className="flex-1 py-3 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium hover:bg-gray-200 transition-colors">
              Back
            </button>
          )}
          {step < steps.length - 1 ? (
            <button onClick={() => setStep(s => s + 1)} disabled={!canNext}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl gradient-bg text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 shadow-md">
              Next <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button onClick={() => onSubmit(buildPrompt(form))} disabled={!canNext || isLoading}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl gradient-bg text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 shadow-md">
              <Navigation className="w-4 h-4" />
              {isLoading ? 'Planning...' : 'Generate My Trip'}
            </button>
          )}
        </div>
      </div>

      {/* Skip link */}
      <button onClick={() => onSubmit('')}
        className="mt-4 text-xs text-gray-400 hover:text-gray-600 transition-colors underline underline-offset-2">
        Skip form — type freely instead
      </button>
    </div>
  )
}
