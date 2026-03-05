# ============================================================
# CLAUDE CODE INSTRUCTIONS
# ============================================================
# You are Claude Code running inside Google Antigravity IDE.
# This file is your complete build brief. Read it fully first,
# then execute every step in order from top to bottom.
#
# CONTEXT:
# - Machine: MacBook Air M4, 16GB RAM, 1TB SSD, macOS
# - Project folder: ~/local-ai
# - docker-compose.yml is already present in ~/local-ai
# - The user has Homebrew, Docker Desktop, Ollama, and Node.js
#   already installed (verify each before proceeding)
#
# YOUR MISSION:
# Build and fully configure the complete local AI stack exactly
# as described in this document. This includes:
# 1. Verifying all prerequisites are installed
# 2. Setting env variables in ~/.zshrc
# 3. Pulling all Ollama models
# 4. Launching the Docker stack via docker compose up -d
# 5. Fixing the SearXNG JSON config
# 6. Configuring Open WebUI (web search ON by default,
#    embedding model set to mxbai-embed-large)
# 7. Installing the Semantic Model Router function
# 8. Verifying all services are healthy
# 9. Running a test prompt to confirm everything works end to end
#
# RULES:
# - Verify each step succeeded before moving to the next
# - If a step fails, diagnose using logs and fix before continuing
# - Never skip a step — do them all in sequence
# - After completion, print a summary of what was done and
#   the URL for each running service
#
# START PROMPT (user will say this to begin):
# "Read setup-guide.md and build the complete local AI stack
#  on my Mac exactly as described. Begin from Step 1 and work
#  through to the end. Fix any errors you encounter."
# ============================================================

# Local AI Stack — Complete Setup Guide
**MacBook Air M4 · 16GB RAM · 1TB SSD · Free · 100% Private**
Last updated: March 2026

---

## What's Included

| Service | Purpose | URL |
|---|---|---|
| Ollama | Runs all LLMs locally | localhost:11434 |
| Open WebUI | ChatGPT-style chat interface | localhost:3000 |
| SearXNG | Private web search (default ON) | localhost:8080 |
| Flowise | Visual AI workflow builder (LangChain) | localhost:3001 |
| n8n | Task automation (400+ integrations) | localhost:5678 |

**Total cost: $0/month forever.**

---

## Final Model Stack (March 2026)

| Role | Model | Command | Size |
|---|---|---|---|
| All-rounder + Coding + Vision | Qwen3.5 9B | `ollama pull qwen3.5:9b` | 6.6GB |
| Reasoning / Math | DeepSeek R1 Distill 8B | `ollama pull deepseek-r1:8b` | ~5GB |
| Vision + Variety | Llama 3.2 Vision 11B | `ollama pull llama3.2-vision:11b` | ~8GB |
| RAG Embeddings (background) | mxbai-embed-large | `ollama pull mxbai-embed-large` | ~0.7GB |

**Total model storage: ~20.3GB**

### Why these models?
- **Qwen3.5 9B** — best all-round model for your hardware. Natively supports vision, tool use, and thinking mode. Outperforms DeepSeek Coder on coding benchmarks. Replaces both the general model and the separate vision model. 6.6GB at Q4_K_M quantization.
- **DeepSeek R1 8B** — dedicated reasoning model. Best for maths, logic, and step-by-step problem solving.
- **mxbai-embed-large** — better than nomic-embed-text for RAG. Outperforms OpenAI's proprietary embedding models on retrieval benchmarks.

### One-liner to pull all models
```bash
ollama pull qwen3.5:9b && ollama pull deepseek-r1:8b && ollama pull llama3.2-vision:11b && ollama pull mxbai-embed-large
```

---

## How RAM Works

**Only one model loads at a time.** Ollama unloads a model 30 minutes after last use and loads the next one on demand. You never have all models in RAM simultaneously.

| Situation | RAM Used |
|---|---|
| No active chat | ~0GB (models idle on SSD) |
| Chatting with Qwen3.5 9B | ~6.6GB |
| Chatting with DeepSeek R1 8B | ~5GB |
| mxbai-embed-large (RAG indexing) | ~0.7GB briefly |

Add to ~/.zshrc for persistent settings:
```bash
export OLLAMA_KEEP_ALIVE=30m
export OLLAMA_METAL_ENABLED=1
export OLLAMA_NUM_GPU=1
```

---

