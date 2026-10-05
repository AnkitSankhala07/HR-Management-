"""Dayflow FastAPI service - AI HR Copilot + Analytics (reads the same MySQL as Django)."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import ai, analytics
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dayflow.fastapi")

app = FastAPI(title="Dayflow HRMS - AI & Analytics Service", version="1.0.0",
              description="Authenticated with short-lived JWTs issued by Django. Every request re-checks the user's role in MySQL.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(ai.router)
app.include_router(analytics.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
