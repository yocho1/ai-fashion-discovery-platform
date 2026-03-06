<div align="center">

# AI Fashion Discovery Platform

**Intelligent fashion analysis and outfit recommendation engine powered by computer vision and machine learning.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Demo Video](https://drive.google.com/file/d/1KHnAltEHsUdiU9IhahY0SHhX8rNExFWI/view?usp=drive_link) &bull; [API Docs (local)](http://localhost:8000/docs) &bull; [Getting Started](#-getting-started)

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Demo](#-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [Features by Sprint](#-features-by-sprint)
- [Environment Variables](#-environment-variables)
- [Docker Deployment](#-docker-deployment)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

AI Fashion Discovery Platform is a full-stack application that lets users upload fashion images, analyze them with AI-powered computer vision, build a virtual closet, and receive intelligent outfit recommendations based on clothing embeddings and compatibility scoring.

**Key capabilities:**

- **AI Vision Analysis** — Automatically identifies clothing type, categories, and attributes using GPT-4o-mini via OpenRouter
- **Smart Recommendations** — Generates outfit pairings using vector embeddings and cosine similarity scoring
- **Virtual Closet** — Organize analyzed clothing items into a personal wardrobe
- **Outfit Management** — Save, name, and manage AI-generated outfit combinations
- **Secure Authentication** — JWT-based auth with Argon2 password hashing

---

## Demo

> **[Watch the full demo on Google Drive](https://drive.google.com/file/d/1KHnAltEHsUdiU9IhahY0SHhX8rNExFWI/view?usp=drive_link)**

The demo showcases the complete user flow: registration, image upload, AI analysis, closet management, recommendation generation, and outfit saving.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
│                     Next.js 14 + React 18                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │   Auth   │ │  Images  │ │  Vision  │ │  Recommendations  │  │
│  │  Routes  │ │  Routes  │ │  Routes  │ │      Routes       │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬──────────┘  │
│       │             │            │                 │             │
│  ┌────▼─────────────▼────────────▼─────────────────▼──────────┐ │
│  │                    Service Layer                            │ │
│  │  AuthService · ImageService · VisionService                │ │
│  │  EmbeddingService · RecommendationService · CacheService   │ │
│  └────┬──────────────────────────┬────────────────────────────┘ │
│       │                          │                              │
│  ┌────▼────────┐  ┌─────────────▼──────────┐  ┌─────────────┐  │
│  │ PostgreSQL  │  │  OpenRouter API         │  │    Redis     │  │
│  │   / SQLite  │  │  (GPT-4o-mini Vision)  │  │   Cache      │  │
│  └─────────────┘  └────────────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer         | Technology                          | Purpose                        |
| ------------- | ----------------------------------- | ------------------------------ |
| **Frontend**  | Next.js 14, React 18, TypeScript    | SPA with SSR support           |
| **Backend**   | FastAPI, Python 3.12, Uvicorn       | Async REST API                 |
| **Database**  | PostgreSQL 16 / SQLite              | Persistent storage             |
| **ORM**       | SQLAlchemy 2.0                      | Database abstraction           |
| **Auth**      | python-jose (JWT), passlib + Argon2 | Token auth + password hashing  |
| **AI/Vision** | OpenRouter API (GPT-4o-mini)        | Clothing analysis              |
| **ML**        | scikit-learn, NumPy                 | Embeddings + cosine similarity |
| **Caching**   | Redis 7                             | Response caching layer         |
| **Storage**   | Local filesystem / S3-ready         | Image persistence              |
| **Infra**     | Docker Compose                      | Container orchestration        |

---

## Project Structure

```
AI-Fashion-Discovery-Platform/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py              # Register, login, token refresh
│   │   │   ├── health.py            # Liveness + readiness probes
│   │   │   ├── images.py            # Upload, list, get, delete, serve
│   │   │   ├── vision.py            # AI analysis trigger + results
│   │   │   └── recommendations.py   # Clothing items, outfits, reco engine
│   │   └── *_schemas.py             # Pydantic request/response models
│   ├── core/
│   │   └── config.py                # Centralized settings (Pydantic BaseSettings)
│   ├── db/
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   └── session.py               # DB engine + session factory
│   ├── services/
│   │   ├── auth_service.py          # JWT generation, password hashing
│   │   ├── cache_service.py         # Redis caching with graceful fallback
│   │   ├── embedding_service.py     # TF-IDF clothing embeddings
│   │   ├── health_service.py        # System health checks
│   │   ├── image_service.py         # Image validation + metadata
│   │   ├── recommendation_service.py # Outfit compatibility scoring
│   │   ├── storage_service.py       # File storage abstraction
│   │   └── vision_service.py        # OpenRouter vision API integration
│   ├── tests/                       # Pytest unit + integration tests
│   ├── workers/                     # Background task workers
│   ├── main.py                      # FastAPI app factory
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Main SPA (auth, dashboard, closet)
│   │   ├── layout.tsx               # Root layout with metadata
│   │   └── globals.css              # Professional e-commerce theme
│   ├── lib/
│   │   ├── api.ts                   # Type-safe API client
│   │   └── types.ts                 # TypeScript interfaces
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml               # Full-stack orchestration
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** and npm
- **PostgreSQL 16** (or use SQLite for local dev)
- **Redis 7** (optional — app degrades gracefully without it)
- **OpenRouter API key** — [Get one here](https://openrouter.ai/keys)

### 1. Clone the repository

```bash
git clone https://github.com/yocho1/AI-Fashion-Discovery-Platform.git
cd AI-Fashion-Discovery-Platform
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv ../.venv
# Windows
..\.venv\Scripts\activate
# macOS/Linux
source ../.venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env   # if .env.example exists, otherwise create .env manually
```

Create `backend/.env` with your settings:

```env
SECRET_KEY=your-secret-key-here
OPENROUTER_API_KEY=sk-or-v1-your-key-here
VISION_MODEL=openai/gpt-4o-mini
DATABASE_URL=sqlite:///./fashion_dev.db
```

```bash
# Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## API Reference

### Health

| Method | Endpoint        | Description                  |
| ------ | --------------- | ---------------------------- |
| `GET`  | `/health/live`  | Liveness probe               |
| `GET`  | `/health/ready` | Readiness probe (DB + Redis) |

### Authentication

| Method | Endpoint         | Description                  |
| ------ | ---------------- | ---------------------------- |
| `POST` | `/auth/register` | Create account (returns JWT) |
| `POST` | `/auth/login`    | Sign in (returns JWT)        |
| `POST` | `/auth/refresh`  | Refresh access token         |

### Images

| Method   | Endpoint            | Description                            |
| -------- | ------------------- | -------------------------------------- |
| `POST`   | `/images/upload`    | Upload image (JPEG/PNG/WebP, max 10MB) |
| `GET`    | `/images/my-images` | List user's images (paginated)         |
| `GET`    | `/images/{id}`      | Get image metadata                     |
| `GET`    | `/images/{id}/file` | Serve image file                       |
| `DELETE` | `/images/{id}`      | Delete image                           |

### Vision Analysis

| Method | Endpoint                      | Description                   |
| ------ | ----------------------------- | ----------------------------- |
| `POST` | `/vision/analyze`             | Start async AI analysis       |
| `GET`  | `/vision/analyses/{image_id}` | Get analysis result           |
| `GET`  | `/vision/my-analyses`         | List all analyses (paginated) |

### Recommendations & Closet

| Method   | Endpoint                           | Description                     |
| -------- | ---------------------------------- | ------------------------------- |
| `POST`   | `/recommendations/clothing-items`  | Add item to closet              |
| `GET`    | `/recommendations/clothing-items`  | List closet items               |
| `POST`   | `/recommendations/recommendations` | Generate outfit recommendations |
| `POST`   | `/recommendations/outfits`         | Save outfit                     |
| `GET`    | `/recommendations/outfits`         | List saved outfits              |
| `DELETE` | `/recommendations/outfits/{id}`    | Delete outfit                   |

> All authenticated endpoints accept the JWT token as a query parameter: `?authorization=Bearer+<token>`

---

## Features by Sprint

| Sprint | Milestone             | Deliverables                                                                        |
| ------ | --------------------- | ----------------------------------------------------------------------------------- |
| **1**  | Project Foundation    | FastAPI scaffolding, PostgreSQL/SQLite, Docker Compose, health endpoints            |
| **2**  | Authentication        | User registration, JWT login/refresh, Argon2 hashing, protected routes              |
| **3**  | Image Management      | Upload with validation (type, size, dimensions), metadata persistence, file storage |
| **4**  | AI Vision             | OpenRouter integration, GPT-4o-mini vision analysis, async background processing    |
| **5**  | Recommendation Engine | TF-IDF clothing embeddings, cosine similarity, outfit compatibility scoring         |
| **6**  | Caching & Performance | Redis caching layer, graceful degradation, cache invalidation                       |
| **7**  | Frontend MVP          | Next.js SPA, auth flow, image gallery, AI analysis UI, closet & outfit management   |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable                      | Default                    | Description                              |
| ----------------------------- | -------------------------- | ---------------------------------------- |
| `SECRET_KEY`                  | —                          | JWT signing key (required)               |
| `DATABASE_URL`                | `postgresql+psycopg://...` | Database connection string               |
| `REDIS_URL`                   | `redis://localhost:6379/0` | Redis connection (optional)              |
| `OPENROUTER_API_KEY`          | —                          | OpenRouter API key (required for vision) |
| `VISION_MODEL`                | `openai/gpt-4o-mini`       | Vision model identifier                  |
| `LOCAL_STORAGE_PATH`          | `./uploads`                | Image storage directory                  |
| `MAX_FILE_SIZE`               | `10485760`                 | Max upload size in bytes (10MB)          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                       | JWT access token TTL                     |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                        | JWT refresh token TTL                    |

### Frontend (`frontend/.env.local`)

| Variable                   | Default                 | Description     |
| -------------------------- | ----------------------- | --------------- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

---

## Docker Deployment

The full backend stack (API + PostgreSQL + Redis) can be deployed with Docker Compose:

```bash
# Build and start all services
docker compose up --build -d

# Check service health
docker compose ps

# View API logs
docker compose logs -f api

# Run tests inside the container
docker compose exec api pytest -q

# Tear down
docker compose down -v
```

**Services:**

| Service    | Port   | Image                     |
| ---------- | ------ | ------------------------- |
| `api`      | `8000` | Custom (Python 3.11-slim) |
| `postgres` | `5432` | postgres:16-alpine        |
| `redis`    | `6379` | redis:7-alpine            |

---

## Testing

```bash
cd backend

# Run all tests
pytest -q

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test module
pytest tests/unit/test_vision_service.py -v
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with** &hearts; **using FastAPI, Next.js, and OpenAI Vision**

</div>