## Auto Model Selection (+ Manual Override)

Open WebUI supports a **Semantic Model Router** — a Python function pipe that automatically picks the best model based on your query, while still letting you manually select any model at any time.

### Routing logic

| Query type detected | Auto-selected model |
|---|---|
| Coding, debugging, scripts | Qwen3.5 9B |
| Maths, logic, step-by-step reasoning | DeepSeek R1 8B |
| Image uploaded | Qwen3.5 9B (vision) |
| General chat, writing, summarization | Qwen3.5 9B |

### How to install
1. Open WebUI → Workspace → Functions → click **+**
2. Search: **"Semantic Model Router"** (by atgehrhardt)
3. Or direct link: https://openwebui.com/f/atgehrhardt/semantic_model_router
4. Set valves:
   - OPENAI_BASE_URL: `http://host.docker.internal:11434/v1`
   - Map each intention to your model names
5. Save — a new **"Auto"** option appears in your model dropdown

Manual model selection still works exactly as before — Auto mode is purely additive.

---

## Installation Steps

### Prerequisites
- macOS Apple Silicon (M4)
- Homebrew
- Docker Desktop (docker.com/products/docker-desktop — free personal use)

### Step 1 — Install Ollama
```bash
brew install ollama
```

Add to ~/.zshrc:
```bash
echo 'export OLLAMA_METAL_ENABLED=1' >> ~/.zshrc
echo 'export OLLAMA_NUM_GPU=1' >> ~/.zshrc
echo 'export OLLAMA_KEEP_ALIVE=30m' >> ~/.zshrc
source ~/.zshrc
```

Start Ollama:
```bash
ollama serve &
```

### Step 2 — Pull models
```bash
ollama pull qwen3.5:9b
ollama pull deepseek-r1:8b
ollama pull mxbai-embed-large
```

### Step 3 — Launch full stack
```bash
mkdir ~/local-ai
# place docker-compose.yml in this folder, then:
cd ~/local-ai
docker compose up -d
```

Wait ~60 seconds. Open http://localhost:3000

### Step 4 — Fix SearXNG JSON (one time only)
```bash
docker exec searxng sed -i 's/formats:/formats:\n    - json/' /etc/searxng/settings.yml
docker restart searxng
```

### Step 5 — Configure Open WebUI

**Web Search (Admin Panel → Settings → Web Search):**
- Enable web search: ON
- Enable by default: ON
- Provider: SearXNG
- URL: `http://searxng:8080/search?q=<query>&format=json`

**RAG Embeddings (Admin Panel → Settings → Documents):**
- Embedding model: `mxbai-embed-large`
- Embedding URL: `http://host.docker.internal:11434`

---

## Chrome Extensions

### Page Assist (start here)
- Chrome Web Store → search "Page Assist" → install
- Settings → Ollama URL: `http://localhost:11434`
- Default model: `qwen3.5:9b`
- Gives a sidebar AI on any webpage — highlight text, right-click, ask AI

### Browser-Use (for automation)
- AI agent that controls your browser — clicks, types, navigates
- GitHub: github.com/browser-use/browser-use
- Pairs with n8n for full end-to-end automation workflows

---

## Using Each Tool

### Open WebUI (localhost:3000)
- Model dropdown: Qwen3.5, DeepSeek R1, or Auto
- Drag and drop PDF/image into chat
- Type `#` to reference a saved document
- Type `#` + URL to pull any webpage into context
- Web search runs automatically before each response

### Flowise (localhost:3001) — login: admin / localai123
- Visual drag-and-drop canvas, no code needed
- ChatOllama node → set URL to `http://host.docker.internal:11434`
- Build RAG pipelines, agents with memory, custom chatbots
- LangChain-powered under the hood

### n8n (localhost:5678)
- Build automations connecting local AI to external services
- Use the Ollama node → endpoint: `http://host.docker.internal:11434`
- Example workflows:
  - Auto-summarize PDFs dropped in a folder
  - Daily AI briefing sent to your email
  - Connect to Gmail, Notion, Google Sheets, Slack
  - Trigger AI tasks on a schedule or based on events

### SearXNG (localhost:8080)
- Private search engine — aggregates Google, Bing, DuckDuckGo simultaneously
- Zero tracking, all queries stay on your Mac
- Can be used directly as a standalone browser search engine

---

## What to Prepare Before Claude Code Starts

