# AI Travel Agent - Backend

> LangGraph-powered AI Travel Concierge backend service

Reference project: [nirbar1985/ai-travel-agent](https://github.com/nirbar1985/ai-travel-agent) (GitHub 692 stars)

## Architecture

```
                    ┌─────────────────┐
                    │   FastAPI App    │  ← REST API + SSE Streaming
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │ API Routes│  │ Auth/JWT │  │ Redis Cache  │
        └─────┬────┘  └──────────┘  └──────────────┘
              │
              ▼
    ┌───────────────────────────────────────────┐
    │          LangGraph Agent System           │
    │                                           │
    │  coordinator → flight → hotel → weather   │
    │                    → navigation → itinerary│
    │                         → budget → END    │
    │                                           │
    │  State: AgentState (auto-persisted)       │
    └────────────────┬──────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
   ┌──────────┐ ┌─────────┐ ┌─────────┐
   │ Services │ │   DB    │ │  LLM    │
   │(API Int.)│ │(Postgres)│ │(Azure)  │
   └──────────┘ └─────────┘ └─────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| Agent Orchestration | LangGraph + LangChain |
| LLM | **Azure OpenAI** (gpt-4.1-mini) |
| Database | PostgreSQL (async via SQLAlchemy) |
| Cache | Redis |
| Auth | JWT (python-jose) |
| External APIs | Amadeus, SerpAPI, OpenWeatherMap, AMap/Google Maps |
| Container | Docker + docker-compose |

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Environment config (pydantic-settings)
│   ├── api/routes/             # REST API endpoints
│   │   ├── chat.py             # Main chat interface (invoke/stream)
│   │   ├── trips.py            # Trip CRUD
│   │   ├── users.py            # Register / Login
│   │   └── preferences.py     # User preference management
│   ├── agents/                 # LangGraph agent system
│   │   ├── graph.py            # Graph definition & compilation
│   │   ├── state.py            # AgentState & TravelPlan
│   │   ├── nodes/              # Graph nodes (one per specialist)
│   │   │   ├── coordinator.py  # Parses user intent
│   │   │   ├── flight_agent.py # Flight search
│   │   │   ├── hotel_agent.py  # Hotel multi-platform comparison
│   │   │   ├── weather_agent.py# Weather forecast
│   │   │   ├── navigation_agent.py # Route planning
│   │   │   ├── itinerary_agent.py  # Day-by-day planner
│   │   │   └── budget_agent.py     # Cost breakdown
│   │   └── prompts/templates.py    # System prompts
│   ├── services/               # External API integrations
│   │   ├── flight_service.py   # Amadeus + Google Flights
│   │   ├── hotel_service.py    # Multi-platform hotel comparison
│   │   ├── weather_service.py  # OpenWeatherMap
│   │   ├── maps_service.py     # AMap + Google Maps
│   │   └── activity_service.py # POI / activity search
│   ├── models/                 # SQLAlchemy ORM + Pydantic schemas
│   │   ├── user.py / trip.py / preference.py / hotel.py / flight.py
│   │   └── schemas.py          # Request/response validation
│   ├── db/
│   │   ├── database.py         # Async engine & session
│   │   └── repositories/       # Data access layer
│   └── core/
│       ├── security.py         # JWT auth
│       └── cache.py            # Redis wrapper
├── tests/                      # pytest test suite
├── docker-compose.yml          # One-command local deployment
├── Dockerfile
├── requirements.txt
└── .env.example                # Environment variable template
```

## API Keys Required

### Required (core functionality)

| Key | Purpose | Free Tier | Sign Up |
|-----|---------|-----------|---------|
| `AZURE_OPENAI_API_KEY` | Powers all LLM agent nodes | Pay-as-you-go | Azure Portal |
| `SERPAPI_API_KEY` | Google Flights/Hotels/POI search | 100 searches/month | https://serpapi.com |

### Recommended (full experience)

| Key | Purpose | Free Tier | Sign Up |
|-----|---------|-----------|---------|
| `OPENWEATHER_API_KEY` | Weather forecasts | 1000 calls/day | https://openweathermap.org |
| `AMAP_API_KEY` | Gaode map navigation (China) | 5000 calls/day | https://console.amap.com |

### Optional (enhanced)

| Key | Purpose |
|-----|---------|
| `AMADEUS_CLIENT_ID/SECRET` | Backup flight/hotel data source |
| `GOOGLE_MAPS_API_KEY` | International route navigation |
| `LANGCHAIN_API_KEY` | LangSmith tracing & debugging |

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys

docker-compose up --build
# API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

### Option 2: Local Development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys

# Start only database and cache via Docker
docker-compose up -d postgres redis

# Start the backend server with hot-reload
uvicorn app.main:app --reload --port 8000
```

### Option 3: Fully Local (no Docker)

```bash
# Install PostgreSQL and Redis via Homebrew
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis
createdb travel_agent

# Then run the server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/users/register` | Register a new user |
| `POST` | `/api/v1/users/login` | Login and get JWT token |
| `POST` | `/api/v1/chat` | Chat with the AI travel agent |
| `POST` | `/api/v1/chat/stream` | Streaming chat (SSE) |
| `GET/POST` | `/api/v1/trips` | List / Create trips |
| `GET` | `/api/v1/trips/{id}` | Get trip details |
| `GET/PUT` | `/api/v1/preferences` | Manage user preferences |
| `GET` | `/health` | Health check |

## Verification

After starting the server, test the flow:

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com", "password":"123456", "nickname":"Tester"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com", "password":"123456"}'
# Returns {"access_token": "eyJ..."}

# 3. Chat with the agent
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{"message":"I want to visit Tokyo for 5 days during Golden Week, budget 8000 CNY"}'
```

## LangGraph Workflow

```
User Message
     │
     ▼
┌─────────────┐     needs more info?
│ Coordinator  │────────────────────► Return question to user
└──────┬──────┘     (HITL interrupt)
       │ has enough info
       ▼
┌──────────────┐  ┌──────────────┐  ┌───────────────┐
│Flight Search │─►│ Hotel Search │─►│ Weather Check  │
└──────────────┘  └──────────────┘  └───────┬───────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  Navigation  │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  Itinerary   │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │   Budget     │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    Complete response
```

## Key Design Decisions

1. **LangGraph StateGraph** — Each function is an independent node sharing `AgentState`, with state persistence and HITL interrupt support
2. **Azure OpenAI** — Uses `AzureChatOpenAI` from langchain-openai, compatible with Azure deployments
3. **Multi-platform comparison** — Hotels/flights aggregated from multiple sources to solve price inconsistency
4. **Dual map support** — Gaode (AMap) for domestic China, Google Maps for international
5. **Redis caching** — API responses cached for 30 minutes to avoid redundant requests
6. **Preference learning** — `learned_tags` JSON field for the ML team to store learned user preferences
7. **Async everywhere** — Full async stack (AsyncIO + SQLAlchemy async + httpx)

## Team Integration Points

- **Frontend team**: Integrate with `POST /api/v1/chat` (regular) and `POST /api/v1/chat/stream` (SSE streaming)
- **ML team**: Extend `UserPreference.learned_tags` field, inject recommendation results in `coordinator_node`
- **State management**: Extend the graph in `app/agents/graph.py` to add new nodes or conditional branches
- **Testing & deployment**: Use `docker-compose.yml` and the `tests/` directory
