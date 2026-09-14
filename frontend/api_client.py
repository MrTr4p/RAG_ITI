import os

import requests
from dotenv import load_dotenv


load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def ask_question(question: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/query",
        json={"question": question},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()

