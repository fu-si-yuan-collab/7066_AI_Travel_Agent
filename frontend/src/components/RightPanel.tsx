import { useState } from 'react'
import { Cloud, Sun, CloudRain, Wind, Thermometer, MapPin, Wallet } from 'lucide-react'

// Mock weather data
const MOCK_WEATHER = [
  { day: 'Today', icon: 'sun', temp_max: 22, temp_min: 15, desc: 'Sunny', pop: 0.05 },
  { day: 'Tue', icon: 'cloud', temp_max: 19, temp_min: 13, desc: 'Cloudy', pop: 0.2 },
  { day: 'Wed', icon: 'rain', temp_max: 16, temp_min: 11, desc: 'Rainy', pop: 0.8 },
  { day: 'Thu', icon: 'sun', temp_max: 21, temp_min: 14, desc: 'Clear', pop: 0.1 },
  { day: 'Fri', icon: 'cloud', temp_max: 18, temp_min: 12, desc: 'Partly cloudy', pop: 0.3 },
]

const DESTINATIONS = [
  { name: 'Tokyo', img: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=300&q=80', tag: 'Trending' },
  { name: 'Bali', img: 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=300&q=80', tag: 'Popular' },
  { name: 'Paris', img: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=300&q=80', tag: 'Classic' },
  { name: 'Kyoto', img: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=300&q=80', tag: 'Cultural' },
]

function WeatherIcon({ icon }: { icon: string }) {
  if (icon === 'sun') return <Sun className="w-5 h-5 text-yellow-400" />
  if (icon === 'rain') return <CloudRain className="w-5 h-5 text-blue-400" />
  return <Cloud className="w-5 h-5 text-gray-400" />
}

export default function RightPanel() {
  const [budgetUsed] = useState(3200)
  const [budgetTotal] = useState(8000)
  const pct = Math.round((budgetUsed / budgetTotal) * 100)

  return (
    <aside className="w-72 min-h-screen overflow-y-auto scrollbar-hide bg-gray-50 border-l border-gray-100 p-4 space-y-4">

      {/* Weather */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-gray-900 text-sm">Weather</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <MapPin className="w-3 h-3" />Tokyo
          </div>
        </div>
        {/* Today highlight */}
        <div className="gradient-bg rounded-xl p-3 mb-3 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/70 text-xs">Today</p>
              <p className="text-2xl font-bold">{MOCK_WEATHER[0].temp_max}°C</p>
              <p className="text-white/80 text-xs">{MOCK_WEATHER[0].desc}</p>
            </div>
            <Sun className="w-10 h-10 text-yellow-300" />
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs text-white/70">
            <span className="flex items-center gap-1"><Wind className="w-3 h-3" />12 km/h</span>
            <span>💧 {Math.round(MOCK_WEATHER[0].pop * 100)}%</span>
          </div>
        </div>
        {/* 5-day forecast */}
        <div className="flex justify-between">
          {MOCK_WEATHER.slice(1).map((w) => (
            <div key={w.day} className="flex flex-col items-center gap-1">
              <span className="text-xs text-gray-400">{w.day}</span>
              <WeatherIcon icon={w.icon} />
              <span className="text-xs font-medium text-gray-700">{w.temp_max}°</span>
              <span className="text-xs text-gray-400">{w.temp_min}°</span>
            </div>
          ))}
        </div>
      </div>

      {/* Budget tracker */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <Wallet className="w-4 h-4 text-green-500" />
          <span className="font-semibold text-gray-900 text-sm">Budget Tracker</span>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mb-2">
          <span>Spent: ¥{budgetUsed.toLocaleString()}</span>
          <span>Total: ¥{budgetTotal.toLocaleString()}</span>
        </div>
        <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden mb-2">
          <div className={`h-full rounded-full transition-all ${pct > 80 ? 'bg-red-400' : pct > 60 ? 'bg-yellow-400' : 'bg-green-400'}`}
            style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-400">{pct}% used · ¥{(budgetTotal - budgetUsed).toLocaleString()} remaining</p>
        <div className="mt-3 space-y-1.5">
          {[['✈️ Flights', 1200], ['🏨 Hotels', 1400], ['🍜 Food', 400], ['🎡 Activities', 200]].map(([label, amt]) => (
            <div key={label as string} className="flex justify-between text-xs">
              <span className="text-gray-600">{label as string}</span>
              <span className="font-medium text-gray-800">¥{(amt as number).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Map placeholder */}
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100">
        <div className="h-36 bg-gradient-to-br from-blue-100 to-green-100 flex items-center justify-center relative">
          <div className="absolute inset-0 opacity-30" style={{ backgroundImage: 'url(https://images.unsplash.com/photo-1524661135-423995f22d0b?w=400&q=60)', backgroundSize: 'cover' }} />
          <div className="relative z-10 text-center">
            <MapPin className="w-8 h-8 text-blue-600 mx-auto mb-1" />
            <p className="text-xs font-medium text-blue-800">Interactive Map</p>
            <p className="text-xs text-blue-600">Coming soon</p>
          </div>
        </div>
      </div>

      {/* Explore inspiration */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">✨ Explore Inspiration</h3>
        <div className="grid grid-cols-2 gap-2">
          {DESTINATIONS.map((d) => (
            <div key={d.name} className="relative rounded-xl overflow-hidden cursor-pointer group">
              <img src={d.img} alt={d.name} className="w-full h-20 object-cover group-hover:scale-110 transition-transform duration-300" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
              <div className="absolute bottom-1.5 left-2">
                <p className="text-white text-xs font-semibold">{d.name}</p>
                <p className="text-white/70 text-[10px]">{d.tag}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
