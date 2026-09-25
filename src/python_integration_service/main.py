from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from python_integration_service.api.vendor import router as vendor_router
from python_integration_service.composition import create_vendor_client
from python_integration_service.config import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()

    with create_vendor_client(settings) as vendor_client:
        app.state.vendor_client = vendor_client
        yield


app = FastAPI(
    title="Python Integration Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(vendor_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
