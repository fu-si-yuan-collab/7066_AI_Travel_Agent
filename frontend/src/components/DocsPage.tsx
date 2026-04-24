import { useState } from 'react'
import { BookOpen, Cpu, Layers, Terminal, Users, ChevronDown, ChevronUp, ExternalLink, Zap, Database, Globe, Shield } from 'lucide-react'

function AccordionSection({ id, icon: Icon, title, color, children }: {
  id: string; icon: typeof BookOpen; title: string; color: string; children: React.ReactNode
}) {
  const [open, setOpen] = useState(id === 'overview')
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 p-5 hover:bg-gray-50 transition-colors text-left">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center flex-shrink-0`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <span className="flex-1 font-semibold text-gray-900">{title}</span>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && <div className="px-5 pb-5 border-t border-gray-50">{children}</div>}
    </div>
  )
}

function Tag({ children, color = 'blue' }: { children: React.ReactNode; color?: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-700',
    green: 'bg-green-100 text-green-700',
    orange: 'bg-orange-100 text-orange-700',
    purple: 'bg-purple-100 text-purple-700',
    red: 'bg-red-100 text-red-700',
  }
  return <span className={`text-xs font-medium px-2 py-1 rounded-lg ${colors[color]}`}>{children}</span>
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="bg-gray-900 text-green-400 rounded-xl p-4 text-xs overflow-x-auto font-mono leading-relaxed mt-3">
      {children}
    </pre>
  )
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto mt-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50">
            {headers.map((h) => <th key={h} className="text-left px-3 py-2 text-xs font-semibold text-gray-600 rounded">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
              {row.map((cell, j) => <td key={j} className="px-3 py-2 text-xs text-gray-700">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DocsPage() {
  return (
    <div className="h-full overflow-y-auto scrollbar-hide p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-2xl gradient-bg flex items-center justify-center shadow-lg">
            <BookOpen className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Project Documentation</h1>
            <p className="text-sm text-gray-500">MSBA 7066 · AI Travel Agent · HKU Business School</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag color="blue">LangGraph</Tag>
          <Tag color="purple">FastAPI</Tag>
          <Tag color="green">React + TypeScript</Tag>
          <Tag color="orange">Azure OpenAI</Tag>
          <Tag color="red">Multi-Agent</Tag>
        </div>
      </div>

      <div className="space-y-3">

        {/* Overview */}
        <AccordionSection id="overview" icon={BookOpen} title="Project Overview" color="from-blue-500 to-cyan-500">
          <div className="pt-4 space-y-4">
            <p className="text-sm text-gray-600 leading-relaxed">
              AI Travel Agent is a full-stack AI-powered travel concierge that solves three core pain points modern travellers face:
            </p>
            <Table
              headers={['Pain Point', 'Description', 'Our Solution']}
              rows={[
                ['Price fragmentation', 'Hotel/flight prices differ across Ctrip, Booking, Agoda', 'Aggregate & compare in one view'],
                ['App switching fatigue', 'Planning, navigation, weather scattered across 5+ apps', 'Single platform for everything'],
                ['No personalisation', 'Platforms forget your preferences every trip', 'AI memory that learns over time'],
              ]}
            />
            <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
              <p className="text-sm font-semibold text-blue-800 mb-2">What the AI can do in one conversation:</p>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>✈️ Search and compare flights across multiple providers</li>
                <li>🏨 Compare hotel prices from Booking.com, Ctrip, Agoda, Google Hotels</li>
                <li>📅 Generate a complete day-by-day itinerary</li>
                <li>🌤️ Check weather forecasts for your travel dates</li>
                <li>🗺️ Plan optimal routes between attractions</li>
                <li>💰 Break down your budget into 3 tiers (Budget / Balanced / Premium)</li>
              </ul>
            </div>
          </div>
        </AccordionSection>

        {/* Architecture */}
        <AccordionSection id="architecture" icon={Layers} title="System Architecture" color="from-purple-500 to-pink-500">
          <div className="pt-4 space-y-4">
            <CodeBlock>{`User Input (natural language)
       │
       ▼
  FastAPI Backend  ──── JWT Auth ──── PostgreSQL
       │                                  │
       ▼                              User prefs
  LangGraph StateGraph
       │
  [coordinator] ──missing info──► return question to user
       │ info complete
       ▼
  [flight_search] → [hotel_search] → [weather_check]
                                           │
                                     [navigation]
                                           │
                                   [plan_itinerary]
                                           │
                                   [analyze_budget]
                                           │
                                          END
       │
  Redis Cache (30min TTL for API responses)
       │
  External APIs: Azure OpenAI · SerpAPI · OpenWeatherMap · AMap`}</CodeBlock>
            <p className="text-xs text-gray-500 mt-2">
              Each node in the graph is an independent specialist agent. They share a single <code className="bg-gray-100 px-1 rounded">AgentState</code> object — each node reads what it needs and writes only its own output fields.
            </p>
          </div>
        </AccordionSection>

        {/* Agent Design */}
        <AccordionSection id="agent" icon={Cpu} title="Agent Design & Prompt Engineering" color="from-orange-500 to-red-500">
          <div className="pt-4 space-y-5">
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Node Responsibilities</h3>
              <Table
                headers={['Node', 'Role', 'Key Output', 'Temperature']}
                rows={[
                  ['coordinator', 'Parse intent, extract structured plan, route decision', 'travel_plan, needs_user_input', '0.3'],
                  ['flight_search', 'Query Amadeus + Google Flights, sort by price', 'flight_results', '—'],
                  ['hotel_search', 'Multi-platform hotel comparison', 'hotel_results', '—'],
                  ['weather_check', 'Fetch 5-day forecast from OpenWeatherMap', 'weather_data', '—'],
                  ['navigation', 'Route planning via AMap / Google Maps', 'navigation_data', '—'],
                  ['plan_itinerary', 'Synthesise all data into day-by-day plan', 'itinerary', '0.4'],
                  ['analyze_budget', 'Cost breakdown, 3-tier suggestions', 'budget_breakdown', '0.2'],
                ]}
              />
            </div>

            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Coordinator Prompt Strategy</h3>
              <div className="bg-orange-50 rounded-xl p-4 border border-orange-100 text-xs text-orange-800 font-mono leading-relaxed">
                <p className="font-bold mb-2">System Prompt (coordinator):</p>
                <p>You are an expert AI Travel Concierge.</p>
                <p>Current user preferences: {'{'}<span className="text-orange-600">user_preferences</span>{'}'} ← personalisation</p>
                <br />
                <p>1. Extract: destination, dates, budget, interests</p>
                <p>2. If missing critical info → ask follow-up (friendly)</p>
                <p>3. Consider user's historical preferences</p>
                <p>4. When complete → output ```json {'{'} travel_plan {'}'}```</p>
                <p>5. Always respond in the user's language</p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">HITL (Human-in-the-Loop) Pattern</h3>
              <CodeBlock>{`User: "I want to go to Japan"
  → coordinator: destination=Japan, dates=MISSING
  → needs_user_input=True → graph pauses at END
  → Returns: "When are you planning to go?"

User: "May 1-5" (same thread_id → state restored)
  → coordinator: destination=Japan, dates=May1-5 ✓
  → needs_user_input=False
  → flight_search → hotel_search → ... → END`}</CodeBlock>
              <p className="text-xs text-gray-500 mt-2">
                <code className="bg-gray-100 px-1 rounded">thread_id</code> is the session key. LangGraph's MemorySaver checkpointer persists state after every node, enabling true multi-turn conversations.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Structured Output Extraction</h3>
              <p className="text-xs text-gray-600 mb-2">LLM outputs natural language + a JSON block. We extract the JSON with regex — more flexible than forcing JSON mode, better UX.</p>
              <CodeBlock>{`match = re.search(r"\`\`\`json\\s*(.*?)\\s*\`\`\`", content, re.DOTALL)
if match:
    plan_data = json.loads(match.group(1))`}</CodeBlock>
            </div>
          </div>
        </AccordionSection>

        {/* Features */}
        <AccordionSection id="features" icon={Zap} title="Feature Modules" color="from-green-500 to-teal-500">
          <div className="pt-4 space-y-4">
            {[
              {
                emoji: '💬', title: 'AI Chat Interface',
                items: ['Natural language in any language (Chinese/English)', 'Bubble-style conversation UI', 'Markdown rendering (lists, bold, tables)', 'Typing indicator + streaming SSE support', 'Quick-start suggestion prompts', 'Multi-turn memory via thread_id'],
              },
              {
                emoji: '📅', title: 'Trip Planner',
                items: ['Day-by-day itinerary in timeline format', 'Collapsible accordion per day', 'Trip status: Draft → Confirmed → Completed', 'Persistent storage in PostgreSQL'],
              },
              {
                emoji: '🏨', title: 'Hotel Comparison',
                items: ['Multi-platform price cards (Booking, Ctrip, Agoda, Google)', 'Filter by max price and location', 'Expandable price comparison per hotel', 'Star rating + user rating display'],
              },
              {
                emoji: '🧠', title: 'AI Memory (Preferences)',
                items: ['Travel style: Budget / Balanced / Luxury', 'Preferred transport, hotel stars, cuisine', 'Daily budget range (min/max)', 'learned_tags: AI-learned preference weights', 'All preferences injected into every AI response'],
              },
              {
                emoji: '🌤️', title: 'Right Panel (Auxiliary)',
                items: ['5-day weather forecast with icons', 'Budget tracker with category breakdown', 'Map placeholder (interactive map coming soon)', 'Explore Inspiration: trending destinations'],
              },
            ].map(({ emoji, title, items }) => (
              <div key={title} className="bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-800 text-sm mb-2">{emoji} {title}</h3>
                <ul className="space-y-1">
                  {items.map((item) => (
                    <li key={item} className="text-xs text-gray-600 flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">✓</span>{item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </AccordionSection>

        {/* Tech Stack */}
        <AccordionSection id="stack" icon={Database} title="Tech Stack" color="from-indigo-500 to-blue-500">
          <div className="pt-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Backend</h3>
              <Table
                headers={['Component', 'Technology', 'Purpose']}
                rows={[
                  ['Web framework', 'FastAPI + Uvicorn', 'Async REST API + SSE streaming'],
                  ['Agent orchestration', 'LangGraph 0.2', 'Multi-agent workflow, state persistence'],
                  ['LLM', 'Azure OpenAI gpt-4.1-mini', 'All AI reasoning'],
                  ['Database', 'PostgreSQL + SQLAlchemy async', 'User data, trips, preferences'],
                  ['Cache', 'Redis', 'API response caching (30min TTL)'],
                  ['Auth', 'JWT (python-jose + bcrypt)', 'Stateless authentication'],
                  ['Flight data', 'Amadeus + SerpAPI Google Flights', 'Multi-source flight search'],
                  ['Hotel data', 'SerpAPI Google Hotels + Amadeus', 'Multi-platform comparison'],
                  ['Weather', 'OpenWeatherMap API', '5-day forecast'],
                  ['Maps', 'AMap (Gaode) + Google Maps', 'Route planning'],
                ]}
              />
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Frontend</h3>
              <Table
                headers={['Component', 'Technology', 'Purpose']}
                rows={[
                  ['Framework', 'React 19 + TypeScript', 'UI components'],
                  ['Build tool', 'Vite 8', 'Fast dev server + bundling'],
                  ['Styling', 'Tailwind CSS v4', 'Utility-first CSS'],
                  ['State', 'Zustand', 'Global app state'],
                  ['HTTP', 'Axios', 'API calls with interceptors'],
                  ['Markdown', 'react-markdown', 'Render AI responses'],
                  ['Icons', 'lucide-react', 'UI icons'],
                  ['Toasts', 'react-hot-toast', 'Error/success notifications'],
                ]}
              />
            </div>
          </div>
        </AccordionSection>

        {/* API Reference */}
        <AccordionSection id="api" icon={Globe} title="API Reference" color="from-pink-500 to-rose-500">
          <div className="pt-4 space-y-4">
            {[
              {
                method: 'POST', path: '/api/v1/users/register', desc: 'Register a new user',
                body: '{ "email": "...", "password": "...", "nickname": "..." }',
              },
              {
                method: 'POST', path: '/api/v1/users/login', desc: 'Login and get JWT token',
                body: '{ "email": "...", "password": "..." }',
                response: '{ "access_token": "eyJ...", "token_type": "bearer" }',
              },
              {
                method: 'POST', path: '/api/v1/chat', desc: 'Chat with the AI agent',
                body: '{ "message": "I want to go to Tokyo", "thread_id": "optional" }',
                response: '{ "reply": "...", "thread_id": "uuid", "trip_plan": null | {...} }',
              },
              {
                method: 'POST', path: '/api/v1/chat/stream', desc: 'Streaming chat (SSE)',
                body: 'Same as /chat',
                response: 'data: <token>\\n\\n ... event: done\\ndata: [DONE]\\n\\n',
              },
              {
                method: 'GET', path: '/api/v1/trips', desc: 'List all trips for current user',
              },
              {
                method: 'GET/PUT', path: '/api/v1/preferences', desc: 'Get or update user preferences',
              },
            ].map(({ method, path, desc, body, response }) => (
              <div key={path} className="bg-gray-50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${method === 'GET' ? 'bg-green-100 text-green-700' : method === 'POST' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}>
                    {method}
                  </span>
                  <code className="text-xs font-mono text-gray-800">{path}</code>
                  <span className="text-xs text-gray-500">— {desc}</span>
                </div>
                {body && <p className="text-xs text-gray-500 font-mono bg-white rounded-lg px-3 py-2 border border-gray-200 mt-1">Body: {body}</p>}
                {response && <p className="text-xs text-gray-500 font-mono bg-white rounded-lg px-3 py-2 border border-gray-200 mt-1">Response: {response}</p>}
              </div>
            ))}
            <div className="bg-yellow-50 rounded-xl p-3 border border-yellow-100">
              <p className="text-xs text-yellow-800">
                <Shield className="w-3 h-3 inline mr-1" />
                All endpoints except <code>/register</code> and <code>/login</code> require: <code>Authorization: Bearer &lt;token&gt;</code>
              </p>
            </div>
          </div>
        </AccordionSection>

        {/* Setup */}
        <AccordionSection id="setup" icon={Terminal} title="Setup & Running" color="from-yellow-500 to-orange-500">
          <div className="pt-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Backend</h3>
              <CodeBlock>{`cd backend
cp .env.example .env        # fill in your API keys

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker-compose up -d postgres redis   # or install locally

uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs`}</CodeBlock>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Frontend</h3>
              <CodeBlock>{`cd frontend
npm install
npm run dev
# Open: http://localhost:5173`}</CodeBlock>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 text-sm mb-2">Required API Keys</h3>
              <Table
                headers={['Key', 'Required', 'Get it at']}
                rows={[
                  ['AZURE_OPENAI_API_KEY', '✅ Yes', 'Azure Portal'],
                  ['SERPAPI_API_KEY', '✅ Yes', 'serpapi.com'],
                  ['OPENWEATHER_API_KEY', '⭐ Recommended', 'openweathermap.org'],
                  ['AMAP_API_KEY', '⭐ Recommended', 'console.amap.com'],
                  ['GOOGLE_MAPS_API_KEY', '○ Optional', 'console.cloud.google.com'],
                  ['AMADEUS_CLIENT_ID/SECRET', '○ Optional', 'developers.amadeus.com'],
                ]}
              />
            </div>
            <div className="bg-green-50 rounded-xl p-3 border border-green-100">
              <p className="text-xs text-green-800">
                💡 Minimum to run: <strong>AZURE_OPENAI_API_KEY</strong> + <strong>SERPAPI_API_KEY</strong>. All other keys gracefully degrade.
              </p>
            </div>
          </div>
        </AccordionSection>

        {/* Team */}
        <AccordionSection id="team" icon={Users} title="Team & Responsibilities" color="from-teal-500 to-green-500">
          <div className="pt-4">
            <Table
              headers={['Role', 'Responsibilities']}
              rows={[
                ['Backend Dev 1', 'API integration (Amadeus, SerpAPI, AMap, OpenWeatherMap), external data services'],
                ['Backend Dev 2', 'Database design (PostgreSQL), user data storage, LangGraph state management'],
                ['Frontend Dev 1', 'UI design, chat interface, trip planner, responsive layout'],
                ['Frontend Dev 2', 'Voice input, NLP input handling, real-time updates (SSE)'],
                ['Data Scientist 1', 'Recommendation algorithm design, user preference learning'],
                ['Data Scientist 2', 'Model training & evaluation, personalisation optimisation'],
                ['State Management', 'LangGraph workflow design, node/edge definition, multi-step flow control'],
                ['Testing & Deployment', 'Unit/integration tests, CI/CD, cloud deployment, monitoring'],
              ]}
            />
            <div className="mt-4 text-center">
              <a href="https://github.com/fu-si-yuan-collab/7066_AI_Travel_Agent" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-xs text-blue-600 hover:text-blue-800 transition-colors">
                <ExternalLink className="w-3 h-3" />
                View on GitHub: fu-si-yuan-collab/7066_AI_Travel_Agent
              </a>
            </div>
          </div>
        </AccordionSection>

      </div>

      <p className="text-center text-xs text-gray-400 mt-8 pb-4">
        Built for MSBA 7066 — Large Language Models · HKU Business School
      </p>
    </div>
  )
}
