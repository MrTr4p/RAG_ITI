from pathlib import Path, PurePosixPath

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.schemas.query import FolderRequest, QueryRequest, QueryResponse, UploadResponse
from app.services.ingestion import extract_documents, save_uploads


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


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    uploaded = []
    for file in files:
        name = (file.filename or "document").replace("\\", "/")
        safe_parts = [part for part in PurePosixPath(name).parts if part not in {".", ".."}]
        safe_name = "/".join(safe_parts)
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File is too large: {safe_name}")
        uploaded.append((safe_name, content))

    try:
        pages = extract_documents(uploaded)
        chunk_count = retriever.replace_documents(pages)
        save_uploads(request.app.state.upload_dir, uploaded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        message="Document index updated",
        files=[name for name, _ in uploaded],
        chunks=chunk_count,
    )


@router.post("/index-folder", response_model=UploadResponse)
def index_folder(body: FolderRequest, request: Request) -> UploadResponse:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    folder = Path(body.path).expanduser().resolve()
    allowed_root = Path(request.app.state.allowed_document_root).resolve()
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail="Folder does not exist")
    if folder != allowed_root and allowed_root not in folder.parents:
        raise HTTPException(status_code=400, detail="Folder must be inside your home directory")

    uploaded = []
    total_size = 0
    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".txt"}:
            continue
        content = path.read_bytes()
        total_size += len(content)
        if len(uploaded) >= 100 or total_size > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Folder is too large")
        uploaded.append((path.relative_to(folder).as_posix(), content))

    if not uploaded:
        raise HTTPException(status_code=400, detail="No PDF or TXT files found")

    try:
        pages = extract_documents(uploaded)
        chunk_count = retriever.replace_documents(pages)
        save_uploads(request.app.state.upload_dir, uploaded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        message="Folder index updated",
        files=[name for name, _ in uploaded],
        chunks=chunk_count,
    )
