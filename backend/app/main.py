from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import health as health_router
from app.api.v1.routers import videos as videos_router
from app.core.config import settings
from app.core.database import engine
from app.core.redis import close_redis_client, get_redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and gracefully close shared infrastructure connections."""
    get_redis_client()
    yield
    await close_redis_client()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        "REST API видеохостинга (YouTube Clone MVP). "
        "Слоистая архитектура, потоковая загрузка в MinIO, HTTP Range-стриминг и фоновая обработка FFmpeg."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(videos_router.router, prefix="/api/v1")
