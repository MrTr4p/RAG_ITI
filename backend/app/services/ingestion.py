from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


ALLOWED_TYPES = {".pdf", ".txt"}


def extract_documents(files: list[tuple[str, bytes]]) -> list[dict]:
    pages = []
    for name, content in files:
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported file: {name}")

        if suffix == ".pdf":
            reader = PdfReader(BytesIO(content))
            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"source": name, "page": page_number, "text": text})
        else:
            text = content.decode("utf-8", errors="ignore")
            if text.strip():
                pages.append({"source": name, "page": 1, "text": text})

    if not pages:
        raise ValueError("No text could be extracted from the uploaded files")
    return pages


def save_uploads(upload_dir: str, files: list[tuple[str, bytes]]) -> None:
    folder = Path(upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    for old_file in folder.iterdir():
        if old_file.is_file():
            old_file.unlink()

    for number, (name, content) in enumerate(files, start=1):
        safe_name = Path(name).name
        (folder / f"{number:03d}_{safe_name}").write_bytes(content)
