// API types shared across the frontend
export interface ToolStep {
  tool: string       // "search_weather" | "find_flights" | "find_hotels" | "find_restaurants" | "find_activities"
  status: 'success' | 'error'
  summary: string    // human-readable: "Found 6 flights from ¥3,200"
  args?: Record<string, unknown>
}

export interface CalendarEvent {
  date: string       // "2024-06-15"
  time: string       // "09:00"
  title: string
  description?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  trip_plan?: TripPlan | null
  tool_steps?: ToolStep[]
  calendar_events?: CalendarEvent[]
  calendar_confirmed?: boolean
}

export interface TripPlan {
  days?: DayPlan[]
  hotels?: Hotel[]
  budget?: BudgetBreakdown
  [key: string]: unknown
}

export interface DayPlan {
  day: number
  date?: string
  title?: string
  activities: Activity[]
}

export interface Activity {
  time?: string
  name: string
  description?: string
  type?: string
  cost?: number
  location?: string
}

export interface Hotel {
  name: string
  stars?: number
  rating?: number
  price_per_night: number
  currency?: string
  source?: string
  amenities?: string[]
  image_url?: string
  booking_url?: string
}

export interface BudgetBreakdown {
  total?: number
  flights?: number
  accommodation?: number
  food?: number
  activities?: number
  transport?: number
  currency?: string
}

export interface UserPreference {
  preferred_travel_style: string
  preferred_transport: string
  preferred_hotel_stars: number
  preferred_cuisine: string
  daily_budget_low: number
  daily_budget_high: number
  currency: string
  learned_tags?: Record<string, number> | null
}

export interface AuthState {
  token: string | null
  user: { email: string; nickname: string; id: string } | null
}
