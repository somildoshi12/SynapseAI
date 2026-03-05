# SynapseAI

A fully self-hosted, 100% private local AI stack that runs entirely on your Mac. No API keys, no subscriptions, no data leaving your machine — ever.

Built with a custom ChatGPT-like React frontend, a FastAPI streaming backend, local LLMs via Ollama, and a Docker-powered support stack (private search, visual AI builder, automation engine).

---

## What's Inside

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18 + Vite | ChatGPT-style chat UI |
| **Backend** | FastAPI + uvicorn | Streaming API, model routing, file uploads |
| **LLM Runtime** | Ollama (Homebrew) | Runs all models locally on Apple Silicon |
| **Search** | SearXNG (Docker) | Private web search, zero tracking |
| **Visual AI Builder** | Flowise (Docker) | Drag-and-drop LangChain pipelines |
| **Automation** | n8n (Docker) | 400+ integrations, workflow automation |

---

## Features

- **Streaming chat** — token-by-token responses, just like ChatGPT
- **Semantic model router** — automatically picks the best model based on your query (coding → Qwen3.5, math/logic → DeepSeek R1, images → Llama Vision); manual override always available
- **Web search** — toggle-able SearXNG integration; results are injected into context before each response, with source citations
- **File uploads** — drag and drop images (JPEG, PNG, GIF, WebP), PDFs, or text/code files directly into chat
- **Multi-conversation sidebar** — persistent chat history stored in localStorage
- **Stop generation** — cancel any response mid-stream
- **100% free** — $0/month, forever

---

## Model Stack

| Role | Model | Pull Command | Size |
|---|---|---|---|
| Coding + General + Vision | Qwen3.5 9B | `ollama pull qwen3.5:9b` | ~6.6 GB |
| Reasoning + Math | DeepSeek R1 8B | `ollama pull deepseek-r1:8b` | ~5.0 GB |
| Vision (alternative) | Llama 3.2 Vision 11B | `ollama pull llama3.2-vision:11b` | ~8.0 GB |
| RAG Embeddings | mxbai-embed-large | `ollama pull mxbai-embed-large` | ~0.7 GB |

> **RAM note:** Ollama loads only one model at a time and unloads it after 30 minutes of inactivity. On a 16 GB Mac, you never exceed ~9 GB for the largest model.

---

## Project Structure

```
SynapseAI/
├── backend/
│   ├── main.py               # FastAPI app — chat, routing, search, uploads
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Root component, SSE streaming, state management
│   │   ├── components/
│   │   │   ├── Sidebar.jsx   # Conversation list
│   │   │   ├── ChatWindow.jsx# Message list with markdown rendering
│   │   │   ├── Message.jsx   # Individual message bubble
│   │   │   └── InputBar.jsx  # Input, file upload, model selector, web search toggle
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js        # Proxies /api/* → localhost:8000
│   └── package.json
├── docker-compose.yml        # SearXNG + Flowise + n8n
├── init.sh                   # One-shot config script (run after docker compose up)
├── setup-guide.md            # Full setup reference
└── README.md
```

---

## Prerequisites

Make sure the following are installed before you begin.

| Requirement | Install | Verify |
|---|---|---|
| macOS Apple Silicon | — | — |
| Homebrew | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | `brew --version` |
| Docker Desktop | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | `docker --version` |
| Ollama | `brew install ollama` | `ollama --version` |
| Python 3.10+ | `brew install python` | `python3 --version` |
| Node.js 18+ | `brew install node` | `node --version` |

---

## Setup & Installation

### 1 — Clone the repo

```bash
git clone https://github.com/your-username/SynapseAI.git
cd SynapseAI
```

### 2 — Configure Ollama environment

Add these to your `~/.zshrc` for GPU acceleration and memory management:

```bash
echo 'export OLLAMA_METAL_ENABLED=1' >> ~/.zshrc
echo 'export OLLAMA_NUM_GPU=1'       >> ~/.zshrc
echo 'export OLLAMA_KEEP_ALIVE=30m'  >> ~/.zshrc
source ~/.zshrc
```

Start Ollama:

```bash
ollama serve &
```

### 3 — Pull AI models

```bash
ollama pull qwen3.5:9b
ollama pull deepseek-r1:8b
ollama pull mxbai-embed-large
```

Optional (large — only if you need a separate vision model):

```bash
ollama pull llama3.2-vision:11b
```

Or pull everything at once:

```bash
ollama pull qwen3.5:9b && ollama pull deepseek-r1:8b && ollama pull mxbai-embed-large
```

