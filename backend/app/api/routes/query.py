from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.schemas.query import (
    ChallengeRequest,
    ChallengeResponse,
    CorrectionRequest,
    CorrectionResponse,
    FolderRequest,
    ProgressResponse,
    ProgressSummary,
    QueryRequest,
    QueryResponse,
    TeachBackRequest,
    TeachBackResponse,
    TeachBackStartRequest,
    TeachBackStartResponse,
    TeachBackTurnRequest,
    TeachBackTurnResponse,
    TopicRequest,
    TopicResponse,
    UploadResponse,
)
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


@router.post("/teachback/topics", response_model=TopicResponse)
def teachback_topics(body: TopicRequest, request: Request) -> TopicResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    try:
        chunks = retriever.sample_chunks(16)
        topics = generator.generate_topics(chunks, body.count)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Topic generation failed: {exc}") from exc
    if not topics:
        raise HTTPException(status_code=400, detail="Upload learning material first")

    return TopicResponse(topics=topics, sources=_sources(chunks))


@router.post("/teachback/start", response_model=TeachBackStartResponse)
def start_teachback(
    body: TeachBackStartRequest, request: Request
) -> TeachBackStartResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    requested_topic = (body.topic or "").strip()
    if body.topic is not None and len(requested_topic) < 2:
        raise HTTPException(status_code=400, detail="Topic must contain at least two characters")

    try:
        if requested_topic:
            topic = requested_topic
            chunks = retriever.search(topic, 8)
        else:
            chunks = retriever.sample_chunks(16)
            topics = generator.generate_topics(chunks, 1)
            topic = topics[0] if topics else ""
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Session start failed: {exc}") from exc
    if not topic or not chunks:
        raise HTTPException(status_code=400, detail="Upload learning material first")

    return TeachBackStartResponse(
        topic=topic,
        message=f"I am learning about {topic}. Could you explain it to me in your own words?",
        sources=_sources(chunks),
    )


@router.post("/teachback/turn", response_model=TeachBackTurnResponse)
def continue_teachback(
    body: TeachBackTurnRequest, request: Request
) -> TeachBackTurnResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")
    if body.conversation[-1].role != "teacher":
        raise HTTPException(status_code=400, detail="The latest turn must be from the teacher")

    try:
        chunks = retriever.search(body.topic, 4)
        if not chunks:
            raise ValueError("Upload learning material first")
        question = generator.ask_follow_up(
            body.topic,
            body.audience,
            [turn.model_dump() for turn in body.conversation],
            chunks,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Student reply failed: {exc}") from exc

    return TeachBackTurnResponse(question=question, sources=_sources(chunks))


@router.post("/teachback/evaluate", response_model=TeachBackResponse)
def evaluate_teachback(body: TeachBackRequest, request: Request) -> TeachBackResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    progress_store = request.app.state.progress_store
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    try:
        chunks = retriever.search(f"{body.topic}. {body.explanation[:300]}", 8)
        if not chunks:
            raise ValueError("Upload learning material first")
        result = generator.evaluate_teachback(
            body.topic, body.explanation, body.audience, chunks
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evaluation failed: {exc}") from exc

    old_sessions = progress_store.list_sessions()
    attempt = 1 + sum(
        str(item.get("topic", "")).casefold() == body.topic.casefold()
        for item in old_sessions
    )
    session = TeachBackResponse(
        session_id=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        topic=body.topic,
        audience=body.audience,
        attempt=attempt,
        scores=result["scores"],
        correct_points=result["correct_points"],
        missing_points=result["missing_points"],
        misconceptions=result["misconceptions"],
        jargon=result["jargon"],
        feedback=result["feedback"],
        follow_up_question=result["follow_up_question"],
        improved_explanation=result["improved_explanation"],
        mastered=result["scores"]["overall"] >= 80,
        sources=_sources(chunks),
    )
    progress_store.save(session.model_dump(mode="json"))
    return session


@router.post("/teachback/challenge", response_model=ChallengeResponse)
def teachback_challenge(body: ChallengeRequest, request: Request) -> ChallengeResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    try:
        chunks = retriever.search(body.topic, 6)
        statement = generator.make_challenge(body.topic, chunks)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Challenge failed: {exc}") from exc
    if not statement:
        raise HTTPException(status_code=400, detail="Upload learning material first")
    return ChallengeResponse(statement=statement, sources=_sources(chunks))


@router.post("/teachback/correction", response_model=CorrectionResponse)
def check_correction(body: CorrectionRequest, request: Request) -> CorrectionResponse:
    retriever = getattr(request.app.state, "retriever", None)
    generator = getattr(request.app.state, "generator", None)
    if retriever is None or generator is None:
        raise HTTPException(status_code=503, detail="RAG services are not ready")

    try:
        chunks = retriever.search(f"{body.topic}. {body.statement}", 6)
        result = generator.check_correction(
            body.topic, body.statement, body.correction, chunks
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Correction check failed: {exc}") from exc
    return CorrectionResponse(**result, sources=_sources(chunks))


@router.get("/teachback/progress", response_model=ProgressResponse)
def teachback_progress(request: Request) -> ProgressResponse:
    saved = request.app.state.progress_store.list_sessions()
    sessions = []
    for item in saved:
        try:
            sessions.append(TeachBackResponse(**item))
        except Exception:
            continue

    latest = {}
    for session in sessions:
        latest[session.topic.casefold()] = session
    scores = [session.scores.overall for session in sessions]
    weak_topics = [
        session.topic for session in latest.values() if session.scores.overall < 70
    ]
    summary = ProgressSummary(
        total_sessions=len(sessions),
        mastered_topics=sum(session.mastered for session in latest.values()),
        average_score=round(sum(scores) / len(scores)) if scores else 0,
        weak_topics=weak_topics,
    )
    return ProgressResponse(summary=summary, sessions=list(reversed(sessions[-50:])))


def _sources(chunks) -> list[str]:
    return list(dict.fromkeys(chunk.citation for chunk in chunks))
