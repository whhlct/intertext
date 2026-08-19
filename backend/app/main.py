from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.reader import router as reader_router
from app.api.routes.texts import router as texts_router

app = FastAPI(title="Intertext API", version="0.1.0")
app.include_router(health_router)
app.include_router(texts_router)
app.include_router(reader_router)
