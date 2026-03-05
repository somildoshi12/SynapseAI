"""
title: Semantic Model Router
author: atgehrhardt (adapted for SynapseAI)
version: 0.1.3
license: MIT
description: Routes queries to the best model automatically.
  - Coding / debugging  → qwen3.5:9b
  - Math / reasoning    → deepseek-r1:8b
  - Image uploaded      → qwen3.5:9b (vision)
  - General chat        → qwen3.5:9b

Install in Open WebUI:
  Workspace → Functions → + → paste this file → Save
  Then toggle it Active + Global.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Pipe:
    class Valves(BaseModel):
        OPENAI_BASE_URL: str = Field(
            default="http://host.docker.internal:11434/v1",
            description="Ollama OpenAI-compatible API base URL"
        )
        CODING_MODEL: str = Field(
            default="qwen3.5:9b",
            description="Model for coding and debugging tasks"
        )
        REASONING_MODEL: str = Field(
            default="deepseek-r1:8b",
            description="Model for math, logic, and step-by-step reasoning"
        )
        GENERAL_MODEL: str = Field(
            default="qwen3.5:9b",
            description="Model for general chat, writing, summarization"
        )
        VISION_MODEL: str = Field(
            default="qwen3.5:9b",
            description="Model for image analysis (vision)"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.type = "manifold"

    def pipes(self):
        return [{"id": "auto", "name": "Auto (Semantic Router)"}]

    def _classify(self, query: str) -> str:
        """Classify query to pick the best model."""
        q = query.lower()

        coding_keywords = [
            "code", "function", "debug", "error", "python", "javascript",
            "typescript", "script", "programming", "bug", "implement", "class",
            "method", "algorithm", "sql", "bash", "shell", "api", "git",
            "docker", "kubernetes", "regex", "syntax", "compile", "refactor",
            "html", "css", "react", "flask", "fastapi", "npm", "pip",
        ]

        reasoning_keywords = [
            "math", "calculate", "solve", "prove", "logic", "reasoning",
            "equation", "formula", "step by step", "step-by-step", "derive",
            "probability", "statistics", "theorem", "proof", "analysis",
            "evaluate", "compare", "reason", "think through", "integral",
            "derivative", "matrix", "linear algebra",
        ]

        coding_score = sum(1 for kw in coding_keywords if kw in q)
        reasoning_score = sum(1 for kw in reasoning_keywords if kw in q)

        if coding_score > reasoning_score and coding_score > 0:
            return self.valves.CODING_MODEL
        elif reasoning_score > 0:
            return self.valves.REASONING_MODEL
        else:
            return self.valves.GENERAL_MODEL

    async def pipe(self, body: dict, __user__: Optional[dict] = None):
        import httpx

        messages = body.get("messages", [])

        # Check if any message contains an image
        has_image = any(
            isinstance(msg.get("content"), list) and any(
                isinstance(c, dict) and c.get("type") == "image_url"
                for c in msg.get("content", [])
            )
            for msg in messages
        )

        if has_image:
            selected_model = self.valves.VISION_MODEL
        else:
            # Get last user message text
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        last_user_msg = content
                    elif isinstance(content, list):
                        last_user_msg = " ".join(
                            c.get("text", "") for c in content
                            if isinstance(c, dict) and c.get("type") == "text"
                        )
                    break
            selected_model = self._classify(last_user_msg)

        payload = {**body, "model": selected_model}
        payload.pop("pipe_id", None)

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer ollama",
        }

        async with httpx.AsyncClient() as client:
            if body.get("stream", False):
                async with client.stream(
                    "POST",
                    f"{self.valves.OPENAI_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=300,
                ) as response:
                    async for chunk in response.aiter_text():
                        yield chunk
            else:
                response = await client.post(
                    f"{self.valves.OPENAI_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=300,
                )
                yield response.text
