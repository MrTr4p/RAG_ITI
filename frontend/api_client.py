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


def index_folder(folder_path: str) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/index-folder",
        json={"path": folder_path},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def generate_topics(count: int = 5) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/teachback/topics",
        json={"count": count},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def evaluate_teachback(topic: str, explanation: str, audience: str) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/teachback/evaluate",
        json={"topic": topic, "explanation": explanation, "audience": audience},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def create_challenge(topic: str) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/teachback/challenge",
        json={"topic": topic},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def check_correction(topic: str, statement: str, correction: str) -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.post(
        f"{api_base_url}/teachback/correction",
        json={"topic": topic, "statement": statement, "correction": correction},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def get_progress() -> dict:
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is not set")

    response = requests.get(f"{api_base_url}/teachback/progress", timeout=30)
    response.raise_for_status()
    return response.json()
