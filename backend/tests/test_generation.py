from app.services.generation import Generator
from app.services.retrieval import RetrievedChunk


def sample_chunks():
    return [
        RetrievedChunk(
            text="Training changes weights when the model's prediction is wrong.",
            source="notes.txt",
            page=1,
            distance=0,
        )
    ]


def jargon_item(term):
    return {
        "term": term,
        "reason": "The audience may not know this term.",
        "simple_version": "A simpler phrase.",
        "question": "Can you explain it more simply?",
    }


def test_jargon_items_removes_duplicate_terms():
    items = Generator._jargon_items(
        [
            jargon_item("representation-learning layers"),
            jargon_item("representation-learning layers"),
            jargon_item("Representation-Learning Layers"),
            jargon_item("representation–learning layers"),
        ]
    )

    assert [item["term"] for item in items] == ["representation-learning layers"]


def test_jargon_items_limits_unique_terms_after_deduplication():
    items = Generator._jargon_items(
        [
            jargon_item("API"),
            jargon_item("api"),
            jargon_item("embedding"),
            jargon_item("vector"),
            jargon_item("token"),
            jargon_item("transformer"),
            jargon_item("extra term"),
        ]
    )

    assert [item["term"] for item in items] == [
        "API",
        "embedding",
        "vector",
        "token",
        "transformer",
    ]


def test_ask_follow_up_uses_the_teaching_conversation():
    generator = Generator.__new__(Generator)
    captured = {}

    def fake_json_chat(prompt):
        captured["prompt"] = prompt
        return {"question": "What happens when the label is wrong?"}

    generator._json_chat = fake_json_chat

    question = generator.ask_follow_up(
        "Supervised learning",
        "A beginner",
        [
            {"role": "student", "content": "What does supervised learning mean?"},
            {"role": "teacher", "content": "It learns from labeled examples."},
        ],
        sample_chunks(),
    )

    assert question == "What happens when the label is wrong?"
    assert "Student: What does supervised learning mean?" in captured["prompt"]
    assert "Teacher: It learns from labeled examples." in captured["prompt"]
    assert "Do not merely ask the teacher to define" in captured["prompt"]
    assert "Stay strictly within Supervised learning" in captured["prompt"]
    assert "Latest teacher answer:\nIt learns from labeled examples." in captured["prompt"]
    assert "what-happens-next or concrete-case question" in captured["prompt"]


def test_ask_follow_up_replaces_a_restatement_question():
    generator = Generator.__new__(Generator)
    responses = iter(
        [
            {"question": "What does it mean to adjust the weights?"},
            {"question": "How does the computer decide which weights to change after a wrong prediction?"},
        ]
    )
    prompts = []

    def fake_json_chat(prompt):
        prompts.append(prompt)
        return next(responses)

    generator._json_chat = fake_json_chat

    question = generator.ask_follow_up(
        "Deep Learning",
        "A beginner",
        [
            {
                "role": "teacher",
                "content": "It compares the answer and gradually changes the weights.",
            }
        ],
        sample_chunks(),
    )

    assert question == (
        "How does the computer decide which weights to change after a wrong prediction?"
    )
    assert len(prompts) == 2
    assert "Replace this shallow restatement question" in prompts[1]
