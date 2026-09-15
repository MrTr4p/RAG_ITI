# Presentation Plan

## Live demo

1. Explain the idea: students learn a topic by teaching it to an AI student.
2. Upload course notes and generate important topics.
3. Choose an audience and explain one topic in your own words.
4. Show the accuracy, clarity, completeness and mastery scores.
5. Show the missing points, misconceptions and cited PDF pages.
6. Answer the AI student's follow-up question by starting a reteach attempt.
7. Open the mistake challenge and correct the false statement.
8. Open the progress dashboard and show the saved attempts.
9. Briefly show the API documentation and automated tests.

## Recording script

"This is TeachBack AI, a learning assistant based on the idea that to teach is to learn twice. A student uploads learning material and explains a generated topic to an AI student. The backend retrieves the relevant document sections and a local Ollama model evaluates the explanation. It scores accuracy, clarity and completeness, finds missing ideas and misconceptions, asks a follow-up question and creates a false statement for the student to correct. Every attempt is saved in the progress dashboard, and the source pages keep the feedback grounded in the uploaded material."

## Before presenting

- Start Ollama and confirm `qwen2.5:3b` is available.
- Start FastAPI on port 8000.
- Start Streamlit on port 8501.
- Try the demo questions before recording.
- Complete one TeachBack session so the progress dashboard has data.
- Record the whole application window and keep the evidence expander visible.
- Save a screenshot to `assets/app-screenshot.png` and add it to the README.
