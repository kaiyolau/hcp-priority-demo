"""Vercel serverless entrypoint. Vercel serves the ASGI `app` exported here."""

import sys
from pathlib import Path

# Make the repo root importable so `backend` resolves inside the function bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import app  # noqa: E402

__all__ = ["app"]
