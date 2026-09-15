import streamlit as st

from api_client import (
    ask_question,
    check_correction,
    continue_teachback,
    create_challenge,
    evaluate_teachback,
    get_progress,
    index_folder,
    start_teachback,
    upload_documents,
)


st.set_page_config(page_title="TeachBack AI", page_icon="🧠", layout="wide")
st.markdown(
    "<style>[data-testid='stAppDeployButton'] {display: none;}</style>",
    unsafe_allow_html=True,
)
st.title("🧠 TeachBack AI")
st.caption("Upload learning material, teach it to the AI, and discover what you really understand.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "teachback_session" not in st.session_state:
    st.session_state.teachback_session = None
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None
if "challenge" not in st.session_state:
    st.session_state.challenge = None
if "correction_result" not in st.session_state:
    st.session_state.correction_result = None


def reset_learning_session():
    st.session_state.messages = []
    st.session_state.teachback_session = None
    st.session_state.evaluation = None
    st.session_state.challenge = None
    st.session_state.correction_result = None


def start_new_teachback():
    st.session_state.teachback_session = None
    st.session_state.evaluation = None
    st.session_state.challenge = None
    st.session_state.correction_result = None


def teaching_transcript(messages):
    labels = {"teacher": "Teacher", "student": "AI student"}
    return "\n\n".join(
        f"{labels[message['role']]}: {message['content']}" for message in messages
    )


def show_list(title, items, empty_text):
    st.markdown(f"**{title}**")
    if items:
        for item in items:
            st.write(f"- {item}")
    else:
        st.caption(empty_text)


with st.sidebar:
    st.header("Learning material")
    uploaded_files = st.file_uploader(
        "Upload PDF or text files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        max_upload_size=20,
    )
    if st.button("Index uploaded files", type="primary", disabled=not uploaded_files):
        with st.spinner("Reading and indexing files..."):
            try:
                result = upload_documents(uploaded_files)
                reset_learning_session()
                st.success(
                    f"Indexed {len(result['files'])} files into {result['chunks']} chunks."
                )
            except Exception:
                st.error("Upload failed. Use text-based PDF or TXT files under 20 MB.")

    st.divider()
    st.caption("Or index a folder already on this computer")
    folder_path = st.text_input("Local folder path", placeholder="/home/user/documents")
    if st.button("Index local folder", disabled=not folder_path.strip()):
        with st.spinner("Reading and indexing folder..."):
            try:
                result = index_folder(folder_path.strip())
                reset_learning_session()
                st.success(
                    f"Indexed {len(result['files'])} files into {result['chunks']} chunks."
                )
            except Exception:
                st.error("Folder failed. Check the path and use PDF or TXT files.")

teach_tab, ask_tab, progress_tab = st.tabs(
    ["🎓 TeachBack session", "💬 Ask the documents", "📈 Progress"]
)

with ask_tab:
    st.subheader("Ask before you teach")
    st.caption("Use document chat when you need to review a concept first.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.write(f"- {source}")

    question = st.chat_input("Ask about the learning material...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the documents..."):
                try:
                    result = ask_question(question)
                    st.markdown(result["answer"])
                    with st.expander("Sources"):
                        for source in result["sources"]:
                            st.write(f"- {source}")
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result["sources"],
                        }
                    )
                except Exception:
                    st.error("The assistant is unavailable. Check that the backend is running.")

