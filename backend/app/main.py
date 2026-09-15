from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.query import router
from app.core.config import settings
from app.services.generation import Generator
from app.services.progress import ProgressStore
from app.services.retrieval import Retriever
from app.utils.logging_config import setup_logging


def create_app(load_services: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if load_services:
            app.state.retriever = Retriever(
                settings.vector_store_path,
                settings.collection_name,
                settings.embedding_model,
            )
            app.state.generator = Generator(
                settings.ollama_base_url,
                settings.ollama_model,
            )
            app.state.top_k = settings.top_k
        yield

    setup_logging()
    api = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    api.state.upload_dir = settings.upload_dir
    api.state.allowed_document_root = settings.allowed_document_root
    api.state.progress_store = ProgressStore(settings.progress_file)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api.include_router(router)
    return api


app = create_app()
