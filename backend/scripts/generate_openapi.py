"""
Utility script to regenerate OpenAPI schema for the FastAPI backend.

Usage:
    poetry run python scripts/generate_openapi.py

The script writes the schema to the repository root as `openapi.json`.
Minimal environment defaults are provided to avoid import errors, but real
deployments should supply the proper environment variables.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

DEFAULT_ENV = {
    "SECRET_KEY": "generate-openapi-placeholder",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
}

for key, value in DEFAULT_ENV.items():
    os.environ.setdefault(key, value)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlalchemy.ext.asyncio as sa_async

_create_async_engine = sa_async.create_async_engine


def _patched_create_async_engine(url: str, **kw):
    if url.startswith("sqlite"):
        kw.pop("pool_size", None)
        kw.pop("max_overflow", None)
    return _create_async_engine(url, **kw)


sa_async.create_async_engine = _patched_create_async_engine

from main import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    output_path = Path(__file__).resolve().parents[2] / "openapi.json"
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI schema written to {output_path}")


if __name__ == "__main__":
    main()

