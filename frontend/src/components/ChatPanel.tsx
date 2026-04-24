import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Sparkles, RotateCcw, MapPin, Calendar, Users, Wallet,
  ChevronDown, ChevronUp, CloudSun, Train, Star, BookmarkPlus, PenLine } from 'lucide-react'
import { useStore } from '../store'
import { chatApi, tripsApi } from '../api'
import toast from 'react-hot-toast'
import type { Message } from '../types'
import TripPlannerForm from './TripPlannerForm'

// ─── Types for the structured trip JSON ──────────────────────────────────────
interface DayItinerary {
  day: number
  date?: string
  theme?: string
  activities: string[]
  transport?: { route?: string; notes?: string }
  daily_cost_per_person?: Record<string, number>
  cumulative_budget?: { spent: number; budget: number; remaining: number }
  tips?: string[]
}

interface TripJSON {
  destination?: string
  travel_dates?: { departure?: string; return?: string; duration_days?: number }
  travelers?: number
  total_budget_cny?: number
  budget_per_person_cny?: number
  travel_style?: string
  interests?: string[]
  daily_itinerary?: DayItinerary[]
  hotel_search?: {
    price_range_cny_per_night?: number[]
    example_hotels?: { name: string; area?: string; stars: number; price_per_night_cny: number; platform: string; highlights?: string }[]
  }
  restaurant_highlights?: { name: string; type?: string; area?: string; address?: string; avg_price_cny?: number; must_order?: string; tip?: string }[]
  transportation?: {
    flight?: { route?: string; estimated_cost_per_person_cny?: number; notes?: string }
    local_transport?: { type?: string; estimated_cost_per_person_cny?: number; notes?: string }
  }
  budget_breakdown_per_person_cny?: Record<string, number | string>
  weather_forecast?: { period?: string; expected_conditions?: string }
  packing_tips?: string[]
  emergency_info?: Record<string, string>
}

// ─── Helper: safely convert any value to a display number string ─────────────
function safeNum(v: unknown): string {
  if (v === null || v === undefined) return '0'
  if (typeof v === 'number') return v.toLocaleString()
  // Strip currency symbols and commas, then parse
  const n = parseFloat(String(v).replace(/[¥,$,，,\s]/g, '').replace(/,/g, ''))
  return isNaN(n) ? '0' : n.toLocaleString()
}