When using **Claude Pro + Claude Code in Google Antigravity IDE**, it can build and configure everything hands-free — but the following must be in place first so it has something to work with.

### Must be done before the Claude Code session

**1. Install Homebrew**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Verify: `brew --version`

**2. Install Docker Desktop**
Download from docker.com/products/docker-desktop → open it → let it fully start.
Verify: `docker --version`

**3. Install Ollama**
```bash
brew install ollama
```
Verify: `ollama --version`

**4. Install Node.js v18+** (required for Flowise and Claude Code CLI)
```bash
brew install node
```
Verify: `node --version`

**5. Create the project folder**
```bash
mkdir ~/local-ai && cd ~/local-ai
```

**6. Place docker-compose.yml in ~/local-ai/**
Save the provided docker-compose.yml file into this folder before starting the session.

**7. Make sure Docker Desktop is running**
Claude Code needs to execute `docker compose up -d` — Docker must be active in your menu bar.

### Optional but helpful

**8. Pull at least one model** so Claude Code can run tests:
```bash
ollama serve &
ollama pull qwen3.5:9b
```

**9. Have a browser tab open** at localhost:3000 after first launch so you can verify each step visually.

**10. Confirm Git is installed:**
```bash
git --version
# if missing:
brew install git
```

### What Claude Code handles after that
Once the above is ready, a single Claude Code session can:
- Write and configure all YAML and config files
- Run `docker compose up -d` to launch the full stack
- Apply the SearXNG JSON fix
- Configure Open WebUI via its API (web search default ON, embedding model, etc.)
- Install the Semantic Model Router function
- Test web search, RAG, file uploads, and model switching end to end
- Read live Docker logs and fix any errors automatically

---

## Useful Commands

```bash
# Start everything
docker compose up -d

# Stop everything
docker compose down

# Check running services
docker compose ps

# View logs
docker logs open-webui
docker logs n8n
docker logs flowise
docker logs searxng

# Update all images to latest
docker compose pull && docker compose up -d

# List downloaded Ollama models
ollama list

# See what's currently loaded in RAM
ollama ps

# Remove a model
ollama rm modelname
```

---

## Storage Summary

| Item | Size |
|---|---|
| Qwen3.5 9B | 6.6GB |
| DeepSeek R1 8B | ~5.0GB |
| mxbai-embed-large | ~0.7GB |
| Docker images (all 5 services) | ~4.0GB |
| **Llama 3.2 Vision 11B** | ~8.0GB |
| **Total used** | **~20.3GB of 1TB** |

---

## Project Files

| File | Description |
|---|---|
| `docker-compose.yml` | Launches all 5 services in one command |
| `setup-guide.md` | This file |

---

*All tools are free and open-source. All data stays on your Mac.*
*Recommended combo: Claude Pro + Claude Code in Google Antigravity IDE for automated setup.*

---

## Claude Code — Verification Checklist

After completing all steps, verify these are true before telling the user you're done:

```bash
# All 5 containers running
docker compose ps
# Expected: ollama, open-webui, searxng, flowise, n8n all "Up"

# Ollama responding
curl http://localhost:11434/api/tags
# Expected: JSON list of pulled models

# Open WebUI accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200

# SearXNG JSON search working
curl "http://localhost:8080/search?q=test&format=json" | head -c 100
# Expected: JSON response starting with {

# Flowise accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001
# Expected: 200

# n8n accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:5678
# Expected: 200
```

If any check fails, read the relevant container logs and fix before reporting done:
```bash
docker logs [container-name] --tail 50
```

## Claude Code — Final Output to User

When all checks pass, print this summary:

```
✅ Local AI Stack is live on your Mac

Open WebUI (main interface)  → http://localhost:3000
SearXNG (private search)     → http://localhost:8080
Flowise (visual AI builder)  → http://localhost:3001  login: admin / localai123
n8n (automations)            → http://localhost:5678

Models ready in Ollama:
  qwen3.5:9b          (main model — coding, chat, vision)
  deepseek-r1:8b      (reasoning, math)
  llama3.2-vision:11b (vision, variety)
  mxbai-embed-large   (RAG embeddings)

Web search: ON by default
Auto model router: installed
Chrome extension: install Page Assist from Chrome Web Store
                  → Ollama URL: http://localhost:11434

Everything is running. Open http://localhost:3000 to start chatting.
```
