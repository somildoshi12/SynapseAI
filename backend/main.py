"""
SynapseAI Backend — FastAPI
Streaming chat, semantic model routing, SearXNG web search, file uploads,
and full disk persistence (conversations + uploaded files).

Run: uvicorn main:app --reload --port 8000
"""

import json
import base64
import io
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx

app = FastAPI(title="SynapseAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL  = "http://localhost:11434"
SEARXNG_URL = "http://localhost:8080"

# ── Disk Storage ───────────────────────────────────────────────────────────────
DATA_DIR  = Path(__file__).parent / "data"
CONVS_DIR = DATA_DIR / "conversations"
FILES_DIR = DATA_DIR / "files"
CONVS_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_EXTS   = {".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json",
               ".csv", ".html", ".css", ".yaml", ".yml", ".sh", ".sql", ".xml"}

# ── Semantic Model Router ──────────────────────────────────────────────────────

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


def route_model(messages: list, preferred: str = "auto") -> str:
    if preferred and preferred != "auto":
        return preferred
    # Image in any message → vision model (check full history)
    for msg in messages:
        if msg.get("images"):
            return "llama3.2-vision:11b"
        meta = msg.get("attachment_meta") or {}
        if meta.get("type") == "image":
            return "llama3.2-vision:11b"
    # Text file in any message → qwen3.5 for stronger document comprehension
    for msg in messages:
        if msg.get("file_context") or (msg.get("attachment_meta") or {}).get("type") == "text":
            return "qwen3.5:9b"
    # Score ALL user messages — if any part of the conversation is coding, stay on qwen3.5
    all_user_text = " ".join(
        m["content"].lower() for m in messages if m.get("role") == "user"
    )
    cs = sum(1 for kw in CODING_KW    if kw in all_user_text)
    rs = sum(1 for kw in REASONING_KW if kw in all_user_text)
    if cs > 0:
        return "qwen3.5:9b"       # coding / technical — never use llama for this
    if rs > 0:
        return "deepseek-r1:8b"   # math / logic / reasoning
    return "llama3.2:latest"      # general chat — fast & light


# ── Web Search ─────────────────────────────────────────────────────────────────

async def web_search(query: str, num_results: int = 4) -> str:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{SEARXNG_URL}/search",
                                 params={"q": query, "format": "json"})
            results = r.json().get("results", [])[:num_results]
            if not results:
                return ""
            lines = [
                f"[{i}] {res.get('title','')}\n{res.get('content','')}\nSource: {res.get('url','')}"
                for i, res in enumerate(results, 1)
            ]
            return f"Web search results for \"{query}\":\n\n" + "\n\n".join(lines)
    except Exception:
        return ""


# ── Conversation Persistence ───────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations():
    """Return all saved conversations, newest first."""
    convs = []
    for f in sorted(CONVS_DIR.glob("*.json"), key=lambda x: -x.stat().st_mtime):
        try:
            convs.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"conversations": convs}


@app.put("/api/conversations/{conv_id}")
async def save_conversation(conv_id: str, request: Request):
    """Save (create or overwrite) a single conversation to disk."""
    data = await request.json()
    path = CONVS_DIR / f"{conv_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {"ok": True}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation JSON and all its uploaded files."""
    conv_file = CONVS_DIR / f"{conv_id}.json"
    if conv_file.exists():
        conv_file.unlink()
    files_dir = FILES_DIR / conv_id
    if files_dir.exists():
        shutil.rmtree(files_dir)
    return {"ok": True}


# ── File Upload ────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    conv_id: str = Query(default="default"),
):
    """Upload a file; save to disk; return metadata for display + Ollama."""
    content = await file.read()
    mime = file.content_type or ""
    name = file.filename or "file"

    # Save raw file to disk (for serving previews and Ollama image calls)
    conv_files_dir = FILES_DIR / conv_id
    conv_files_dir.mkdir(parents=True, exist_ok=True)
    # Avoid collisions by prepending timestamp
    import time
    safe_name = f"{int(time.time()*1000)}_{name}"
    (conv_files_dir / safe_name).write_bytes(content)
    file_url = f"/api/files/{conv_id}/{safe_name}"

    # Images — also return base64 for backwards compat (small images only)
    if mime in IMAGE_TYPES:
        b64 = base64.b64encode(content).decode()
        return {
            "type": "image", "name": name, "mime": mime,
            "base64": b64, "file_url": file_url,
        }

    # PDFs → extract text
    if mime == "application/pdf" or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(
                page.extract_text() for page in reader.pages if page.extract_text()
            )
            return {"type": "text", "name": name, "content": text[:15000], "file_url": file_url}
        except ImportError:
            raise HTTPException(422, "PDF support requires: pip install pypdf")
        except Exception as e:
            raise HTTPException(422, f"Could not read PDF: {e}")

    # Text / code files
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if mime.startswith("text/") or ext in TEXT_EXTS:
        try:
            text = content.decode("utf-8")
            return {"type": "text", "name": name, "content": text[:15000], "file_url": file_url}
        except Exception:
            raise HTTPException(422, "Could not decode file as UTF-8 text")

    raise HTTPException(415, f"Unsupported file type: {mime or ext}")


