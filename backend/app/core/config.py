from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Project Guide Assistant"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_path: str = str(BACKEND_DIR / "data" / "vector_store")
    upload_dir: str = str(BACKEND_DIR / "data" / "uploads")
    allowed_document_root: str = str(Path.home())
    collection_name: str = "project_guide"
    frontend_origin: str = "http://localhost:8501"
    top_k: int = 6

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
    )


settings = Settings()