with teach_tab:
    st.subheader("Teach the AI student")
    st.write(
        "Choose a topic or let the AI pick one from your documents. Teach it naturally, "
        "answer its questions, then finish when you are ready for feedback."
    )

    session = st.session_state.teachback_session
    if session is None:
        topic_mode = st.radio(
            "Who chooses the topic?",
            ["Let the AI choose", "Choose my own topic"],
            horizontal=True,
        )
        chosen_topic = None
        if topic_mode == "Choose my own topic":
            chosen_topic = st.text_input(
                "Topic you want to teach",
                placeholder="Example: Reinforcement learning",
                max_chars=200,
            )
        audience = st.selectbox(
            "Teach this audience",
            ["A beginner", "A child", "A classmate", "A professor", "An interviewer"],
        )
        if st.button("Start a TeachBack session", type="primary"):
            if chosen_topic is not None and len(chosen_topic.strip()) < 2:
                st.warning("Enter a topic before starting the session.")
            else:
                spinner_text = (
                    "Finding your topic in the documents..."
                    if chosen_topic
                    else "Choosing a topic from your documents..."
                )
                with st.spinner(spinner_text):
                    try:
                        result = start_teachback(
                            audience,
                            chosen_topic.strip() if chosen_topic else None,
                        )
                        st.session_state.teachback_session = {
                            "topic": result["topic"],
                            "audience": audience,
                            "messages": [
                                {"role": "student", "content": result["message"]}
                            ],
                            "sources": result["sources"],
                        }
                        st.session_state.evaluation = None
                        st.rerun()
                    except Exception:
                        st.error(
                            "A session could not be started. Check the topic and uploaded documents."
                        )
    else:
        st.info(f"Your assigned topic: **{session['topic']}**")
        st.caption(f"You are teaching {session['audience'].lower()}.")

        for message in session["messages"]:
            chat_role = "user" if message["role"] == "teacher" else "assistant"
            with st.chat_message(chat_role):
                st.markdown(message["content"])

        teacher_turns = sum(
            message["role"] == "teacher" for message in session["messages"]
        )
        evaluation = st.session_state.evaluation
        if evaluation is None and teacher_turns < 6:
            with st.form(f"teachback_turn_{teacher_turns}"):
                reply = st.text_area(
                    "Your explanation" if teacher_turns == 0 else "Your answer",
                    key=f"teachback_reply_{teacher_turns}",
                    height=140,
                    max_chars=2000,
                    placeholder=(
                        "Explain the assigned topic in your own words..."
                        if teacher_turns == 0
                        else "Answer the AI student's question in your own words..."
                    ),
                )
                sent = st.form_submit_button(
                    "Teach the student" if teacher_turns == 0 else "Send my answer",
                    type="primary",
                )

            if sent:
                minimum_length = 20 if teacher_turns == 0 else 5
                if len(reply.strip()) < minimum_length:
                    st.warning(
                        f"Please write at least {minimum_length} characters before sending."
                    )
                else:
                    conversation = session["messages"] + [
                        {"role": "teacher", "content": reply.strip()}
                    ]
                    with st.spinner("The AI student is thinking of a question..."):
                        try:
                            result = continue_teachback(
                                session["topic"],
                                session["audience"],
                                conversation,
                            )
                            session["messages"] = conversation + [
                                {"role": "student", "content": result["question"]}
                            ]
                            session["sources"] = list(
                                dict.fromkeys(session["sources"] + result["sources"])
                            )
                            st.rerun()
                        except Exception:
                            st.error(
                                "The AI student could not reply. Check the backend and try again."
                            )
        elif evaluation is None:
            st.info("You completed six teaching turns. Finish the session to see your feedback.")

        if evaluation is None:
            action_column, reset_column = st.columns(2)
            with action_column:
                if st.button(
                    "Finish and evaluate",
                    type="primary",
                    width="stretch",
                    disabled=teacher_turns == 0,
                ):
                    with st.spinner("Checking the full conversation against the documents..."):
                        try:
                            st.session_state.evaluation = evaluate_teachback(
                                session["topic"],
                                teaching_transcript(session["messages"]),
                                session["audience"],
                            )
                            st.session_state.challenge = None
                            st.session_state.correction_result = None
                            st.rerun()
                        except Exception:
                            st.error(
                                "Evaluation failed. Make sure the backend and Ollama are running."
                            )
            with reset_column:
                st.button(
                    "Cancel this session",
                    on_click=start_new_teachback,
                    width="stretch",
                )

    evaluation = st.session_state.evaluation
    if evaluation:
        st.divider()
        if evaluation["mastered"]:
            st.success(f"Topic mastered on attempt {evaluation['attempt']}!")
        else:
            st.info(f"TeachBack attempt {evaluation['attempt']} saved. Improve it and teach again.")

        scores = evaluation["scores"]
        score_columns = st.columns(4)
        score_columns[0].metric("Accuracy", f"{scores['accuracy']}%")
        score_columns[1].metric("Clarity", f"{scores['clarity']}%")
        score_columns[2].metric("Completeness", f"{scores['completeness']}%")
        score_columns[3].metric("Mastery", f"{scores['overall']}%")

        st.markdown("### Feedback")
        st.write(evaluation["feedback"])
        good_column, improve_column = st.columns(2)
        with good_column:
            show_list("What you explained well", evaluation["correct_points"], "No strong points were found yet.")
        with improve_column:
            show_list("Important points you missed", evaluation["missing_points"], "You covered the important points.")
            show_list("Misconceptions", evaluation["misconceptions"], "No misconceptions found.")

        jargon = evaluation.get("jargon", [])
        st.markdown("### Jargon detector")
        if jargon:
            st.warning("Some terms may be difficult for your selected audience.")
            for item in jargon:
                with st.expander(item["term"]):
                    st.write(item["reason"])
                    if item["simple_version"]:
                        st.write(f"**Simpler version:** {item['simple_version']}")
                    st.info(item["question"])
        else:
            st.success("Your wording was clear for the selected audience.")

        with st.expander("See an improved explanation"):
            st.write(evaluation["improved_explanation"])
        with st.expander("Evidence used"):
            for source in evaluation["sources"]:
                st.write(f"- {source}")

        action_column, challenge_column = st.columns(2)
        with action_column:
            st.button(
                "Start another session",
                on_click=start_new_teachback,
                width="stretch",
            )
        with challenge_column:
            if st.button("Give me a mistake to correct", width="stretch"):
                with st.spinner("Creating a challenge..."):
                    try:
                        st.session_state.challenge = create_challenge(evaluation["topic"])
                        st.session_state.correction_result = None
                        st.session_state.pop("correction_text", None)
                        st.rerun()
                    except Exception:
                        st.error("The challenge could not be created.")

    challenge = st.session_state.challenge
    if challenge and evaluation:
        st.divider()
        st.markdown("### Find and fix the mistake")
        st.warning(challenge["statement"])
        correction = st.text_area(
            "Your correction",
            key="correction_text",
            placeholder="Explain what is wrong and write the correct idea...",
        )
        if st.button("Check my correction", disabled=len(correction.strip()) < 10):
            with st.spinner("Checking your correction..."):
                try:
                    st.session_state.correction_result = check_correction(
                        evaluation["topic"], challenge["statement"], correction.strip()
                    )
                    st.rerun()
                except Exception:
                    st.error("The correction could not be checked.")

        correction_result = st.session_state.correction_result
        if correction_result:
            if correction_result["correct"]:
                st.success(f"Correct — {correction_result['score']}%")
            else:
                st.warning(f"Not quite yet — {correction_result['score']}%")
            st.write(correction_result["feedback"])

with progress_tab:
    st.subheader("Your learning progress")
    try:
        progress = get_progress()
        summary = progress["summary"]
        summary_columns = st.columns(3)
        summary_columns[0].metric("TeachBack sessions", summary["total_sessions"])
        summary_columns[1].metric("Average score", f"{summary['average_score']}%")
        summary_columns[2].metric("Mastered topics", summary["mastered_topics"])

        if summary["weak_topics"]:
            st.warning("Revise next: " + ", ".join(summary["weak_topics"]))
        elif summary["total_sessions"]:
            st.success("No weak topics in your latest attempts.")

        if progress["sessions"]:
            rows = [
                {
                    "Topic": session["topic"],
                    "Attempt": session["attempt"],
                    "Audience": session["audience"],
                    "Score": f"{session['scores']['overall']}%",
                    "Mastered": "Yes" if session["mastered"] else "Not yet",
                }
                for session in progress["sessions"]
            ]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info("Complete your first TeachBack session to start tracking progress.")
    except Exception:
        st.error("Progress is unavailable. Check that the backend is running.")