# ── Serve Uploaded Files ───────────────────────────────────────────────────────

@app.get("/api/files/{conv_id}/{filename}")
async def serve_file(conv_id: str, filename: str):
    """Serve a previously uploaded file by conv_id and filename."""
    # Prevent path traversal
    base = FILES_DIR.resolve()
    target = (FILES_DIR / conv_id / filename).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(400, "Invalid path")
    if not target.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(target)


# ── Chat ───────────────────────────────────────────────────────────────────────

class AttachmentMeta(BaseModel):
    name: str
    type: str                        # "image" | "text"
    file_url: Optional[str] = None
    mime: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None        # base64 (legacy / small images)
    file_context: Optional[str] = None         # extracted text content
    attachment_meta: Optional[AttachmentMeta] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "auto"
    web_search: bool = False


@app.get("/api/models")
async def list_models():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            return {"models": ["auto"] + models}
    except Exception:
        return {"models": ["auto", "qwen3.5:9b", "deepseek-r1:8b"]}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream chat from Ollama with routing, web search, and file context."""
    raw_messages = [m.model_dump() for m in req.messages]
    model = route_model(raw_messages, req.model)

    # Detect if any message in the conversation carries a file
    has_text_file = any(
        m.get("file_context") or (m.get("attachment_meta") or {}).get("type") == "text"
        for m in raw_messages
    )
    has_image = any(
        m.get("images") or (m.get("attachment_meta") or {}).get("type") == "image"
        for m in raw_messages
    )
    has_file = has_text_file or has_image

    # Build Ollama-compatible message list
    ollama_messages = []
    for msg in raw_messages:
        user_question = msg["content"].strip()

        # Inject text file with clear framing so the model MUST use it
        if msg.get("file_context"):
            meta     = msg.get("attachment_meta") or {}
            filename = meta.get("name", "attached file")
            question = user_question or "Please read this file carefully and describe what it contains."
            om = {
                "role": msg["role"],
                "content": (
                    f'[Attached file: "{filename}"]\n\n'
                    f'{msg["file_context"]}\n\n'
                    f'---\n\n'
                    f'{question}'
                ),
            }
        else:
            # For messages without file context, use trimmed content
            # (if only a file was sent with no text, content is ' ' — give default prompt)
            om = {
                "role": msg["role"],
                "content": user_question or "Please analyze the attached file.",
            }

        # Resolve images: read from disk (authoritative), fall back to inline base64
        meta = msg.get("attachment_meta") or {}
        if meta.get("type") == "image" and meta.get("file_url"):
            file_url = meta["file_url"]
            rel      = file_url.removeprefix("/api/files/")
            img_path = (FILES_DIR / rel).resolve()
            base_dir = FILES_DIR.resolve()
            if str(img_path).startswith(str(base_dir)) and img_path.exists():
                om["images"] = [base64.b64encode(img_path.read_bytes()).decode()]
        elif msg.get("images"):
            om["images"] = msg["images"]

        ollama_messages.append(om)

    # Prepend a system message when a file is present, forcing the model to use it
    if has_file:
        if has_image:
            file_instruction = (
                "The user has shared an image. Carefully examine it and answer "
                "the user's question based on what you see in the image."
            )
        else:
            file_instruction = (
                "The user has attached a file to this conversation. "
                "You MUST read the file content provided and answer the user's "
                "question based on it. Quote or reference specific parts of the "
                "file when relevant. Do not rely on general knowledge if the "
                "answer is in the file."
            )
        ollama_messages.insert(0, {"role": "system", "content": file_instruction})

    # Inject web search context
    search_used = False
    if req.web_search and ollama_messages:
        last_user = next(
            (m["content"] for m in reversed(ollama_messages) if m["role"] == "user"), ""
        )
        context = await web_search(last_user)
        if context:
            ollama_messages = [{
                "role": "system",
                "content": (
                    f"{context}\n\n"
                    "Use these web search results to answer. Cite sources as [1], [2], etc."
                ),
            }] + ollama_messages
            search_used = True

    async def generate():
        yield f"data: {json.dumps({'type': 'meta', 'model': model, 'search': search_used})}\n\n"
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_URL}/api/chat",
                    json={"model": model, "messages": ollama_messages,
                          "stream": True, "options": {"num_ctx": 8192}},
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
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
