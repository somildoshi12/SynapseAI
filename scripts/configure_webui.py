"""
configure_webui.py — Open WebUI post-launch configuration
Run after `docker compose up -d` to apply settings via API.

Usage:
  python3 scripts/configure_webui.py

What it does:
  - Enables SearXNG web search
  - Sets web search ON by default in every new chat
  - Installs and activates the Semantic Model Router function
"""

import json
import sys
import urllib.request
import urllib.error

WEBUI_URL = "http://localhost:3000"
SEARXNG_URL = "http://searxng:8080/search?q=<query>&format=json"


def api(method: str, path: str, data: dict = None, token: str = None) -> dict:
    url = WEBUI_URL + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}


def get_token() -> str:
    result = api("POST", "/api/v1/auths/signin",
                 {"email": "admin@localhost", "password": "admin"})
    token = result.get("token", "")
    if not token:
        print("ERROR: Could not authenticate with Open WebUI")
        sys.exit(1)
    return token


def configure_web_search(token: str):
    config = api("GET", "/api/v1/retrieval/config", token=token)
    config["web"] = config.get("web", {})
    config["web"]["ENABLE_WEB_SEARCH"] = True
    config["web"]["WEB_SEARCH_ENGINE"] = "searxng"
    config["web"]["SEARXNG_QUERY_URL"] = SEARXNG_URL
    config["web"]["WEB_SEARCH_RESULT_COUNT"] = 5
    config["web"]["WEB_SEARCH_CONCURRENT_REQUESTS"] = 10

    result = api("POST", "/api/v1/retrieval/config/update", config, token=token)
    enabled = result.get("web", {}).get("ENABLE_WEB_SEARCH", False)
    print(f"  Web search enabled: {enabled}")

    # Set web search ON by default in new chats
    api("POST", "/api/v1/users/user/settings/update", {
        "ui": {
            "version": "0.8.8",
            "memory": True,
            "params": {"web_search": True}
        }
    }, token=token)
    print("  Web search default-on in new chats: True")


def install_model_router(token: str):
    # Check if already installed
    funcs = api("GET", "/api/v1/functions/", token=token)
    if isinstance(funcs, list):
        if any(f.get("id") == "semantic_model_router" for f in funcs):
            print("  Semantic Model Router already installed")
            return

    # Read the function code from the functions/ directory
    import os
    func_path = os.path.join(os.path.dirname(__file__), "..", "functions",
                             "semantic_model_router.py")
    with open(func_path) as f:
        router_code = f.read()

    result = api("POST", "/api/v1/functions/create", {
        "id": "semantic_model_router",
        "name": "Semantic Model Router",
        "content": router_code,
        "is_active": True,
        "is_global": True,
        "meta": {
            "description": "Routes to qwen3.5:9b (coding/general) or deepseek-r1:8b (reasoning)",
            "manifest": {}
        }
    }, token=token)

    if "_error" not in result:
        api("POST", "/api/v1/functions/id/semantic_model_router/toggle", {}, token=token)
        api("POST", "/api/v1/functions/id/semantic_model_router/toggle/global", {}, token=token)
        print(f"  Installed: {result.get('name')}")
    else:
        print(f"  Error installing router: {result}")


def main():
    print("Configuring Open WebUI...")
    token = get_token()
    print("  Authenticated")

    print("\n  → Web search:")
    configure_web_search(token)

    print("\n  → Semantic Model Router:")
    install_model_router(token)

    print("\nDone.")


if __name__ == "__main__":
    main()
