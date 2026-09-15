# TeachBack AI

A RAG-based learning assistant built around the idea that "to teach is to learn twice." Students upload PDF or text learning material, teach a topic to an AI student, receive document-grounded feedback, correct an intentional mistake, and track their mastery over repeated attempts.

## Main features

- Chat with uploaded learning material and view page citations
- Generate important topics from the documents
- Teach different audiences: a child, beginner, classmate, professor or interviewer
- Receive accuracy, clarity, completeness and mastery scores
- Find missing points and misconceptions
- Answer an adaptive follow-up question
- Correct a believable mistake created by the AI student
- Reteach a topic and compare attempts
- Track mastered and weak topics in a progress dashboard

## Architecture

```mermaid
flowchart LR
    A[PDF or TXT material] --> B[Text extraction and chunking]
    B --> C[Sentence Transformer]
    C --> D[(ChromaDB)]
    E[Student explanation] --> F[FastAPI]
    F --> D
    D --> G[Relevant source context]
    G --> H[Ollama qwen2.5:3b]
    H --> I[Scores and feedback]
    I --> J[Follow-up and mistake challenge]
    J --> K[(Progress history)]
```

## Tech stack

- Python 3.12
- PyPDF, Sentence Transformers and ChromaDB
- Ollama with `qwen2.5:3b`
- FastAPI and Streamlit
- Pytest

## Project structure

```text
notebooks/                 RAG pipeline and evaluation
data/source_documents/    Optional local learning material
backend/app/               FastAPI application
backend/data/vector_store/ Persisted Chroma database
backend/tests/             API tests
frontend/                  Streamlit learning application
evaluation/                Saved ten-question results
PRESENTATION.md            Demo and recording outline
```

## RAG and TeachBack method

The user supplies PDF or TXT learning material. Text is split into 700-character chunks with 120 characters of overlap. The overlap helps ideas near a chunk boundary stay together.

Embeddings use `sentence-transformers/all-MiniLM-L6-v2`. Relevant chunks are added to a strict prompt that asks Ollama to use only the supplied material. During a TeachBack session, the model evaluates the student's explanation, produces three scores, identifies knowledge gaps, asks a follow-up question and writes a clearer example explanation. Each attempt is saved locally for the dashboard.

### Vector store schema

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Document, page and chunk identifier |
| `document` | string | Extracted chunk text |
| `source` | string | Original filename |
| `page` | integer | PDF page number |
| `chunk` | integer | Chunk number on the page |

## Setup

Requirements: Python 3.12, Git and a running Ollama installation.

```bash
git clone <repository-url>
cd RagFinalProject
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
ollama pull qwen2.5:3b
```

Run the notebook once to rebuild the vector database if needed:

```bash
jupyter notebook notebooks/rag_pipeline.ipynb
```

Copy the environment examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Start the backend from one terminal:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

Start the frontend from another terminal:

```bash
source .venv/bin/activate
cd frontend
streamlit run app.py
```

Open `http://localhost:8501`. API documentation is at `http://localhost:8000/docs`.

Use the sidebar to upload several PDF/TXT files, or paste the path of a local folder and click **Index local folder**. A new upload replaces the current document index.

## Environment variables

| Variable | Example | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local generation model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `VECTOR_STORE_PATH` | `data/vector_store` | Chroma database path |
| `PROGRESS_FILE` | `data/teachback_progress.json` | Saved TeachBack attempts |
| `COLLECTION_NAME` | `project_guide` | Chroma collection |
| `FRONTEND_ORIGIN` | `http://localhost:8501` | Allowed browser origin |
| `TOP_K` | `6` | Retrieved chunks per question |
| `API_BASE_URL` | `http://localhost:8000` | Frontend API address |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check service and index status |
| `POST` | `/query` | Ask a document-grounded question |
| `POST` | `/upload` | Upload and index PDF/TXT files |
| `POST` | `/index-folder` | Index a local document folder |
| `POST` | `/teachback/topics` | Generate topics from the material |
| `POST` | `/teachback/evaluate` | Score and evaluate an explanation |
| `POST` | `/teachback/challenge` | Create an intentional mistake |
| `POST` | `/teachback/correction` | Check the student's correction |
| `GET` | `/teachback/progress` | Return saved attempts and summary |

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@document.pdf" \
  -F "files=@notes.txt"
```

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What must the frontend include?"}'
```

Example response:

```json
{
  "answer": "The frontend needs a chat interface and must show cited sources.",
  "sources": ["course_notes.pdf, page 4"]
}
```

## Evaluation

The original RAG evaluation results remain available in `evaluation/results.csv`. TeachBack responses use the same retrieved page evidence, and the progress dashboard stores the overall score from each attempt.

## Tests

```bash
cd backend
pytest
```

The tests cover document questions, uploads, local folder indexing, topic generation, TeachBack evaluation, saved progress, mistake challenges and corrections.

The setup and tests were also checked from a fresh local clone of the repository.

## Presentation

The live-demo order and recording outline are in `PRESENTATION.md`.

## Screenshot

![TeachBack AI application](assets/app-screenshot.png)
