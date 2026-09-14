import os

import requests
from dotenv import load_dotenv


load_dotenv()


def ask_question(question: str) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/query",
        json={"question": question},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def upload_documents(uploaded_files) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    files = [
        (
            "files",
            (file.name, file.getvalue(), file.type or "application/octet-stream"),
        )
        for file in uploaded_files
    ]
    response = requests.post(
        f"{api_base_url}/upload",
        files=files,
        timeout=300,
    )
    response.raise_for_status()
    return response.json()
