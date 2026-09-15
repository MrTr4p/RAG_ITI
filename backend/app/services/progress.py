import json
from pathlib import Path
from threading import Lock


class ProgressStore:
    def __init__(self, file_path: str):
        self.path = Path(file_path)
        self.lock = Lock()

    def list_sessions(self) -> list[dict]:
        with self.lock:
            if not self.path.exists():
                return []
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []

    def save(self, session: dict) -> None:
        with self.lock:
            sessions = []
            if self.path.exists():
                try:
                    sessions = json.loads(self.path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    sessions = []
            sessions.append(session)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(sessions, indent=2), encoding="utf-8")
