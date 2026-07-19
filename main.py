"""
Structured Output Agent - Main entry point.

Run with:
    python main.py
    # or
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
import sys

import uvicorn

from agent.api import create_app
from agent.core import get_agent

# Create the FastAPI application
app = create_app(agent=get_agent())

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload_enabled = os.environ.get("RELOAD", "false").lower() == "true"

    print(f"🚀 Starting Structured Output Agent API")
    print(f"📡 Listening on {host}:{port}")
    print(f"📚 API docs: http://{host}:{port}/docs")
    print(f"🔧 Reload: {reload_enabled}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