### 4 — Launch the Docker stack

Make sure Docker Desktop is running, then:

```bash
docker compose up -d
```

This starts SearXNG (`:8080`), Flowise (`:3001`), and n8n (`:5678`).

### 5 — Run the one-shot init script

```bash
bash init.sh
```

This script:
- Verifies Ollama is running
- Pulls any missing models
- Waits for containers to be healthy
- Enables SearXNG JSON format
- Creates the n8n owner account

### 6 — Install Python dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7 — Install frontend dependencies

```bash
cd frontend
npm install
```

---

## Running SynapseAI

You need three things running simultaneously: Ollama, the FastAPI backend, and the Vite frontend.

### Option A — Quickstart (three separate terminals)

**Terminal 1 — Ollama** (skip if already running):
```bash
ollama serve
```

**Terminal 2 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

### Option B — start.sh (single command)

If the repo includes `start.sh`:

```bash
bash start.sh
```

---

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| SynapseAI Chat | http://localhost:5173 | — |
| FastAPI Backend | http://localhost:8000 | — |
| Ollama API | http://localhost:11434 | — |
| SearXNG | http://localhost:8080 | — |
| Flowise | http://localhost:3001 | `admin` / `localai123` |
| n8n | http://localhost:5678 | `admin@local.ai` / `Admin12345` |

---

## How the Backend Works

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Streaming chat (SSE) |
| `GET` | `/api/models` | List available Ollama models |
| `POST` | `/api/upload` | Upload image, PDF, or text file |
| `GET` | `/api/health` | Health check |

### Semantic Model Router

The backend automatically selects the best model based on keyword analysis of the user's message:

| Query type | Selected model |
|---|---|
| Coding, debugging, scripts | `qwen3.5:9b` |
| Math, logic, step-by-step reasoning | `deepseek-r1:8b` |
| Image attached | `llama3.2-vision:11b` |
| General chat, writing, summarization | `llama3.2:latest` |

Set `model` to any specific model name in the request to override routing.

### Web Search

When `web_search: true` is included in the chat request, the backend:
1. Sends the user's last message to SearXNG
2. Takes the top 4 results
3. Injects them as a system message before calling Ollama
4. The model cites sources as `[1]`, `[2]`, etc.

---

## Docker Stack Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Check container status
docker compose ps

# View logs for a specific service
docker logs searxng
docker logs flowise
docker logs n8n

# Update all images to latest
docker compose pull && docker compose up -d
```

---

## Ollama Commands

```bash
# List downloaded models
ollama list

# Check which model is currently loaded in RAM
ollama ps

# Remove a model
ollama rm modelname

# Pull a new model
ollama pull modelname
```

---

## Troubleshooting

**Backend can't reach Ollama**
```bash
# Make sure Ollama is running
ollama serve &
curl http://localhost:11434/api/tags
```

**SearXNG returns HTML instead of JSON**
```bash
docker exec searxng sed -i '/^  formats:/a\    - json' /etc/searxng/settings.yml
docker restart searxng
# Verify:
curl "http://localhost:8080/search?q=test&format=json" | head -c 50
```

**Frontend can't reach backend**

Check that [vite.config.js](frontend/vite.config.js) has the proxy pointing to `http://localhost:8000` and that the backend is running on that port.

**Docker containers not starting**

Make sure Docker Desktop is open and fully started before running `docker compose up -d`.

**Port already in use**

Check what's on the conflicting port and stop it, or change the port mapping in [docker-compose.yml](docker-compose.yml).

```bash
lsof -i :8080   # example for SearXNG port
```

---

## Storage Summary

| Item | Size |
|---|---|
| Qwen3.5 9B | ~6.6 GB |
| DeepSeek R1 8B | ~5.0 GB |
| mxbai-embed-large | ~0.7 GB |
| Llama 3.2 Vision 11B (optional) | ~8.0 GB |
| Docker images (3 services) | ~2.0 GB |
| **Total (without Vision)** | **~14.3 GB** |
| **Total (with Vision)** | **~22.3 GB** |

---

## Tech Stack

**Frontend:** React 18, Vite 5, react-markdown, remark-gfm

**Backend:** FastAPI, uvicorn, httpx, pydantic, python-multipart

**LLM:** Ollama (native, Apple Silicon GPU acceleration via Metal)

**Infrastructure:** Docker Desktop, SearXNG, Flowise, n8n

---

*All tools are free and open-source. All data stays on your Mac. No telemetry, no cloud, no cost.*
