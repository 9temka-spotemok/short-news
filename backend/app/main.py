"""
Compatibility module exposing the FastAPI application for tests.

Pytest fixtures import `app.main` to retrieve the FastAPI `app` instance.
The actual application entrypoint lives in `backend/main.py`, so we re-export
the same object here to keep import paths stable.
"""

from main import app  # noqa: F401  (re-export for consumers expecting app.main)




