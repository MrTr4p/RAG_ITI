import streamlit as st

from api_client import ask_question


st.set_page_config(page_title="Project Guide Assistant", page_icon="📚")
st.title("📚 Project Guide Assistant")
st.caption("Ask questions about the graduation project requirements")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.write(f"- {source}")

question = st.chat_input("Ask about the project...")
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

