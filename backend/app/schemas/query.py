from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


class UploadResponse(BaseModel):
    message: str
    files: list[str]
    chunks: int


class FolderRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)


Audience = Literal[
    "A child",
    "A beginner",
    "A classmate",
    "A professor",
    "An interviewer",
]


class TopicRequest(BaseModel):
    count: int = Field(default=5, ge=3, le=8)


class TopicResponse(BaseModel):
    topics: list[str]
    sources: list[str]


class TeachBackRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    explanation: str = Field(min_length=20, max_length=6000)
    audience: Audience = "A beginner"


class TeachBackScores(BaseModel):
    accuracy: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


class JargonItem(BaseModel):
    term: str
    reason: str
    simple_version: str
    question: str


class TeachBackResponse(BaseModel):
    session_id: str
    created_at: str
    topic: str
    audience: Audience
    attempt: int
    scores: TeachBackScores
    correct_points: list[str]
    missing_points: list[str]
    misconceptions: list[str]
    jargon: list[JargonItem] = Field(default_factory=list)
    feedback: str
    follow_up_question: str
    improved_explanation: str
    mastered: bool
    sources: list[str]


class ChallengeRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


class ChallengeResponse(BaseModel):
    statement: str
    sources: list[str]


class CorrectionRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    statement: str = Field(min_length=5, max_length=1000)
    correction: str = Field(min_length=10, max_length=3000)


class CorrectionResponse(BaseModel):
    correct: bool
    score: int = Field(ge=0, le=100)
    feedback: str
    sources: list[str]


class ProgressSummary(BaseModel):
    total_sessions: int
    mastered_topics: int
    average_score: int
    weak_topics: list[str]


class ProgressResponse(BaseModel):
    summary: ProgressSummary
    sessions: list[TeachBackResponse]
