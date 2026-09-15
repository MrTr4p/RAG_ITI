from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import create_app


class FakeCollection:
    def count(self):
        return 1


class FakeRetriever:
    collection = FakeCollection()

    def search(self, question, limit):
        return [
            SimpleNamespace(
                text="The project needs a FastAPI backend.",
                citation="course_notes.pdf, page 3",
            )
        ]

    def replace_documents(self, pages):
        return len(pages)

    def sample_chunks(self, limit):
        return self.search("topics", limit)


class FakeGenerator:
    def answer(self, question, chunks):
        return "Use FastAPI [course_notes.pdf, page 3]."

    def generate_topics(self, chunks, count):
        return ["FastAPI", "RAG workflow", "Vector databases"][:count]

    def evaluate_teachback(self, topic, explanation, audience, chunks):
        return {
            "scores": {
                "accuracy": 90,
                "clarity": 80,
                "completeness": 70,
                "overall": 80,
            },
            "correct_points": ["FastAPI provides the backend"],
            "missing_points": ["Explain the API routes"],
            "misconceptions": [],
            "jargon": [
                {
                    "term": "API",
                    "reason": "A beginner may not know this abbreviation.",
                    "simple_version": "A way for programs to communicate.",
                    "question": "Can you explain API without using the term API?",
                }
            ],
            "feedback": "Good explanation with one missing detail.",
            "follow_up_question": "What does the query route return?",
            "improved_explanation": "FastAPI exposes the RAG pipeline through API routes.",
        }

    def make_challenge(self, topic, chunks):
        return "FastAPI stores document embeddings by itself."

    def check_correction(self, topic, statement, correction, chunks):
        return {"correct": True, "score": 95, "feedback": "Correct. Chroma stores them."}


class FakeProgressStore:
    def __init__(self):
        self.sessions = []

    def list_sessions(self):
        return self.sessions

    def save(self, session):
        self.sessions.append(session)


def make_client():
    app = create_app(load_services=False)
    app.state.retriever = FakeRetriever()
    app.state.generator = FakeGenerator()
    app.state.top_k = 3
    app.state.progress_store = FakeProgressStore()
    return TestClient(app)


def test_query_happy_path():
    with make_client() as client:
        response = client.post("/query", json={"question": "What backend is needed?"})

    assert response.status_code == 200
    assert "FastAPI" in response.json()["answer"]
    assert response.json()["sources"] == ["course_notes.pdf, page 3"]


def test_query_invalid_input():
    with make_client() as client:
        response = client.post("/query", json={"question": ""})

    assert response.status_code == 422


def test_upload_text_file(tmp_path):
    client = make_client()
    client.app.state.upload_dir = str(tmp_path)
    with client:
        response = client.post(
            "/upload",
            files=[("files", ("notes.txt", b"A short test document", "text/plain"))],
        )

    assert response.status_code == 200
    assert response.json()["chunks"] == 1
    assert list(tmp_path.iterdir())[0].name == "001_notes.txt"


def test_index_local_folder(tmp_path):
    source_folder = tmp_path / "documents"
    upload_folder = tmp_path / "uploads"
    source_folder.mkdir()
    (source_folder / "notes.txt").write_text("A local folder document")

    client = make_client()
    client.app.state.upload_dir = str(upload_folder)
    client.app.state.allowed_document_root = str(tmp_path)
    with client:
        response = client.post("/index-folder", json={"path": str(source_folder)})

    assert response.status_code == 200
    assert response.json()["files"] == ["notes.txt"]
    assert response.json()["chunks"] == 1


def test_generate_teachback_topics():
    with make_client() as client:
        response = client.post("/teachback/topics", json={"count": 3})

    assert response.status_code == 200
    assert response.json()["topics"] == ["FastAPI", "RAG workflow", "Vector databases"]
    assert response.json()["sources"] == ["course_notes.pdf, page 3"]


def test_evaluate_teachback_and_save_progress():
    client = make_client()
    with client:
        response = client.post(
            "/teachback/evaluate",
            json={
                "topic": "FastAPI",
                "explanation": "FastAPI is used to create the backend API for the RAG system.",
                "audience": "A beginner",
            },
        )
        progress = client.get("/teachback/progress")

    assert response.status_code == 200
    assert response.json()["scores"]["overall"] == 80
    assert response.json()["mastered"] is True
    assert response.json()["jargon"][0]["term"] == "API"
    assert progress.json()["summary"]["total_sessions"] == 1
    assert progress.json()["summary"]["mastered_topics"] == 1


def test_mistake_challenge_and_correction():
    with make_client() as client:
        challenge = client.post("/teachback/challenge", json={"topic": "FastAPI"})
        correction = client.post(
            "/teachback/correction",
            json={
                "topic": "FastAPI",
                "statement": challenge.json()["statement"],
                "correction": "Chroma stores embeddings, while FastAPI exposes the API routes.",
            },
        )

    assert challenge.status_code == 200
    assert correction.status_code == 200
    assert correction.json()["correct"] is True
    assert correction.json()["score"] == 95
