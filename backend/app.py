"""FastAPI app: scored HCP list and grounded AI explanations."""

from __future__ import annotations

import json
import logging
import os
import time
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .explain import ExplanationService
from .llm import LLMClient, LLMConfig
from .scoring import SCORING_VERSION, ScoringEngine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("hcp-api")


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "on", "yes"}


@lru_cache
def get_engine() -> ScoringEngine:
    return ScoringEngine()


@lru_cache
def get_explainer() -> ExplanationService:
    config = LLMConfig.from_env()
    return ExplanationService(
        llm=LLMClient(config) if config else None,
        enabled=_flag("FEATURE_AI_EXPLAIN", True),
    )


app = FastAPI(title="HCP Priority Demo API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.middleware("http")
async def instrument(request: Request, call_next):
    """Structured request log + Server-Timing header (visible in browser devtools)."""
    started = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - started) * 1000
    response.headers["Server-Timing"] = f"app;dur={ms:.1f}"
    log.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "durationMs": round(ms, 1),
    }))
    return response


@app.get("/api/health")
def health() -> dict:
    explainer = get_explainer()
    return {
        "status": "ok",
        "scoringVersion": SCORING_VERSION,
        "flags": {"aiExplain": _flag("FEATURE_AI_EXPLAIN", True)},
        "llmConfigured": explainer.llm_enabled,
    }


@app.get("/api/doctors")
def list_doctors() -> dict:
    doctors = get_engine().all()
    return {"scoringVersion": SCORING_VERSION, "count": len(doctors), "doctors": doctors}


@app.get("/api/doctors/{doctor_id}")
def get_doctor(doctor_id: str) -> dict:
    doctor = get_engine().get(doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@app.get("/api/doctors/{doctor_id}/explain")
def explain_doctor(doctor_id: str) -> dict:
    engine = get_engine()
    doctor = engine.get(doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    result = get_explainer().explain(doctor, total=len(engine.all()))
    log.info(json.dumps({
        "event": "explain",
        "doctorId": doctor_id,
        "source": result.source,
        "cached": result.cached,
        "attempts": result.attempts,
        "latencyMs": result.latencyMs,
        "fallbackReason": result.fallbackReason,
    }))
    return result.to_dict()
