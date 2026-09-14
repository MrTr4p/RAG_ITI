from dataclasses import dataclass

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

