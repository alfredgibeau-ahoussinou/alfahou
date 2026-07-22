#!/usr/bin/env python3
"""Entrypoint production (Render / Docker)."""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8787"))
    uvicorn.run("alfahou.api.app:app", host="0.0.0.0", port=port, proxy_headers=True)


if __name__ == "__main__":
    main()
