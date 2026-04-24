# AI Travel Agent — Complete Project Documentation

> **MSBA 7066 Group Project** · HKU Business School
> A full-stack AI-powered travel concierge built with LangGraph, FastAPI, and React.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Agent Design & Prompt Engineering](#3-agent-design--prompt-engineering)
4. [Feature Modules](#4-feature-modules)
5. [Tech Stack](#5-tech-stack)
6. [API Reference](#6-api-reference)
7. [Setup & Running](#7-setup--running)
8. [Team & Responsibilities](#8-team--responsibilities)

---

## 1. Project Overview

### Problem Statement

Modern travellers face three core pain points:

| Pain Point | Description |
|-----------|-------------|
| **Price fragmentation** | Hotel and flight prices differ across Ctrip, Booking.com, Agoda, Google Hotels — users must check each manually |
| **App switching fatigue** | Planning, navigation, weather, and booking are scattered across 5+ apps |
| **No personalisation memory** | Platforms forget your preferences; every trip starts from scratch |

### Our Solution

A single AI Travel Concierge that:
- **Understands** natural language requests ("I want 5 days in Tokyo, budget ¥10,000")
- **Searches** flights and hotels across multiple platforms simultaneously
- **Plans** a complete day-by-day itinerary with weather, routes, and budget breakdown
- **Remembers** your preferences and improves recommendations over time

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  AuthPage │ ChatPanel │ TripsPanel │ HotelsPanel │ Preferences  │
└─────────────────────────┬───────────────────────────────────────┘
                          │  REST API + SSE Streaming
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│                                                                  │
│  /api/v1/chat  ──────────────────────────────────────────────┐  │
│  /api/v1/trips                                               │  │
│  /api/v1/users                                               │  │
│  /api/v1/preferences                                         │  │
│                                                              ▼  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              LangGraph Agent System                      │    │
│  │                                                          │    │
│  │  [coordinator] ──no info──► END (ask user)              │    │
│  │       │ has info                                         │    │
│  │       ▼                                                  │    │
│  │  [flight_search]──►[hotel_search]──►[weather_check]     │    │
│  │                                          │               │    │
│  │                                    [navigation]          │    │
│  │                                          │               │    │
│  │                                  [plan_itinerary]        │    │
│  │                                          │               │    │
│  │                                  [analyze_budget]        │    │
│  │                                          │               │    │
│  │                                         END              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  PostgreSQL (user data, trips)    Redis (API response cache)     │
└─────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   Azure OpenAI      SerpAPI         OpenWeatherMap
   (gpt-4.1-mini)  (Flights/Hotels)  (Weather)
                          │
                    AMap / Google Maps
                      (Navigation)
```

### Data Flow

1. User sends a message via the chat interface
2. FastAPI receives it, loads user preferences from PostgreSQL
3. The message enters the LangGraph graph with a `thread_id` (session ID)
4. `coordinator` node parses intent → if info is incomplete, returns a follow-up question
5. Once complete, specialist nodes run sequentially: search → plan → budget
6. Results are cached in Redis (30 min TTL) to avoid redundant API calls
7. Final response (text + structured trip plan) is returned to the frontend

---

## 3. Agent Design & Prompt Engineering

### 3.1 Multi-Agent Architecture

The system uses **LangGraph StateGraph** — a directed graph where each node is a specialist AI agent. All nodes share a single `AgentState` object.

```python
@dataclass
class AgentState:
    messages: list[AnyMessage]        # conversation history (auto-accumulated)
    travel_plan: TravelPlan           # structured plan extracted from user input
    user_preferences: dict            # loaded from DB for personalisation
    needs_user_input: bool            # HITL interrupt flag
    flight_results: list[dict]        # filled by flight_search node
    hotel_results: list[dict]         # filled by hotel_search node
    weather_data: dict                # filled by weather_check node
    navigation_data: dict             # filled by navigation node
    itinerary: dict                   # filled by plan_itinerary node
    budget_breakdown: dict            # filled by analyze_budget node
```

Each node **reads what it needs, writes only its own fields** — clean separation of concerns.

### 3.2 Node Responsibilities

| Node | Role | Key Output |
|------|------|-----------|
| `coordinator` | Parse user intent, extract structured plan, decide routing | `travel_plan`, `needs_user_input` |
| `flight_search` | Query Amadeus + Google Flights, sort by price | `flight_results` |
| `hotel_search` | Query Google Hotels + Amadeus, multi-platform comparison | `hotel_results` |
| `weather_check` | Fetch 5-day forecast from OpenWeatherMap | `weather_data` |
| `navigation` | Plan routes between activities via AMap/Google Maps | `navigation_data` |
| `plan_itinerary` | Synthesise all data into day-by-day itinerary | `itinerary` |
| `analyze_budget` | Break down costs, compare against budget, suggest 3 tiers | `budget_breakdown` |

### 3.3 Prompt Engineering Strategies

#### Coordinator — Intent Extraction + Routing

```
System: You are an expert AI Travel Concierge.
        Current user preferences: {user_preferences}   ← personalisation injection

Guidelines:
1. Extract: destination, dates, budget, interests from natural language
2. If missing critical info → ask follow-up (concise, friendly)
3. Consider user's historical preferences
4. When info is complete → output ```json { travel_plan } ```
5. Always respond in the user's language
```

**Key design choices:**
- **Structured output via JSON block** — LLM can explain first, then give JSON. More natural than forcing JSON mode.
- **User preferences injected** — every response is personalised from the first message
- **Language mirroring** — Chinese input → Chinese response, English input → English response

#### Itinerary Planner — Context Synthesis

```
System: You are an Itinerary Architect.
        [All search results passed as context: flights, hotels, weather, activities, routes]

Requirements:
- Respect budget and travel style
- Account for weather conditions
- Optimise routes to minimise travel time
- Include meal recommendations near activity locations
- Output structured JSON itinerary
```

**Temperature settings by node:**

| Node | Temperature | Reason |
|------|------------|--------|
| coordinator | 0.3 | Stable intent parsing |
| plan_itinerary | 0.4 | Slightly creative for richer suggestions |
| analyze_budget | 0.2 | Accurate number calculations |

### 3.4 HITL (Human-in-the-Loop) Pattern

```
User: "I want to go to Japan"
         │
         ▼
  coordinator: destination=Japan, dates=MISSING
         │
         ▼  needs_user_input=True
  Graph pauses at END
         │
         ▼
  Returns: "Great choice! When are you planning to go, and how many days?"
         │
  User: "May 1-5, 5 days"
         │
         ▼  (same thread_id → LangGraph restores state)
  coordinator: destination=Japan, dates=May1-5 ✓
         │
         ▼  needs_user_input=False
  → flight_search → hotel_search → ... → END
```

The `thread_id` is the session key. LangGraph's `MemorySaver` checkpointer persists state after every node, so conversations can be resumed across requests.

### 3.5 Caching Strategy

```
User request
    │
    ▼
Redis cache hit? ──yes──► Return cached result (instant)
    │ no
    ▼
Call external API
    │
    ▼
Store in Redis (TTL: flights=30min, hotels=30min, weather=60min, activities=24h)
    │
    ▼
Return result
```

Cache keys are MD5 hashes of search parameters, ensuring identical queries always hit the cache.

---

## 4. Feature Modules

### 4.1 AI Chat Interface

- Natural language input in any language
- Bubble-style conversation UI (similar to ChatGPT)
- Markdown rendering for structured responses (lists, bold, tables)
- Typing indicator during AI processing
- Quick-start suggestion prompts
- Streaming support via Server-Sent Events (SSE)
- Multi-turn conversation with memory (same `thread_id`)

### 4.2 Trip Planner

- Displays AI-generated day-by-day itinerary
- Timeline format with activity cards
- Collapsible accordion per day
- Trip status tracking: Draft → Confirmed → Completed
- Persistent storage in PostgreSQL

### 4.3 Hotel Comparison

- Cards showing hotel name, stars, user rating, price per night
- Multi-platform price comparison (Booking.com, Ctrip, Agoda, Google Hotels)
- Filter by: max price per night, location/district
- Expandable price comparison panel per hotel
- Direct booking link

### 4.4 User Preference System (AI Memory)

- Travel style: Budget / Balanced / Luxury
- Preferred transport: Any / Flight / Train / Drive
- Hotel star preference (slider 1–5★)
- Daily budget range (min/max)
- Favourite cuisine (multi-select tags)
- `learned_tags` — AI-learned preference weights updated by the recommendation engine
  - Example: `{"beach": 0.8, "museum": 0.3, "street_food": 0.9}`
- All preferences are injected into every AI response for personalisation

### 4.5 Right Panel (Auxiliary Info)

- **Weather widget**: 5-day forecast with temperature, precipitation probability
- **Budget tracker**: Visual progress bar, breakdown by category (flights, hotels, food, activities)
- **Map placeholder**: Interactive map (coming soon)
- **Explore Inspiration**: Trending destination cards (Airbnb-style)

---

## 5. Tech Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web framework | FastAPI + Uvicorn | Async REST API + SSE |
| Agent orchestration | LangGraph 0.2 | Multi-agent workflow, state persistence |
| LLM | Azure OpenAI (gpt-4.1-mini) | All AI reasoning |
| LLM client | LangChain + langchain-openai | LLM abstraction layer |
| Database | PostgreSQL + SQLAlchemy (async) | User data, trips, preferences |
| Cache | Redis | API response caching |
| Auth | JWT (python-jose + passlib/bcrypt) | Stateless authentication |
| HTTP client | httpx + tenacity | Async API calls with retry |
| Flight data | Amadeus API + SerpAPI Google Flights | Multi-source flight search |
| Hotel data | SerpAPI Google Hotels + Amadeus | Multi-platform hotel comparison |
| Weather | OpenWeatherMap API | 5-day forecast |
| Maps | AMap (Gaode) + Google Maps | Route planning |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 19 + TypeScript | UI components |
| Build tool | Vite 8 | Fast dev server + bundling |
| Styling | Tailwind CSS v4 | Utility-first CSS |
| State management | Zustand | Global app state |
| HTTP client | Axios | API calls |
| Markdown | react-markdown | Render AI responses |
| Icons | lucide-react | UI icons |
| Notifications | react-hot-toast | Toast messages |

---

## 6. API Reference

### Authentication

```
POST /api/v1/users/register
Body: { "email": "...", "password": "...", "nickname": "..." }
Response: { "id": "...", "email": "...", "nickname": "..." }

POST /api/v1/users/login
Body: { "email": "...", "password": "..." }
Response: { "access_token": "eyJ...", "token_type": "bearer" }
```

All subsequent requests require: `Authorization: Bearer <token>`

### Chat

```
POST /api/v1/chat
Body: { "message": "I want to go to Tokyo for 5 days", "thread_id": "optional-uuid" }
Response: {
  "reply": "Great! When are you planning to go?",
  "thread_id": "uuid-for-this-session",
  "trip_plan": null | { itinerary, budget, ... }
}

POST /api/v1/chat/stream          ← Server-Sent Events
Body: same as above
Stream: data: <token>\n\n  ...  event: done\ndata: [DONE]\n\n
```

### Trips

```
GET  /api/v1/trips                 ← list all trips
POST /api/v1/trips                 ← create trip
GET  /api/v1/trips/{id}            ← get trip details
PATCH /api/v1/trips/{id}/status    ← update status
DELETE /api/v1/trips/{id}          ← delete trip
```

### Preferences

```
GET /api/v1/preferences            ← get current preferences
PUT /api/v1/preferences            ← update preferences
Body: {
  "preferred_travel_style": "balanced",
  "preferred_transport": "any",
  "preferred_hotel_stars": 3.0,
  "daily_budget_low": 300,
  "daily_budget_high": 1000,
  "currency": "CNY"
}
```

---

## 7. Setup & Running

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Redis 7

### Backend

```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker)
docker-compose up -d postgres redis

# Run the server
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:5173
```

### Docker (one command)

```bash
cd backend
docker-compose up --build
```

### Required API Keys

| Key | Required | Get it at |
|-----|---------|-----------|
| `AZURE_OPENAI_API_KEY` | ✅ Yes | Azure Portal |
| `SERPAPI_API_KEY` | ✅ Yes | serpapi.com |
| `OPENWEATHER_API_KEY` | Recommended | openweathermap.org |
| `AMAP_API_KEY` | Recommended | console.amap.com |
| `GOOGLE_MAPS_API_KEY` | Optional | console.cloud.google.com |
| `AMADEUS_CLIENT_ID/SECRET` | Optional | developers.amadeus.com |

---

## 8. Team & Responsibilities

| Role | Responsibilities |
|------|----------------|
| Backend Dev 1 | API integration (Amadeus, SerpAPI, AMap, OpenWeatherMap), external data services |
| Backend Dev 2 | Database design (PostgreSQL), user data storage, state management (LangGraph) |
| Frontend Dev 1 | UI design, chat interface, trip planner, responsive layout |
| Frontend Dev 2 | Voice input integration, NLP input handling, real-time updates |
| Data Scientist 1 | Recommendation algorithm design, user preference learning |
| Data Scientist 2 | Model training & evaluation, personalisation optimisation |
| State Management | LangGraph workflow design, node/edge definition, multi-step flow control |
| Testing & Deployment | Unit/integration tests, CI/CD, cloud deployment, monitoring |

---

*Built with ❤️ for MSBA 7066 — Large Language Models · HKU Business School*
