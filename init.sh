#!/bin/bash
# ============================================================
# SynapseAI — One-shot init script
# Run once after `docker compose up -d` to configure everything
# Usage: bash init.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
fail(){ echo -e "${RED}[✗]${NC} $1"; }

echo "=================================================="
echo "  SynapseAI Stack — Init & Configuration"
echo "=================================================="
echo ""

# ── STEP 1: Verify Ollama is running ─────────────────────
echo "→ Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  fail "Ollama is not running. Start it with: open -a Ollama"
  exit 1
fi
ok "Ollama is running"

# ── STEP 2: Pull required models ─────────────────────────
echo ""
echo "→ Pulling Ollama models (skip if already present)..."

pull_if_missing() {
  local model=$1
  if ollama list | grep -q "^${model}"; then
    ok "  ${model} already present"
  else
    echo "  Pulling ${model}..."
    ollama pull "$model"
    ok "  ${model} pulled"
  fi
}

pull_if_missing "mxbai-embed-large"
pull_if_missing "deepseek-r1:8b"
pull_if_missing "llama3.2-vision:11b"

# Cap qwen3.5:9b context to 8192 (safe for 16GB Mac)
if ollama list | grep -q "^qwen3.5:9b"; then
  echo "  Applying 8192 context cap to qwen3.5:9b..."
  tmpfile=$(mktemp)
  echo "FROM qwen3.5:9b" > "$tmpfile"
  echo "PARAMETER num_ctx 8192" >> "$tmpfile"
  ollama create qwen3.5:9b -f "$tmpfile" > /dev/null 2>&1
  rm "$tmpfile"
  ok "  qwen3.5:9b context capped to 8192"
else
  echo "  Pulling qwen3.5:9b..."
  ollama pull qwen3.5:9b
  tmpfile=$(mktemp)
  echo "FROM qwen3.5:9b" > "$tmpfile"
  echo "PARAMETER num_ctx 8192" >> "$tmpfile"
  ollama create qwen3.5:9b -f "$tmpfile" > /dev/null 2>&1
  rm "$tmpfile"
  ok "  qwen3.5:9b pulled + context capped to 8192"
fi

# ── STEP 3: Wait for Docker containers ───────────────────
echo ""
echo "→ Waiting for containers to be healthy..."
max_wait=90
elapsed=0
while true; do
  owui_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
  if [ "$owui_code" = "200" ]; then
    break
  fi
  if [ "$elapsed" -ge "$max_wait" ]; then
    fail "Open WebUI didn't start in ${max_wait}s. Check: docker compose logs open-webui"
    exit 1
  fi
  sleep 3
  elapsed=$((elapsed + 3))
done
ok "All containers are up"

# ── STEP 4: Configure Open WebUI ─────────────────────────
echo ""
echo "→ Configuring Open WebUI..."

