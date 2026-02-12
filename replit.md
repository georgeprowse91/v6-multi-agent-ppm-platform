# Multi-Agent PPM Platform

## Overview
AI-native Project Portfolio Management (PPM) platform with 25 specialized agents orchestrating portfolio, program, and project delivery. The platform includes a React frontend, FastAPI backend, and multiple microservices.

## Project Architecture

### Directory Structure
| Folder | Description |
| --- | --- |
| `agents/` | 25 domain agents plus runtime scaffolding, prompts, and tests |
| `apps/web/` | Web console - React frontend + FastAPI backend |
| `apps/web/frontend/` | React/Vite frontend (TypeScript) |
| `apps/web/src/` | FastAPI web backend (Python) |
| `apps/api-gateway/` | API Gateway service |
| `design-system/` | Design tokens and icon system |
| `packages/` | Shared Python and TypeScript packages |
| `services/` | Backend microservices |
| `integrations/` | Connector manifests and mappings |

### Tech Stack
- **Frontend**: React 18, Vite, TypeScript, Zustand, React Router
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Package Manager**: pnpm (workspace monorepo)
- **Database**: SQLite (local dev), PostgreSQL (production-ready)
- **AI/ML**: OpenAI, LangChain, FAISS

### Port Configuration
- **Frontend (Vite dev)**: 0.0.0.0:5000 (exposed to Replit proxy)
- **Backend (FastAPI)**: 127.0.0.1:8080 (internal, proxied via Vite)

### Key Files
- `start_web.py` - Backend startup script with Python path setup
- `apps/web/frontend/vite.config.ts` - Vite config with proxy to backend
- `apps/web/src/main.py` - FastAPI web console application

### Environment Variables
- `ENVIRONMENT=development` - Runtime environment
- `AUTH_DEV_MODE=true` - Enables dev auth bypass
- `AUTH_DEV_ROLES=PMO_ADMIN` - Dev user roles
- `LLM_PROVIDER=mock` - Uses mock LLM responses
- `DEMO_MODE=true` - Enables demo data

### Workflow
Single combined workflow runs:
1. Python FastAPI backend on port 8080 (background)
2. Vite dev server on port 5000 (foreground, proxies API to backend)

### Deployment
- Build: Vite frontend build
- Run: Python FastAPI serving both API and static frontend

## Recent Changes
- Configured for Replit environment (Feb 2026)
- Created `design-system/` stubs for tokens and icon map
- Set up Vite proxy configuration for backend API calls
- Configured development auth bypass mode
