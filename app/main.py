# app/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Routers
from app.api.routers import (
    whatsapp, notifications, auth, dashboard, courses, flows, crm, messages, users,
    analytics, predictive, exam_debt
)

# ---- Optional caching (micro-cache) ----
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
try:
    from fastapi_cache.backends.redis import RedisBackend
    from redis.asyncio import from_url as redis_from_url
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False

app = FastAPI(
    title="Moodle Chatbot Backend",
    description="Backend funcional para recibir y enviar mensajes de WhatsApp.",
    version="1.2.0",
)

# ---- GZip to reduce payload size ----
app.add_middleware(GZipMiddleware, minimum_size=500)

# ---- CORS: allow localhost and LAN:3000 ----
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://172.16.10.250:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|\d{1,3}(?:\.\d{1,3}){3}):3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(whatsapp.router,       prefix="/api/whatsapp", tags=["Whatsapp"])
app.include_router(notifications.router,  prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(auth.router,           prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router,      prefix="/api", tags=["Dashboard"])
app.include_router(courses.router,        prefix="/api", tags=["Courses"])
app.include_router(flows.router,          prefix="/api", tags=["Flows"])
app.include_router(crm.router,            prefix="/api", tags=["CRM"])
app.include_router(messages.router,       prefix="/api", tags=["Messages"])
app.include_router(users.router,          prefix="/api/users", tags=["Users"])
app.include_router(analytics.router,      prefix="/api", tags=["Analytics"])
app.include_router(predictive.router,     prefix="/api", tags=["predictive"])
app.include_router(exam_debt.router,      prefix="/api", tags=["ExamDebt"])

# 👇 IMPORTANTE: este router YA tiene prefix="/api/exams/debt" dentro del archivo.
#    No le agregues otro prefix acá, o te quedará /api/api/exams/debt/*
app.include_router(exam_debt.router)  # <- sin prefix ni tags extra

@app.on_event("startup")
async def _init_cache():
    # Use Redis if available, else fall back to in-memory (no extra deps)
    if _HAS_REDIS:
        try:
            redis = redis_from_url("redis://localhost:6379", encoding="utf8", decode_responses=True)
            FastAPICache.init(RedisBackend(redis), prefix="cache:")
            return
        except Exception:
            pass
    FastAPICache.init(InMemoryBackend(), prefix="cache:")

@app.get("/")
def read_root():
    return {"status": "API is running"}