from fastapi import APIRouter, HTTPException, Request

from app.schemas.query import QueryRequest, QueryResponse


router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    retriever = getattr(request.app.state, "retriever", None)
    return {
        "status": "ok" if retriever else "starting",
        "chunks": retriever.collection.count() if retriever else 0,
    }


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, request: Request) -> QueryResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    try:
        chunks = retriever.search(body.question, request.app.state.top_k)
        answer = generator.answer(body.question, chunks)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Query failed: {exc}") from exc

    sources = list(dict.fromkeys(chunk.citation for chunk in chunks))
    return QueryResponse(answer=answer, sources=sources)

