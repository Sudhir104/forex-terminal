from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import scheduler
from .api import admin, auth, calendar, central_banks, currencies, internal, news, pairs, public, status
from .config import get_settings
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Forex Fundamental Terminal", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    for router in (auth.router, currencies.router, pairs.router, news.router, calendar.router,
                  central_banks.router, admin.router, status.router, internal.router, public.router):
        app.include_router(router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "demo_mode": settings.demo_mode}

    return app


app = create_app()