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
                citation="Graduation_Project_L2.pdf, page 3",
            )
        ]


class FakeGenerator:
    def answer(self, question, chunks):
        return "Use FastAPI [Graduation_Project_L2.pdf, page 3]."


def make_client():
    app = create_app(load_services=False)
    app.state.retriever = FakeRetriever()
    app.state.generator = FakeGenerator()
    app.state.top_k = 3
    return TestClient(app)


def test_query_happy_path():
    with make_client() as client:
        response = client.post("/query", json={"question": "What backend is needed?"})

    assert response.status_code == 200
    assert "FastAPI" in response.json()["answer"]
    assert response.json()["sources"] == ["Graduation_Project_L2.pdf, page 3"]


def test_query_invalid_input():
    with make_client() as client:
        response = client.post("/query", json={"question": ""})

    assert response.status_code == 422

