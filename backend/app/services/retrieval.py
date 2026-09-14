from dataclasses import dataclass
from pathlib import Path
import json
import re
from threading import Lock

import chromadb
from sentence_transformers import SentenceTransformer


@dataclass
class RetrievedChunk:
    text: str
    source: str
    page: int
    distance: float

    @property
    def citation(self) -> str:
        return f"{self.source}, page {self.page}"


class Retriever:
    def __init__(self, store_path: str, collection_name: str, model_name: str):
        self.store_path = store_path
        self.collection_name = collection_name
        self.model_name = model_name
        self.lock = Lock()
        self.client = chromadb.PersistentClient(path=store_path)
        self.collection = self.client.get_collection(collection_name)
        self.encoder = SentenceTransformer(model_name)

    def search(self, question: str, limit: int = 3) -> list[RetrievedChunk]:
        count = self.collection.count()
        if count == 0:
            return []

        embedding = self.encoder.encode(
            [question], normalize_embeddings=True
        ).tolist()
        with self.lock:
            result = self.collection.query(
                query_embeddings=embedding,
                n_results=min(limit, count),
            )

        chunks = []
        for text, metadata, distance in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source=metadata["source"],
                    page=int(metadata["page"]),
                    distance=float(distance),
                )
            )
        return chunks

    def replace_documents(self, pages: list[dict]) -> int:
        chunks = []
        for page in pages:
            for chunk_number, text in enumerate(self._split_text(page["text"]), start=1):
                chunks.append({
                    "id": f"upload-{len(chunks) + 1}",
                    "text": text,
                    "source": page["source"],
                    "page": page["page"],
                    "chunk": chunk_number,
                })

        embeddings = self.encoder.encode(
            [chunk["text"] for chunk in chunks],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        with self.lock:
            old_ids = self.collection.get()["ids"]
            if old_ids:
                self.collection.delete(ids=old_ids)
            self.collection.add(
                ids=[chunk["id"] for chunk in chunks],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[
                    {
                        "source": chunk["source"],
                        "page": chunk["page"],
                        "chunk": chunk["chunk"],
                    }
                    for chunk in chunks
                ],
                embeddings=embeddings,
            )

        config_path = Path(self.store_path) / "rag_config.json"
        config = {
            "collection_name": self.collection_name,
            "chunk_size": 700,
            "chunk_overlap": 120,
            "embedding_model": self.model_name,
            "chunk_count": len(chunks),
        }
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return len(chunks)

    @staticmethod
    def _split_text(text: str, size: int = 700, overlap: int = 120) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space
            chunks.append(text[start:end].strip())
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
        return chunks
