import streamlit as st

from api_client import (
    ask_question,
    check_correction,
    create_challenge,
    evaluate_teachback,
    generate_topics,
    get_progress,
    index_folder,
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
if "topics" not in st.session_state:
    st.session_state.topics = []
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None
if "challenge" not in st.session_state:
    st.session_state.challenge = None
if "correction_result" not in st.session_state:
    st.session_state.correction_result = None


def reset_learning_session():
    st.session_state.messages = []
    st.session_state.topics = []
    st.session_state.evaluation = None
    st.session_state.challenge = None
    st.session_state.correction_result = None


def start_reteach():
    st.session_state.teachback_explanation = ""
    st.session_state.evaluation = None
    st.session_state.challenge = None
    st.session_state.correction_result = None


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
    st.write("Explain a topic in your own words. The AI will check the explanation against your documents.")

    topic_column, audience_column = st.columns([2, 1])
    with topic_column:
        if st.button("Generate topics from my documents", key="generate_topics"):
            with st.spinner("Finding the main topics..."):
                try:
                    result = generate_topics()
                    st.session_state.topics = result["topics"]
                    st.session_state.evaluation = None
                    st.rerun()
                except Exception:
                    st.error("Topics could not be generated. Upload documents first.")

        if st.session_state.topics:
            selected_topic = st.selectbox(
                "Choose a topic",
                st.session_state.topics + ["Write my own topic"],
            )
            if selected_topic == "Write my own topic":
                topic = st.text_input("Your topic")
            else:
                topic = selected_topic
        else:
            topic = st.text_input("Topic", placeholder="Example: Supervised learning")

    with audience_column:
        audience = st.selectbox(
            "Teach this audience",
            ["A beginner", "A child", "A classmate", "A professor", "An interviewer"],
        )

    explanation = st.text_area(
        "Your explanation",
        key="teachback_explanation",
        height=220,
        placeholder="Teach the topic as if the AI knows nothing about it...",
    )
    if st.button(
        "Evaluate my teaching",
        type="primary",
        disabled=len(topic.strip()) < 2 or len(explanation.strip()) < 20,
    ):
        with st.spinner("Checking your explanation against the documents..."):
            try:
                st.session_state.evaluation = evaluate_teachback(
                    topic.strip(), explanation.strip(), audience
                )
                st.session_state.challenge = None
                st.session_state.correction_result = None
                st.rerun()
            except Exception:
                st.error("Evaluation failed. Make sure the backend and Ollama are running.")

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

        st.markdown("### AI student's follow-up question")
        st.info(evaluation["follow_up_question"])

        with st.expander("See an improved explanation"):
            st.write(evaluation["improved_explanation"])
        with st.expander("Evidence used"):
            for source in evaluation["sources"]:
                st.write(f"- {source}")

        action_column, challenge_column = st.columns(2)
        with action_column:
            st.button("Start a reteach attempt", on_click=start_reteach, use_container_width=True)
        with challenge_column:
            if st.button("Give me a mistake to correct", use_container_width=True):
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
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Complete your first TeachBack session to start tracking progress.")
    except Exception:
        st.error("Progress is unavailable. Check that the backend is running.")