// ─── Helper: detect if a string is a trip JSON ───────────────────────────────
function normalizeTripJSON(obj: Record<string, unknown>): TripJSON | null {
  // Must have at least a destination-like field to be a trip JSON
  const dest = (obj.destination ?? obj.destination_city ?? obj.trip_overview) as string | Record<string,unknown> | undefined
  if (!dest) return null

  // ── Flatten nested structures ──────────────────────────────────────────────
  // Some AI outputs wrap everything in trip_overview
  const overview = (typeof obj.trip_overview === 'object' && obj.trip_overview
    ? obj.trip_overview : obj) as Record<string, unknown>

  // ── Destination ────────────────────────────────────────────────────────────
  const destination = (overview.destination ?? overview.destination_city ?? '') as string

  // ── Dates — handle: travel_dates, dates, start_date/end_date at root ───────
  const datesObj = (overview.travel_dates ?? overview.dates ?? {}) as Record<string, unknown>
  const departure = (datesObj.departure ?? datesObj.start_date ?? overview.start_date ?? overview.departure_date ?? '') as string
  const returnDate = (datesObj.return ?? datesObj.end_date ?? overview.end_date ?? overview.return_date ?? '') as string
  const durationDays = (datesObj.duration_days ?? overview.duration_days) as number | undefined

  // ── Travelers & budget ─────────────────────────────────────────────────────
  const travelers = Number(overview.travelers ?? 1)
  const totalBudget = Number(overview.total_budget_cny ?? overview.total_budget ?? 0)
  const perPersonRaw = Number(overview.budget_per_person_cny ?? overview.budget_per_person ?? (totalBudget ? totalBudget / travelers : 0))

  // ── Travel style ───────────────────────────────────────────────────────────
  const travelStyle = (overview.travel_style ?? overview.preferred_travel_style ?? '') as string

  // ── Interests ──────────────────────────────────────────────────────────────
  const interests = (overview.interests ?? []) as string[]

  // ── Daily itinerary — handle: daily_itinerary, itinerary, days ────────────
  type DayRaw = Record<string, unknown>
  const rawDays = ((overview.daily_itinerary ?? overview.itinerary ?? overview.days ?? []) as DayRaw[])

  // Transport routes for injection
  type RouteRaw = { route?: string; transport?: string; duration?: string; from?: string; to?: string }
  const rawRoutes = ((overview.transportation_routes ?? overview.routes ?? []) as RouteRaw[])

  const days: DayItinerary[] = rawDays.map((d, i) => {
    // Activities: handle string[] or object[] with description/name fields
    const rawActs = (d.activities ?? d.schedule ?? []) as unknown[]
    const activities: string[] = rawActs.map(a => {
      if (typeof a === 'string') return a
      if (typeof a === 'object' && a !== null) {
        const ao = a as Record<string, unknown>
        const time = ao.time ?? ao.start_time ?? ''
        const name = ao.name ?? ao.title ?? ao.activity ?? ''
        const desc = ao.description ?? ao.details ?? ''
        const cost = ao.cost ?? ao.fee ?? ao.price ?? ''
        return [time && `${time} ·`, name, desc && `— ${desc}`, cost && `Fee: ¥${cost}`]
          .filter(Boolean).join(' ')
      }
      return String(a)
    })

    // Transport for this day
    const route = rawRoutes[i]
    const transport = d.transport as { route?: string; notes?: string } | undefined
    const transportData = transport ?? (route ? {
      route: route.route ?? `${route.from ?? ''} → ${route.to ?? ''}`,
      notes: [route.transport, route.duration].filter(Boolean).join(' · '),
    } : undefined)

    // Daily cost
    const costRaw = (d.daily_cost_per_person ?? d.cost ?? d.daily_cost ?? {}) as Record<string, unknown>
    const dailyCost = Object.keys(costRaw).length > 0
      ? Object.fromEntries(Object.entries(costRaw).map(([k, v]) => [k, Number(v) || 0]))
      : undefined

    return {
      day: Number(d.day ?? i + 1),
      date: (d.date ?? '') as string,
      theme: (d.theme ?? d.title ?? d.summary ?? '') as string,
      activities,
      transport: transportData,
      daily_cost_per_person: dailyCost,
      tips: (d.tips ?? d.notes ?? []) as string[],
    }
  })

  // ── Hotels — handle: hotel_search, hotel_recommendations, hotels ──────────
  type HotelRaw = Record<string, unknown>
  const hotelSearch = overview.hotel_search as Record<string, unknown> | undefined
  const rawHotels = ((hotelSearch?.example_hotels ?? overview.hotel_recommendations ?? overview.hotels ?? []) as HotelRaw[])
  const exampleHotels = rawHotels.map(h => {
    const platforms = (h.booking_platforms ?? h.platforms ?? {}) as Record<string, number>
    const firstPlatform = Object.keys(platforms)[0] ?? 'Booking.com'
    const priceFromPlatforms = Object.values(platforms).find(v => Number(v) > 0) ?? 0
    const price = Number(
      h.price_per_night_cny ?? h.average_price_per_night_cny ??
      h.price_per_night ?? h.price ?? h.rate ?? priceFromPlatforms
    )
    return {
      name: (h.name ?? h.hotel_name ?? '') as string,
      area: (h.area ?? h.location ?? h.district ?? '') as string,
      stars: Number(h.stars ?? h.star_rating ?? h.hotel_class ?? 3),
      price_per_night_cny: isNaN(price) ? 0 : price,
      platform: (h.platform ?? firstPlatform) as string,
      highlights: (h.highlights ?? h.description ?? h.features ?? '') as string,
    }
  }).filter(h => h.name)  // remove empty entries

  // ── Restaurants ────────────────────────────────────────────────────────────
  type RestRaw = Record<string, unknown>
  const rawRests = ((overview.restaurant_highlights ?? overview.dining_recommendations ?? overview.restaurants ?? []) as RestRaw[])
  const restaurants = rawRests.map(r => ({
    name: (r.name ?? '') as string,
    type: (r.type ?? r.cuisine ?? '') as string,
    area: (r.area ?? r.location ?? '') as string,
    address: (r.address ?? '') as string,
    avg_price_cny: Number(r.avg_price_cny ?? r.price ?? r.average_price ?? 0),
    must_order: (r.must_order ?? r.signature_dish ?? r.recommended_dish ?? '') as string,
    tip: (r.tip ?? r.notes ?? '') as string,
  }))

  // ── Budget breakdown ───────────────────────────────────────────────────────
  type BudgetRaw = Record<string, number | string>
  const rawBudget = (overview.budget_breakdown_per_person_cny ?? overview.budget_breakdown ?? overview.budget ?? {}) as BudgetRaw
  const KEY_MAP: Record<string, string> = {
    airfare: 'flight', air_ticket: 'flight', flights: 'flight',
    accommodation: 'hotel', lodging: 'hotel',
    food: 'meals', dining: 'meals', restaurants: 'meals',
    activities_transport: 'activities', sightseeing: 'activities',
    transportation: 'local_transport', transit: 'local_transport',
    // ignore summary fields — don't render them as budget segments
    total_spent: '_skip', budget_remain: '_skip', remaining: '_skip',
  }
  const normalizedBudget: BudgetRaw = {}
  for (const [k, v] of Object.entries(rawBudget)) {
    const key = KEY_MAP[k] ?? k
    if (key !== '_skip') normalizedBudget[key] = v
  }

  // ── Weather ────────────────────────────────────────────────────────────────
  const weatherRaw = (overview.weather_forecast ?? overview.weather ?? {}) as Record<string, string>
  const weather = {
    period: weatherRaw.period ?? weatherRaw.dates ?? '',
    expected_conditions: weatherRaw.expected_conditions ?? weatherRaw.forecast ?? weatherRaw.description ?? weatherRaw.summary ?? '',
  }

  // ── Packing tips ───────────────────────────────────────────────────────────
  const packingTips = (overview.packing_tips ?? overview.packing ?? overview.tips ?? []) as string[]

  // ── Transportation summary ─────────────────────────────────────────────────
  const transRaw = (overview.transportation ?? overview.transport ?? {}) as Record<string, unknown>
  const transportation = Object.keys(transRaw).length > 0 ? {
    flight: transRaw.flight as TripJSON['transportation'],
    local_transport: transRaw.local_transport as TripJSON['transportation'],
  } : undefined

  return {
    destination,
    travel_dates: { departure, return: returnDate, duration_days: durationDays },
    travelers,
    budget_per_person_cny: perPersonRaw || undefined,
    total_budget_cny: totalBudget || undefined,
    travel_style: travelStyle,
    interests,
    daily_itinerary: days.length > 0 ? days : undefined,
    hotel_search: exampleHotels.length > 0 ? { example_hotels: exampleHotels } : undefined,
    restaurant_highlights: restaurants.length > 0 ? restaurants : undefined,
    transportation: transportation as TripJSON['transportation'],
    budget_breakdown_per_person_cny: Object.keys(normalizedBudget).length > 0 ? normalizedBudget : undefined,
    weather_forecast: (weather.period || weather.expected_conditions) ? weather : undefined,
    packing_tips: packingTips.length > 0 ? packingTips : undefined,
  }
}

