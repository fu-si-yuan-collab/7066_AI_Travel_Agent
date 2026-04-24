import { useState } from 'react'
import { Star, MapPin, Wifi, Coffee, Car, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'

// Mock hotel data for demonstration (real data comes from chat trip_plan)
const MOCK_HOTELS = [
  { name: 'Park Hyatt Tokyo', stars: 5, rating: 9.2, price_per_night: 1200, currency: 'CNY', source: 'Booking.com', location: 'Shinjuku', amenities: ['WiFi', 'Pool', 'Spa', 'Restaurant'], image: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&q=80' },
  { name: 'Shinjuku Granbell Hotel', stars: 4, rating: 8.7, price_per_night: 680, currency: 'CNY', source: 'Ctrip', location: 'Shinjuku', amenities: ['WiFi', 'Gym', 'Bar'], image: 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400&q=80' },
  { name: 'APA Hotel Shinjuku', stars: 3, rating: 8.1, price_per_night: 380, currency: 'CNY', source: 'Agoda', location: 'Shinjuku', amenities: ['WiFi', 'Convenience Store'], image: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&q=80' },
  { name: 'Cerulean Tower Tokyu Hotel', stars: 5, rating: 9.0, price_per_night: 980, currency: 'CNY', source: 'Google Hotels', location: 'Shibuya', amenities: ['WiFi', 'Pool', 'Restaurant', 'Bar'], image: 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=400&q=80' },
  { name: 'Dormy Inn Asakusa', stars: 3, rating: 8.5, price_per_night: 420, currency: 'CNY', source: 'Booking.com', location: 'Asakusa', amenities: ['WiFi', 'Onsen', 'Breakfast'], image: 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=400&q=80' },
]

const AMENITY_ICONS: Record<string, React.ReactNode> = {
  WiFi: <Wifi className="w-3 h-3" />,
  Breakfast: <Coffee className="w-3 h-3" />,
  Parking: <Car className="w-3 h-3" />,
}

const SOURCE_COLORS: Record<string, string> = {
  'Booking.com': 'bg-blue-100 text-blue-700',
  'Ctrip': 'bg-orange-100 text-orange-700',
  'Agoda': 'bg-red-100 text-red-700',
  'Google Hotels': 'bg-green-100 text-green-700',
}

function HotelCard({ hotel }: { hotel: typeof MOCK_HOTELS[0] }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="relative h-40 overflow-hidden">
        <img src={hotel.image} alt={hotel.name} className="w-full h-full object-cover hover:scale-105 transition-transform duration-300" />
        <div className="absolute top-3 right-3">
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${SOURCE_COLORS[hotel.source] ?? 'bg-gray-100 text-gray-600'}`}>
            {hotel.source}
          </span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">{hotel.name}</h3>
            <div className="flex items-center gap-1 mt-1">
              <MapPin className="w-3 h-3 text-gray-400" />
              <span className="text-xs text-gray-500">{hotel.location}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-blue-600">¥{hotel.price_per_night}</div>
            <div className="text-xs text-gray-400">/night</div>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-3">
          <div className="flex">
            {Array.from({ length: hotel.stars }).map((_, i) => (
              <Star key={i} className="w-3 h-3 text-yellow-400 fill-yellow-400" />
            ))}
          </div>
          <span className="text-xs font-semibold text-green-600 bg-green-50 px-1.5 py-0.5 rounded">{hotel.rating}</span>
        </div>

        <div className="flex flex-wrap gap-1 mb-3">
          {hotel.amenities.slice(0, 3).map((a) => (
            <span key={a} className="flex items-center gap-1 text-xs bg-gray-50 text-gray-600 px-2 py-1 rounded-lg">
              {AMENITY_ICONS[a] ?? null}{a}
            </span>
          ))}
        </div>

        <button onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 text-xs text-blue-500 hover:text-blue-700 transition-colors">
          {expanded ? <><ChevronUp className="w-3 h-3" />Less</> : <><ChevronDown className="w-3 h-3" />Compare prices</>}
        </button>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            <p className="text-xs font-medium text-gray-700 mb-2">Price comparison:</p>
            {['Booking.com', 'Ctrip', 'Agoda'].map((src) => {
              const variation = Math.round((Math.random() - 0.5) * 100)
              return (
                <div key={src} className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">{src}</span>
                  <span className={`text-xs font-semibold ${variation < 0 ? 'text-green-600' : 'text-gray-700'}`}>
                    ¥{hotel.price_per_night + variation}
                    {variation < 0 && <span className="ml-1 text-green-500">Best</span>}
                  </span>
                </div>
              )
            })}
            <button className="w-full mt-2 py-2 rounded-xl gradient-bg text-white text-xs font-medium flex items-center justify-center gap-1 hover:opacity-90 transition-opacity">
              <ExternalLink className="w-3 h-3" />Book Now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function HotelsPanel() {
  const [maxPrice, setMaxPrice] = useState(2000)
  const [location, setLocation] = useState('All')

  const locations = ['All', ...Array.from(new Set(MOCK_HOTELS.map((h) => h.location)))]
  const filtered = MOCK_HOTELS.filter((h) => h.price_per_night <= maxPrice && (location === 'All' || h.location === location))

  return (
    <div className="h-full overflow-y-auto scrollbar-hide p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-1">Hotel Comparison</h2>
        <p className="text-sm text-gray-500">Compare prices across Booking.com, Ctrip, Agoda & more</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-48">
            <label className="text-xs font-medium text-gray-600 mb-1 block">Max price/night: ¥{maxPrice}</label>
            <input type="range" min={200} max={2000} step={100} value={maxPrice} onChange={(e) => setMaxPrice(+e.target.value)}
              className="w-full accent-blue-500" />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">Location</label>
            <div className="flex gap-2">
              {locations.map((l) => (
                <button key={l} onClick={() => setLocation(l)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${location === l ? 'gradient-bg text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filtered.map((h) => <HotelCard key={h.name} hotel={h} />)}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p>No hotels match your filters.</p>
          </div>
        )}
      </div>
    </div>
  )
}
