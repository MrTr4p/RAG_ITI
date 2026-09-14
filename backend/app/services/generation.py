import re

import ollama

from app.services.retrieval import RetrievedChunk


class Generator:
    def __init__(self, base_url: str, model: str):
        self.client = ollama.Client(host=base_url, timeout=120)
        self.model = model

    def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "I could not find this information in the documents."

        context = "\n\n".join(
            f"Source: [{chunk.citation}]\n{chunk.text}" for chunk in chunks
        )
        prompt = f"""Answer the question using only the context below.
If the answer is missing, say you could not find it in the documents.
Keep the answer short and cite facts like [filename, page 2].

Context:
{context}

Question: {question}
Answer:"""

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        answer = re.sub(
            r"\s*\[[^\]]+,\s*page\s+\d+\]", "", response.message.content
        ).strip()
        source_names = dict.fromkeys(chunk.citation for chunk in chunks)
        citations = ", ".join(f"[{source}]" for source in source_names)
        if "Sources:" not in answer:
            answer = f"{answer}\n\nSources: {citations}"
        return answer