function parseTripJSON(text: string): TripJSON | null {
  const trimmed = text.trim()
  const candidates: string[] = []

  const match = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (match) candidates.push(match[1].trim())
  candidates.push(trimmed)

  for (const s of candidates) {
    try {
      const obj = JSON.parse(s)
      if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
        const normalized = normalizeTripJSON(obj as Record<string, unknown>)
        if (normalized) return normalized
      }
    } catch { /* continue */ }
  }
  return null
}

// ─── TripHeader ───────────────────────────────────────────────────────────────
function TripHeader({ data }: { data: TripJSON }) {
  return (
    <div className="rounded-2xl overflow-hidden mb-4">
      <div className="gradient-bg p-5 text-white">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <MapPin className="w-4 h-4 text-white/80" />
              <span className="text-xs text-white/70 uppercase tracking-wide">Destination</span>
            </div>
            <h2 className="text-2xl font-bold mb-3">{data.destination ?? 'Trip Plan'}</h2>
          </div>
          {data.travel_style && (
            <span className="text-xs bg-white/20 px-3 py-1 rounded-full">{data.travel_style}</span>
          )}
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          {data.travel_dates?.departure && (
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-white/70" />
              <span>{data.travel_dates.departure} → {data.travel_dates.return}</span>
              {data.travel_dates.duration_days && (
                <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">{data.travel_dates.duration_days} days</span>
              )}
            </div>
          )}
          {data.travelers && (
            <div className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-white/70" />
              <span>{data.travelers} travellers</span>
            </div>
          )}
          {(data.budget_per_person_cny || data.total_budget_cny) && (
            <div className="flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5 text-white/70" />
              {data.total_budget_cny
                ? <span>Total ¥{safeNum(data.total_budget_cny)} · ¥{safeNum(Math.round(data.total_budget_cny / (data.travelers ?? 2)))} / person</span>
                : <span>¥{safeNum(data.budget_per_person_cny)} / person</span>
              }
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── WeatherBanner ────────────────────────────────────────────────────────────
function WeatherBanner({ data }: { data: TripJSON['weather_forecast'] }) {
  if (!data) return null
  return (
    <div className="flex items-start gap-3 bg-sky-50 border border-sky-100 rounded-xl p-3 mb-4">
      <CloudSun className="w-5 h-5 text-sky-500 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-xs font-semibold text-sky-700 mb-0.5">{data.period ?? 'Weather Forecast'}</p>
        <p className="text-xs text-sky-600">{data.expected_conditions}</p>
      </div>
    </div>
  )
}

// ─── RouteVisualizer ──────────────────────────────────────────────────────────
function RouteVisualizer({ route }: { route: string }) {
  const stops = route.split(/[→\->]+/).map(s => s.trim()).filter(Boolean)
  if (stops.length < 2) return <p className="text-xs text-gray-600">{route}</p>
  return (
    <div className="flex items-center flex-wrap gap-1 mt-1">
      {stops.map((stop, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-700">{stop}</span>
          </div>
          {i < stops.length - 1 && (
            <div className="flex items-center gap-0.5 text-gray-300">
              <div className="w-4 h-px bg-gray-300" />
              <div className="w-1.5 h-1.5 border-t border-r border-gray-300 rotate-45 -ml-1" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── DailyItinerary ───────────────────────────────────────────────────────────
function DailyItinerary({ days }: { data: TripJSON; days: NonNullable<TripJSON['daily_itinerary']> }) {
  const [openDays, setOpenDays] = useState<Set<number>>(new Set([1]))
  const toggle = (day: number) => setOpenDays(prev => {
    const next = new Set(prev)
    next.has(day) ? next.delete(day) : next.add(day)
    return next
  })

  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
        <Calendar className="w-4 h-4 text-blue-500" /> Day-by-Day Itinerary
      </h3>
      <div className="space-y-2">
        {days.map((d) => (
          <div key={d.day} className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
            <button onClick={() => toggle(d.day)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {d.day}
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-gray-800">
                    Day {d.day}{d.date ? ` · ${d.date}` : ''}
                  </p>
                  {d.theme && <p className="text-xs text-blue-500">{d.theme}</p>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {d.daily_cost_per_person?.total && (
                  <span className="text-xs text-green-600 font-medium">¥{safeNum(d.daily_cost_per_person.total)}/person</span>
                )}
                {openDays.has(d.day) ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </div>
            </button>

            {openDays.has(d.day) && (
              <div className="px-4 pb-4 border-t border-gray-50">
                {/* Timeline activities */}
                <div className="mt-3 space-y-1">
                  {d.activities.map((act, i) => {
                    // Detect time prefix like "09:00 · " or "09:00 - "
                    const timeMatch = act.match(/^(\d{1,2}:\d{2})\s*[·\-]\s*/)
                    const time = timeMatch?.[1]
                    const content = timeMatch ? act.slice(timeMatch[0].length) : act
                    return (
                      <div key={i} className="flex gap-3">
                        <div className="flex flex-col items-center flex-shrink-0 w-12">
                          {time ? (
                            <span className="text-[10px] font-mono text-blue-500 font-semibold">{time}</span>
                          ) : (
                            <div className="w-2 h-2 rounded-full bg-blue-300 mt-1" />
                          )}
                          {i < d.activities.length - 1 && <div className="w-px flex-1 bg-gray-100 mt-1 mb-1" />}
                        </div>
                        <p className="text-xs text-gray-700 pb-2 leading-relaxed flex-1">{content}</p>
                      </div>
                    )
                  })}
                </div>

                {/* Transport card */}
                {d.transport && (
                  <div className="mt-3 bg-amber-50 border border-amber-100 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Train className="w-3.5 h-3.5 text-amber-600" />
                      <span className="text-xs font-semibold text-amber-700">Transport Route</span>
                    </div>
                    {d.transport.route && <RouteVisualizer route={d.transport.route} />}
                    {d.transport.notes && (
                      <p className="text-xs text-amber-600 mt-1.5">{d.transport.notes}</p>
                    )}
                  </div>
                )}

                {/* Daily cost breakdown */}
                {d.daily_cost_per_person && Object.keys(d.daily_cost_per_person).length > 1 && (
                  <div className="mt-3 bg-gray-50 rounded-xl p-3">
                    <p className="text-xs font-semibold text-gray-600 mb-2">Today's Cost / Person</p>
                    <div className="grid grid-cols-2 gap-1">
                      {Object.entries(d.daily_cost_per_person)
                        .filter(([k]) => k !== 'total')
                        .map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}</span>
                            <span className="font-medium text-gray-700">¥{safeNum(v)}</span>
                          </div>
                        ))}
                    </div>
                    {d.daily_cost_per_person.total && (
                      <div className="flex justify-between text-xs font-bold text-gray-800 border-t border-gray-200 mt-2 pt-2">
                        <span>Total</span>
                        <span>¥{safeNum(d.daily_cost_per_person.total)}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Cumulative budget tracker */}
                {d.cumulative_budget && (
                  <div className="mt-3 flex items-center justify-between bg-blue-50 rounded-xl px-3 py-2 border border-blue-100">
                    <span className="text-xs text-blue-600">Cumulative spend</span>
                    <span className="text-xs font-bold text-blue-800">
                      ¥{safeNum(d.cumulative_budget.spent)} / ¥{safeNum(d.cumulative_budget.budget)}
                      <span className={`ml-2 ${(d.cumulative_budget.remaining ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                        ({(d.cumulative_budget.remaining ?? 0) >= 0
                          ? '¥' + safeNum(d.cumulative_budget.remaining) + ' left'
                          : 'over budget'})
                      </span>
                    </span>
                  </div>
                )}

                {/* Tips */}
                {d.tips && d.tips.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {d.tips.map((tip, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-purple-700">
                        <span className="text-purple-400 flex-shrink-0">💡</span>
                        <span>{tip}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── HotelCards ───────────────────────────────────────────────────────────────
const PLATFORM_COLORS: Record<string, string> = {
  'Booking.com': 'bg-blue-100 text-blue-700',
  'Agoda': 'bg-orange-100 text-orange-700',
  'Hotels.com': 'bg-red-100 text-red-700',
  'Ctrip': 'bg-cyan-100 text-cyan-700',
}

function HotelCards({ hotels }: { hotels: NonNullable<TripJSON['hotel_search']>['example_hotels'] }) {
  if (!hotels?.length) return null
  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
        🏨 Recommended Hotels
      </h3>
      <div className="space-y-2">
        {hotels.map((h, i) => (
          <div key={i} className="bg-white border border-gray-100 rounded-xl p-3 shadow-sm flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-medium text-gray-800 truncate">{h.name}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${PLATFORM_COLORS[h.platform] ?? 'bg-gray-100 text-gray-600'}`}>
                  {h.platform}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: h.stars }).map((_, j) => (
                    <Star key={j} className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                {h.area && <span className="text-xs text-gray-400">{h.area}</span>}
              </div>
              {h.highlights && <p className="text-xs text-gray-500 mt-0.5">{h.highlights}</p>}
            </div>
            <div className="text-right flex-shrink-0 ml-3">
              {h.price_per_night_cny > 0 ? (
                <>
                  <p className="text-base font-bold text-blue-600">¥{h.price_per_night_cny.toLocaleString()}</p>
                  <p className="text-xs text-gray-400">/night</p>
                </>
              ) : (
                <p className="text-xs text-gray-400">Price varies</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── RestaurantHighlights ─────────────────────────────────────────────────────
function RestaurantHighlights({ restaurants }: { restaurants: NonNullable<TripJSON['restaurant_highlights']> }) {
  if (!restaurants.length) return null
  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-gray-800 mb-3">🍜 Restaurant Highlights</h3>
      <div className="space-y-2">
        {restaurants.map((r, i) => (
          <div key={i} className="bg-white border border-gray-100 rounded-xl p-3 shadow-sm">
            <div className="flex items-start justify-between mb-1">
              <div>
                <p className="text-sm font-semibold text-gray-800">{r.name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {r.type && <span className="text-xs bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full">{r.type}</span>}
                  {r.area && <span className="text-xs text-gray-400">{r.area}</span>}
                </div>
              </div>
              {r.avg_price_cny && (
                <span className="text-xs font-semibold text-green-600 flex-shrink-0">~¥{r.avg_price_cny}/person</span>
              )}
            </div>
            {r.address && <p className="text-xs text-gray-500 mt-1">📍 {r.address}</p>}
            {r.must_order && <p className="text-xs text-gray-700 mt-1">⭐ Must order: <span className="font-medium">{r.must_order}</span></p>}
            {r.tip && <p className="text-xs text-amber-600 mt-1">💡 {r.tip}</p>}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── PackingTips ──────────────────────────────────────────────────────────────
function PackingTips({ tips }: { tips: string[] }) {
  if (!tips.length) return null
  return (
    <div className="mb-4 bg-purple-50 border border-purple-100 rounded-xl p-4">
      <h3 className="text-sm font-bold text-purple-800 mb-2">🎒 Packing Tips</h3>
      <div className="flex flex-wrap gap-2">
        {tips.map((tip, i) => (
          <span key={i} className="text-xs bg-white text-purple-700 border border-purple-200 px-2 py-1 rounded-lg">{tip}</span>
        ))}
      </div>
    </div>
  )
}

// ─── BudgetBreakdown ──────────────────────────────────────────────────────────
const BUDGET_COLORS = ['#3b82f6', '#8b5cf6', '#f97316', '#10b981', '#6b7280']
const BUDGET_LABELS: Record<string, string> = {
  flight: 'Flights', hotel: 'Hotel', meals: 'Meals',
  activities: 'Activities', local_transport: 'Transport',
}

function BudgetDonut({ breakdown, perPerson, totalBudget }: {
  breakdown: Record<string, number>; perPerson: number; totalBudget: number
}) {
  // Safely parse all values to numbers
  const entries = Object.entries(breakdown)
    .map(([k, v]) => ({ key: k, value: parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0 }))
    .filter(({ value }) => value > 0)

  const total = entries.reduce((s, e) => s + e.value, 0) || 1
  const radius = 40
  const circumference = 2 * Math.PI * radius
  let offset = 0

  const segments = entries.map((e, i) => {
    const pct = e.value / total
    const dash = pct * circumference
    const seg = { ...e, pct, dash, offset, color: BUDGET_COLORS[i % BUDGET_COLORS.length] }
    offset += dash
    return seg
  })

  const safePerPerson = parseFloat(String(perPerson).replace(/[^0-9.]/g, '')) || 0
  const safeTotalBudget = parseFloat(String(totalBudget).replace(/[^0-9.]/g, '')) || 1
  const remaining = safeTotalBudget - safePerPerson

  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
        <Wallet className="w-4 h-4 text-green-500" /> Budget Breakdown
      </h3>
      <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-6">
          <div className="relative flex-shrink-0">
            <svg width="100" height="100" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r={radius} fill="none" stroke="#f3f4f6" strokeWidth="16" />
              {segments.map((seg) => (
                <circle key={seg.key} cx="50" cy="50" r={radius} fill="none"
                  stroke={seg.color} strokeWidth="16"
                  strokeDasharray={`${seg.dash} ${circumference - seg.dash}`}
                  strokeDashoffset={-seg.offset + circumference * 0.25}
                  style={{ transform: 'rotate(-90deg)', transformOrigin: '50px 50px' }} />
              ))}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <p className="text-xs text-gray-500">per person</p>
              <p className="text-sm font-bold text-gray-900">¥{safeNum(safePerPerson)}</p>
            </div>
          </div>
          <div className="flex-1 space-y-1.5">
            {segments.map((seg) => (
              <div key={seg.key} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: seg.color }} />
                  <span className="text-xs text-gray-600">{BUDGET_LABELS[seg.key] ?? seg.key}</span>
                </div>
                <span className="text-xs font-semibold text-gray-800">¥{safeNum(seg.value)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-4 pt-3 border-t border-gray-100">
          <div className="flex justify-between text-xs text-gray-500 mb-1.5">
            <span>Estimated: ¥{safeNum(safePerPerson)}</span>
            <span>Budget: ¥{safeNum(safeTotalBudget)}</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all"
              style={{ width: `${Math.min((safePerPerson / safeTotalBudget) * 100, 100)}%` }} />
          </div>
          <p className={`text-xs mt-1.5 font-medium ${remaining >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {remaining >= 0 ? `¥${safeNum(remaining)} remaining` : `¥${safeNum(Math.abs(remaining))} over budget`}
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── TripResultCard ───────────────────────────────────────────────────────────
function TripResultCard({ data, onSave, onModify }: {
  data: TripJSON
  onSave: () => void
  onModify: () => void
}) {
  // Safely parse budget breakdown — AI sometimes returns strings like "¥3,500"
  const toNum = (v: unknown) => parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0
  const numericBreakdown = Object.fromEntries(
    Object.entries(data.budget_breakdown_per_person_cny ?? {})
      .filter(([k]) => !['total_estimated', 'total', 'notes', '_skip'].includes(k))
      .map(([k, v]) => [k, toNum(v)])
      .filter(([, v]) => (v as number) > 0)
  )

  // Determine per-person budget — prefer breakdown total, then explicit fields
  const breakdownTotal = toNum(data.budget_breakdown_per_person_cny?.total_estimated ?? data.budget_breakdown_per_person_cny?.total ?? 0)
  const rawPerPerson = toNum(data.budget_per_person_cny ?? 0)
  const rawTotal = toNum(data.total_budget_cny ?? 0)
  const travelers = data.travelers ?? 1

  // Pick the best per-person figure
  let perPerson = breakdownTotal || rawPerPerson || (rawTotal ? rawTotal / travelers : 0)

  // Sanity check: if AI confused total vs per-person (ratio > 5x), auto-correct
  if (rawTotal > 0 && perPerson > 0 && rawTotal / perPerson > 5) {
    perPerson = Math.round(rawTotal / travelers)
  }

  // totalBudget = what the user said their per-person budget is
  const totalBudget = rawPerPerson || (rawTotal ? rawTotal / travelers : perPerson) || 15000

  return (
    <div className="w-full max-w-xl">
      <TripHeader data={data} />
      <WeatherBanner data={data.weather_forecast} />
      {data.daily_itinerary && <DailyItinerary data={data} days={data.daily_itinerary} />}
      <HotelCards hotels={data.hotel_search?.example_hotels} />
      {data.restaurant_highlights && data.restaurant_highlights.length > 0 && (
        <RestaurantHighlights restaurants={data.restaurant_highlights} />
      )}
      {Object.keys(numericBreakdown).length > 0 && (
        <BudgetDonut breakdown={numericBreakdown} perPerson={perPerson} totalBudget={totalBudget} />
      )}
      {data.packing_tips && data.packing_tips.length > 0 && (
        <PackingTips tips={data.packing_tips} />
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-2">
        <button onClick={onSave}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl gradient-bg text-white text-xs font-semibold hover:opacity-90 transition-opacity shadow-md">
          <BookmarkPlus className="w-3.5 h-3.5" /> Save to My Trips
        </button>
        <button onClick={onModify}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gray-100 text-gray-700 text-xs font-semibold hover:bg-gray-200 transition-colors">
          <PenLine className="w-3.5 h-3.5" /> Modify Request
        </button>
      </div>
    </div>
  )
}

// ─── Suggestions (kept for TripPlannerForm skip fallback) ────────────────────
function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-2 h-2 rounded-full bg-blue-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </div>
  )
}

// ─── ChatBubble ───────────────────────────────────────────────────────────────
function ChatBubble({ msg, onModify }: { msg: Message; onModify: (text: string) => void }) {
  const isUser = msg.role === 'user'

  // Try to parse trip JSON from content
  const tripData = !isUser ? parseTripJSON(msg.content) : null

  const handleSave = async () => {
    if (!tripData) return
    try {
      await tripsApi.create({
        destination: tripData.destination ?? 'Unknown',
        start_date: tripData.travel_dates?.departure ?? undefined,
        end_date: tripData.travel_dates?.return ?? undefined,
        budget: tripData.total_budget_cny ?? undefined,
        currency: 'CNY',
        travel_style: tripData.travel_style ?? 'balanced',
      })
      toast.success('Trip saved!')
    } catch {
      toast.error('Failed to save trip')
    }
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${isUser ? 'gradient-bg' : 'bg-blue-50 border border-blue-100'}`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-blue-500" />}
      </div>

      {tripData ? (
        // Render structured trip card
        <TripResultCard
          data={tripData}
          onSave={handleSave}
          onModify={() => onModify(`Please help me modify this trip plan for ${tripData.destination}: `)}
        />
      ) : (
        // Render normal markdown bubble
        <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser ? 'gradient-bg text-white rounded-tr-sm' : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-sm'
        }`}>
          {isUser ? (
            <p>{msg.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── ChatPanel (main export) ──────────────────────────────────────────────────
export default function ChatPanel() {
  const { messages, isLoading, threadId, addMessage, setLoading, setThreadId, clearChat } = useStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content || isLoading) return
    setInput('')

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content, timestamp: new Date() }
    addMessage(userMsg)
    setLoading(true)

    try {
      const res = await chatApi.send(content, threadId ?? undefined)
      const { reply, thread_id } = res.data
      setThreadId(thread_id)
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
        trip_plan: res.data.trip_plan as Message['trip_plan'],
      }
      addMessage(aiMsg)
    } catch {
      toast.error('Failed to get response. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-gray-900">AI Travel Concierge</h2>
          <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full font-medium">Online</span>
        </div>
        <button
          onClick={() => { clearChat(); setThreadId('') }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors text-xs font-medium"
          title="Start a new conversation (clears history and context)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide p-6 space-y-4">
        {messages.length === 0 && (
          <TripPlannerForm
            onSubmit={(prompt) => { if (prompt) send(prompt) }}
            isLoading={isLoading}
          />
        )}

        {messages.map((msg) => (
          <ChatBubble key={msg.id} msg={msg} onModify={(text) => setInput(text)} />
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center">
              <Bot className="w-4 h-4 text-blue-500" />
            </div>
            <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm">
              <TypingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-gray-100 bg-white">
        <div className="flex gap-3 items-end">
          <textarea value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Tell me where you want to go..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent max-h-32 overflow-y-auto"
            style={{ minHeight: '48px' }}
          />
          <button onClick={() => send()} disabled={!input.trim() || isLoading}
            className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center text-white hover:opacity-90 transition-opacity disabled:opacity-40 flex-shrink-0 shadow-md">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