TOKEN=$(curl -s 'http://localhost:3000/api/v1/auths/signin' \
  -X POST -H 'Content-Type: application/json' \
  -d '{"email":"admin@localhost","password":"admin"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  warn "Could not get Open WebUI token — skipping API config"
else
  # Enable web search with SearXNG
  python3 << PYEOF
import json, urllib.request, urllib.error

BASE = 'http://localhost:3000'
TOKEN = '${TOKEN}'

def api(method, path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    h = {'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN}'}
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_error': e.code}

# Enable web search
config = api('GET', '/api/v1/retrieval/config')
config['web'] = config.get('web', {})
config['web']['ENABLE_WEB_SEARCH'] = True
config['web']['WEB_SEARCH_ENGINE'] = 'searxng'
config['web']['SEARXNG_QUERY_URL'] = 'http://searxng:8080/search?q=<query>&format=json'
config['web']['WEB_SEARCH_RESULT_COUNT'] = 5
config['web']['WEB_SEARCH_CONCURRENT_REQUESTS'] = 10
result = api('POST', '/api/v1/retrieval/config/update', config)
print('  Web search enabled:', result.get('web', {}).get('ENABLE_WEB_SEARCH'))

# Set web search on by default in chat
api('POST', '/api/v1/users/user/settings/update', {
    "ui": {"version": "0.8.8", "memory": True, "params": {"web_search": True}}
})
print('  Web search default-on in new chats: True')
PYEOF
  ok "Open WebUI configured (web search on, SearXNG connected)"
fi

# ── STEP 5: n8n owner setup ───────────────────────────────
echo ""
echo "→ Setting up n8n owner account..."
N8N_RESULT=$(python3 << 'PYEOF'
import json, urllib.request, urllib.error

# Check if already set up
req = urllib.request.Request('http://localhost:5678/rest/settings')
try:
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        if not data.get('data', {}).get('userManagement', {}).get('showSetupOnFirstLoad', True):
            print("already_done")
        else:
            print("needs_setup")
except Exception:
    print("error")
PYEOF
)

if [ "$N8N_RESULT" = "already_done" ]; then
  ok "n8n already configured"
else
  python3 << 'PYEOF'
import json, urllib.request, urllib.error

payload = {
    "email": "admin@local.ai",
    "firstName": "Admin",
    "lastName": "User",
    "password": "Admin12345"
}
req = urllib.request.Request('http://localhost:5678/rest/owner/setup',
    data=json.dumps(payload).encode(), method='POST',
    headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        print(f"  n8n owner: {result.get('data', {}).get('email', 'created')}")
except urllib.error.HTTPError as e:
    print(f"  n8n setup: {e.read()[:100]}")
PYEOF
  ok "n8n owner account created"
fi

# ── STEP 6: Fix SearXNG JSON format ──────────────────────
echo ""
echo "→ Checking SearXNG JSON format..."
SEARXNG_CHECK=$(curl -s "http://localhost:8080/search?q=test&format=json" 2>/dev/null | head -c 1)
if [ "$SEARXNG_CHECK" = "{" ]; then
  ok "SearXNG JSON already enabled"
else
  docker exec searxng sed -i '/^  formats:/a\    - json' /etc/searxng/settings.yml 2>/dev/null && \
  docker restart searxng > /dev/null 2>&1 && \
  sleep 5
  ok "SearXNG JSON format enabled"
fi

# ── STEP 7: Install Semantic Model Router ────────────────
echo ""
echo "→ Installing Semantic Model Router in Open WebUI..."
if [ -n "$TOKEN" ]; then
  python3 << PYEOF
import json, urllib.request, urllib.error

BASE = 'http://localhost:3000'
TOKEN = '${TOKEN}'

def api(method, path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    h = {'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN}'}
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_error': e.code, '_msg': e.read().decode()[:100]}

# Check if already installed
funcs = api('GET', '/api/v1/functions/')
if isinstance(funcs, list) and any(f.get('id') == 'semantic_model_router' for f in funcs):
    print('  Already installed')
else:
    router_code = '''
\"\"\"
title: Semantic Model Router
author: atgehrhardt
version: 0.1.3
license: MIT
description: Routes queries to the best model automatically.
\"\"\"
from pydantic import BaseModel, Field
from typing import Optional

class Pipe:
    class Valves(BaseModel):
        OPENAI_BASE_URL: str = Field(default="http://host.docker.internal:11434/v1")
        CODING_MODEL: str = Field(default="qwen3.5:9b")
        REASONING_MODEL: str = Field(default="deepseek-r1:8b")
        GENERAL_MODEL: str = Field(default="qwen3.5:9b")
        VISION_MODEL: str = Field(default="qwen3.5:9b")

    def __init__(self):
        self.valves = self.Valves()
        self.type = "manifold"

    def pipes(self):
        return [{"id": "auto", "name": "Auto (Semantic Router)"}]

    def _classify(self, query):
        q = query.lower()
        coding = ["code","function","debug","python","javascript","script","bug","implement","sql","bash","api","docker","regex"]
        reasoning = ["math","calculate","solve","logic","reasoning","equation","formula","step by step","probability","statistics","proof"]
        cs = sum(1 for k in coding if k in q)
        rs = sum(1 for k in reasoning if k in q)
        if cs > rs and cs > 0: return self.valves.CODING_MODEL
        if rs > 0: return self.valves.REASONING_MODEL
        return self.valves.GENERAL_MODEL

    async def pipe(self, body: dict, __user__: Optional[dict] = None):
        import httpx
        messages = body.get("messages", [])
        has_image = any(isinstance(m.get("content"), list) and any(
            isinstance(c, dict) and c.get("type") == "image_url" for c in m.get("content", [])) for m in messages)
        if has_image:
            model = self.valves.VISION_MODEL
        else:
            last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
            content = last.get("content", "")
            text = content if isinstance(content, str) else " ".join(c.get("text","") for c in content if isinstance(c, dict))
            model = self._classify(text)
        payload = {**body, "model": model}
        payload.pop("pipe_id", None)
        async with httpx.AsyncClient() as client:
            if body.get("stream", False):
                async with client.stream("POST", f"{self.valves.OPENAI_BASE_URL}/chat/completions",
                    json=payload, headers={"Content-Type":"application/json","Authorization":"Bearer ollama"}, timeout=300) as r:
                    async for chunk in r.aiter_text(): yield chunk
            else:
                r = await client.post(f"{self.valves.OPENAI_BASE_URL}/chat/completions",
                    json=payload, headers={"Content-Type":"application/json","Authorization":"Bearer ollama"}, timeout=300)
                yield r.text
'''
    result = api('POST', '/api/v1/functions/create', {
        "id": "semantic_model_router", "name": "Semantic Model Router",
        "content": router_code, "is_active": True, "is_global": True,
        "meta": {"description": "Routes to qwen3.5:9b (coding/general) or deepseek-r1:8b (reasoning)", "manifest": {}}
    })
    if '_error' not in result:
        api('POST', '/api/v1/functions/id/semantic_model_router/toggle', {})
        api('POST', '/api/v1/functions/id/semantic_model_router/toggle/global', {})
        print(f'  Installed: {result.get("name")}')
    else:
        print(f'  Error: {result}')
PYEOF
  ok "Semantic Model Router installed"
fi

# ── DONE ─────────────────────────────────────────────────
echo ""
echo "=================================================="
echo -e "${GREEN}  All done! Stack is ready.${NC}"
echo "=================================================="
echo ""
echo "  Open WebUI        → http://localhost:3000"
echo "  SearXNG           → http://localhost:8080"
echo "  Flowise           → http://localhost:3001"
echo "  n8n               → http://localhost:5678"
echo ""
echo "  n8n login:    admin@local.ai / Admin12345"
echo "  Flowise:      see FLOWISE_SETUP.md for one-time setup"
echo ""
echo "  Models in Ollama:"
ollama list | awk 'NR==1 || /qwen3|deepseek|mxbai|llama3.2-vision/ {printf "    %s\n", $0}'
echo ""
