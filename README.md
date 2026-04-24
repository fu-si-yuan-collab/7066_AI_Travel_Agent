# 🌏 AI Travel Agent

> **MSBA 7066 Group Project** · HKU Business School
> A full-stack AI-powered travel concierge — one platform for flights, hotels, itineraries, weather, navigation, and personalised recommendations.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript)](https://www.typescriptlang.org)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-gpt--4.1--mini-0078D4?logo=microsoft-azure)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

---

## ✈️ What It Does

Tell the AI where you want to go — it handles everything else.

```
User: "I want 5 days in Tokyo, budget ¥10,000, leaving May 1st"

AI:  ✅ Searches flights (Amadeus + Google Flights)
     ✅ Compares hotels across Booking.com, Ctrip, Agoda
     ✅ Checks weather for your travel dates
     ✅ Plans day-by-day itinerary with routes
     ✅ Breaks down your budget into 3 tiers
     ✅ Remembers your preferences for next time
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              React Frontend (port 5173)              │
│  Chat │ Trips │ Hotels │ Preferences │ Docs          │
└───────────────────────┬─────────────────────────────┘
                        │ REST API + SSE
┌───────────────────────▼─────────────────────────────┐
│              FastAPI Backend (port 8000)             │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │         LangGraph Multi-Agent System         │    │
│  │                                              │    │
│  │  coordinator → flight → hotel → weather      │    │
│  │               → navigation → itinerary       │    │
│  │                    → budget → END            │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  PostgreSQL (user data)    Redis (API cache)         │
└──────────────────────────────────────────────────────┘
         │              │              │
   Azure OpenAI      SerpAPI     OpenWeatherMap
   gpt-4.1-mini   Flights/Hotels    Weather
                        │
                  AMap / Google Maps
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+, Node.js 18+, PostgreSQL 16, Redis 7

### Backend
```bash
cd backend
cp .env.example .env        # fill in your API keys
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker-compose up -d postgres redis
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
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
cd backend && docker-compose up --build
```

---

## 🔑 Required API Keys

| Key | Required | Get it at |
|-----|---------|-----------|
| `AZURE_OPENAI_API_KEY` | ✅ | Azure Portal |
| `SERPAPI_API_KEY` | ✅ | [serpapi.com](https://serpapi.com) |
| `OPENWEATHER_API_KEY` | ⭐ | [openweathermap.org](https://openweathermap.org/api) |
| `AMAP_API_KEY` | ⭐ | [console.amap.com](https://console.amap.com) |
| `GOOGLE_MAPS_API_KEY` | ○ | [Google Cloud Console](https://console.cloud.google.com) |
| `AMADEUS_CLIENT_ID/SECRET` | ○ | [developers.amadeus.com](https://developers.amadeus.com) |

Copy `backend/.env.example` → `backend/.env` and fill in your keys.

---

## 📦 Project Structure

```
7066_AI_Travel_Agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py          # LangGraph workflow definition
│   │   │   ├── state.py          # Shared AgentState
│   │   │   ├── nodes/            # 7 specialist agent nodes
│   │   │   └── prompts/          # System prompt templates
│   │   ├── api/routes/           # FastAPI endpoints
│   │   ├── services/             # External API integrations
│   │   ├── models/               # SQLAlchemy ORM + Pydantic schemas
│   │   ├── db/repositories/      # Data access layer
│   │   └── core/                 # JWT auth, Redis cache, LLM factory
│   ├── tests/                    # pytest test suite
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatPanel.tsx     # AI chat interface
│       │   ├── HotelsPanel.tsx   # Multi-platform hotel comparison
│       │   ├── PreferencesPanel.tsx  # AI memory / user preferences
│       │   ├── TripsPanel.tsx    # Trip history
│       │   ├── DocsPage.tsx      # In-app documentation
│       │   └── RightPanel.tsx    # Weather, budget, map, inspiration
│       ├── store/                # Zustand state management
│       ├── api/                  # Axios API client
│       └── types/                # TypeScript interfaces
├── DOCUMENTATION.md              # Full project documentation
└── README.md
```

---

## 🤖 Agent Design

The system uses **LangGraph StateGraph** — each node is an independent specialist agent sharing a single `AgentState`:

| Node | Role | Temperature |
|------|------|-------------|
| `coordinator` | Parse intent, extract plan, HITL routing | 0.3 |
| `flight_search` | Amadeus + Google Flights aggregation | — |
| `hotel_search` | Multi-platform hotel comparison | — |
| `weather_check` | OpenWeatherMap 5-day forecast | — |
| `navigation` | AMap / Google Maps route planning | — |
| `plan_itinerary` | Day-by-day itinerary synthesis | 0.4 |
| `analyze_budget` | Cost breakdown, 3-tier suggestions | 0.2 |

**HITL (Human-in-the-Loop):** If the user's message is missing critical info, the graph pauses and returns a follow-up question. The same `thread_id` resumes the conversation with full context restored.

See [`DOCUMENTATION.md`](./DOCUMENTATION.md) for the complete design writeup.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph 0.2 + LangChain |
| LLM | Azure OpenAI gpt-4.1-mini |
| Backend | FastAPI + Uvicorn (async) |
| Database | PostgreSQL + SQLAlchemy async |
| Cache | Redis |
| Auth | JWT (python-jose + bcrypt) |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v4 |
| State | Zustand |

---

## 👥 Team

| Role | Responsibilities |
|------|----------------|
| Backend Dev 1 | API integration (Amadeus, SerpAPI, AMap, OpenWeatherMap) |
| Backend Dev 2 | Database design, LangGraph state management |
| Frontend Dev 1 | UI design, chat interface, responsive layout |
| Frontend Dev 2 | Voice input, NLP handling, real-time SSE updates |
| Data Scientist 1 | Recommendation algorithm, preference learning |
| Data Scientist 2 | Model training, personalisation optimisation |
| State Management | LangGraph workflow, node/edge design |
| Testing & Deployment | Tests, CI/CD, cloud deployment |

---

*Built with ❤️ for MSBA 7066 — Large Language Models · HKU Business School*
