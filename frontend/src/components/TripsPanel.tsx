import { useEffect, useState } from 'react'
import { tripsApi } from '../api'
import { MapPin, Calendar, DollarSign, ChevronDown, ChevronUp, Clock } from 'lucide-react'

interface Trip {
  id: string
  title: string
  destination: string
  origin: string
  start_date: string | null
  end_date: string | null
  budget: number | null
  currency: string
  status: string
  travel_style: string
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  confirmed: 'bg-blue-100 text-blue-600',
  completed: 'bg-green-100 text-green-600',
  cancelled: 'bg-red-100 text-red-600',
}

function TripCard({ trip }: { trip: Trip }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="h-32 relative overflow-hidden">
        <div className="absolute inset-0 gradient-bg opacity-80" />
        <div className="absolute inset-0 flex items-end p-4">
          <div>
            <h3 className="text-white font-bold text-lg">{trip.destination}</h3>
            {trip.origin && <p className="text-white/70 text-sm">from {trip.origin}</p>}
          </div>
        </div>
        <span className={`absolute top-3 right-3 text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[trip.status] ?? 'bg-gray-100 text-gray-600'}`}>
          {trip.status}
        </span>
      </div>
      <div className="p-4">
        <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
          {trip.start_date && (
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {trip.start_date}{trip.end_date ? ` → ${trip.end_date}` : ''}
            </div>
          )}
          {trip.budget && (
            <div className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              {trip.budget} {trip.currency}
            </div>
          )}
          <div className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {trip.travel_style}
          </div>
        </div>
        <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700">
          {open ? <><ChevronUp className="w-3 h-3" />Hide details</> : <><ChevronDown className="w-3 h-3" />View details</>}
        </button>
        {open && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">Trip ID: {trip.id}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden animate-pulse">
      <div className="h-32 bg-gray-200" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-3 bg-gray-100 rounded w-1/2" />
      </div>
    </div>
  )
}

export default function TripsPanel() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    tripsApi.list().then((r) => setTrips(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div className="h-full overflow-y-auto scrollbar-hide p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-1">My Trips</h2>
        <p className="text-sm text-gray-500">All your travel plans in one place</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
      ) : trips.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
            <Clock className="w-8 h-8 text-blue-300" />
          </div>
          <h3 className="font-semibold text-gray-700 mb-2">No trips yet</h3>
          <p className="text-sm text-gray-400 max-w-xs">Start a conversation with the AI to plan your first trip!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {trips.map((t) => <TripCard key={t.id} trip={t} />)}
        </div>
      )}
    </div>
  )
}
