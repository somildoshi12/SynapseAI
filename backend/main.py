"""
SynapseAI Backend — FastAPI
Streaming chat, semantic model routing, SearXNG web search.

Run: uvicorn main:app --reload --port 8000
"""

import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

app = FastAPI(title="SynapseAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434"
SEARXNG_URL = "http://localhost:8080"

# ── Semantic Model Router ─────────────────────────────────────────────────────

CODING_KW = {
    "code", "function", "debug", "error", "python", "javascript", "typescript",
    "script", "programming", "bug", "implement", "class", "method", "algorithm",
    "sql", "bash", "shell", "api", "git", "docker", "regex", "html", "css",
    "react", "flask", "fastapi", "node", "npm", "pip", "refactor", "syntax",
}

REASONING_KW = {
    "math", "calculate", "solve", "prove", "logic", "reasoning", "equation",
    "formula", "step by step", "step-by-step", "derive", "probability",
    "statistics", "theorem", "proof", "integral", "derivative", "matrix",
    "linear algebra", "optimize", "why does",
}

MODEL_NAMES = {
    "auto": "auto",
    "qwen3.5:9b": "Qwen3.5 9B",
    "deepseek-r1:8b": "DeepSeek R1 8B",
    "llama3.2-vision:11b": "Llama 3.2 Vision 11B",
}


def route_model(messages: list, preferred: str = "auto") -> str:
    if preferred and preferred != "auto":
        return preferred
    last = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    q = last.lower()
    coding_score = sum(1 for kw in CODING_KW if kw in q)
    reasoning_score = sum(1 for kw in REASONING_KW if kw in q)
    if coding_score > reasoning_score and coding_score > 0:
        return "qwen3.5:9b"
    if reasoning_score > 0:
        return "deepseek-r1:8b"
    return "qwen3.5:9b"


# ── Web Search ────────────────────────────────────────────────────────────────

async def web_search(query: str, num_results: int = 4) -> str:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
            )
            data = r.json()
            results = data.get("results", [])[:num_results]
            if not results:
                return ""
            lines = []
            for i, res in enumerate(results, 1):
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                lines.append(f"[{i}] {title}\n{content}\nSource: {url}")
            return f"Web search results for \"{query}\":\n\n" + "\n\n".join(lines)
    except Exception:
        return ""


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/models")
async def list_models():
    """Return list of available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            data = r.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": ["auto"] + models}
    except Exception:
        return {"models": ["auto", "qwen3.5:9b", "deepseek-r1:8b"]}


class ChatRequest(BaseModel):
    messages: list
    model: str = "auto"
    web_search: bool = False


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream a chat response from Ollama with optional web search context."""
    model = route_model(req.messages, req.model)
    messages = list(req.messages)

    # Inject web search context if enabled
    search_used = False
    if req.web_search and messages:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        context = await web_search(last_user)
        if context:
            system_msg = {
                "role": "system",
                "content": (
                    f"{context}\n\n"
                    "Use the above web search results to help answer the user's question. "
                    "Cite sources with [1], [2], etc. when referencing them."
                ),
            }
            messages = [system_msg] + messages
            search_used = True

    async def generate():
        # Send metadata first (model chosen, search used)
        yield f"data: {json.dumps({'type': 'meta', 'model': model, 'search': search_used})}\n\n"

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "options": {"num_ctx": 8192},
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        if data.get("done"):
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
