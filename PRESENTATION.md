# Presentation Plan

## Live demo

1. Explain that the assistant answers questions about the graduation project PDF.
2. Show the source document and the executed notebook.
3. Show the 19 stored chunks and the 10-question evaluation table.
4. Open `http://localhost:8000/docs` and call `GET /health`.
5. Open the Streamlit application and ask: `What must the frontend include?`
6. Point out the answer and its cited PDF pages.
7. Ask an unrelated question to show that the assistant stays grounded.
8. Briefly show the backend, frontend and test folders.

## Recording script

"This is my Project Guide RAG Assistant. It reads the graduation project PDF, splits its five pages into 19 overlapping chunks, creates embeddings and stores them in ChromaDB. When a user asks a question, FastAPI retrieves the closest chunks and sends only that context to the local qwen2.5 model through Ollama. The Streamlit interface displays the answer and its sources. I tested ten questions in the notebook, nine passed the correctness check, and all ten answers included sources. The backend also has tests for a valid query and invalid input."

## Before presenting

- Start Ollama and confirm `qwen2.5:3b` is available.
- Start FastAPI on port 8000.
- Start Streamlit on port 8501.
- Try the demo questions before recording.
- Record the whole application window and keep the source expander visible.
- Save a screenshot to `assets/app-screenshot.png` and add it to the README.
