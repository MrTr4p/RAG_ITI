import json
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

    def generate_topics(
        self, chunks: list[RetrievedChunk], count: int
    ) -> list[str]:
        if not chunks:
            return []

        prompt = f"""Read the learning material and choose {count} important topics a student can teach back.
Use short, specific topic names. Return only JSON in this form:
{{"topics": ["Topic one", "Topic two"]}}

Material:
{self._context(chunks)}"""
        data = self._json_chat(prompt)
        topics = data.get("topics", [])
        return [str(topic).strip() for topic in topics if str(topic).strip()][:count]

    def evaluate_teachback(
        self,
        topic: str,
        explanation: str,
        audience: str,
        chunks: list[RetrievedChunk],
    ) -> dict:
        prompt = f"""Evaluate a student's teach-back using only the material below.
The topic is: {topic}
The intended audience is: {audience}

Student explanation:
{explanation}

Give accuracy, clarity and completeness scores from 0 to 100. Be supportive but honest.
Find correct ideas, important missing ideas and actual misconceptions. Ask one short follow-up question.
Detect up to five technical terms the student used without explaining clearly enough for the intended audience.
For every jargon term, explain the problem, give a simpler version and ask the student to explain it without using the term.
Do not mark a technical term as jargon when the student already explained it clearly.
Write a better explanation suitable for the intended audience.
Return only JSON with this exact structure:
{{
  "scores": {{"accuracy": 0, "clarity": 0, "completeness": 0}},
  "correct_points": [],
  "missing_points": [],
  "misconceptions": [],
  "jargon": [{{"term": "", "reason": "", "simple_version": "", "question": ""}}],
  "feedback": "",
  "follow_up_question": "",
  "improved_explanation": ""
}}

Material:
{self._context(chunks)}"""
        data = self._json_chat(prompt)
        raw_scores = data.get("scores", {})
        scores = {
            name: self._score(raw_scores.get(name, 0))
            for name in ("accuracy", "clarity", "completeness")
        }
        scores["overall"] = round(sum(scores.values()) / 3)
        return {
            "scores": scores,
            "correct_points": self._text_list(data.get("correct_points")),
            "missing_points": self._text_list(data.get("missing_points")),
            "misconceptions": self._text_list(data.get("misconceptions")),
            "jargon": self._jargon_items(data.get("jargon")),
            "feedback": str(data.get("feedback", "Keep teaching and improve the missing points.")),
            "follow_up_question": str(data.get("follow_up_question", "Can you explain the main idea with an example?")),
            "improved_explanation": str(data.get("improved_explanation", explanation)),
        }

    def make_challenge(self, topic: str, chunks: list[RetrievedChunk]) -> str:
        prompt = f"""Create one believable but incorrect statement about {topic}.
The student must find and correct the mistake. Do not reveal the correction.
Return only JSON like {{"statement": "..."}}.

Material:
{self._context(chunks)}"""
        return str(self._json_chat(prompt).get("statement", "")).strip()

    def check_correction(
        self,
        topic: str,
        statement: str,
        correction: str,
        chunks: list[RetrievedChunk],
    ) -> dict:
        prompt = f"""Check whether the student correctly fixed the false statement using only the material.
Topic: {topic}
False statement: {statement}
Student correction: {correction}

Return only JSON like:
{{"correct": true, "score": 0, "feedback": "Explain what was fixed and what is still missing."}}

Material:
{self._context(chunks)}"""
        data = self._json_chat(prompt)
        return {
            "correct": bool(data.get("correct", False)),
            "score": self._score(data.get("score", 0)),
            "feedback": str(data.get("feedback", "Review the source and try again.")),
        }

    def _json_chat(self, prompt: str) -> dict:
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.1},
        )
        content = response.message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("The model did not return valid feedback")
            return json.loads(match.group())

    @staticmethod
    def _context(chunks: list[RetrievedChunk]) -> str:
        return "\n\n".join(
            f"Source: [{chunk.citation}]\n{chunk.text}" for chunk in chunks
        )

    @staticmethod
    def _score(value) -> int:
        try:
            return max(0, min(100, round(float(value))))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _text_list(value) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _jargon_items(value) -> list[dict]:
        if not isinstance(value, list):
            return []

        items = []
        for item in value[:5]:
            if not isinstance(item, dict) or not str(item.get("term", "")).strip():
                continue
            term = str(item["term"]).strip()
            items.append(
                {
                    "term": term,
                    "reason": str(item.get("reason", "This term may be unclear.")).strip(),
                    "simple_version": str(item.get("simple_version", "")).strip(),
                    "question": str(
                        item.get(
                            "question",
                            f"Can you explain {term} without using that term?",
                        )
                    ).strip(),
                }
            )
        return items
