import streamlit as st

from api_client import ask_question, index_folder, upload_documents


st.set_page_config(page_title="Project Guide Assistant", page_icon="📚")
st.title("📚 Project Guide Assistant")
st.caption("Upload a document folder, then ask questions about its contents")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Your documents")
    uploaded_files = st.file_uploader(
        "Upload PDF or text files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        max_upload_size=20,
        help="Open a folder and select all the files you want to use.",
    )
    if st.button("Index uploaded files", type="primary", disabled=not uploaded_files):
        with st.spinner("Reading and indexing files..."):
            try:
                upload_result = upload_documents(uploaded_files)
                st.session_state.messages = []
                st.success(
                    f"Indexed {len(upload_result['files'])} files into "
                    f"{upload_result['chunks']} chunks."
                )
            except Exception:
                st.error("Upload failed. Use text-based PDF or TXT files under 20 MB.")

    st.divider()
    st.caption("Or index a folder already on this computer")
    folder_path = st.text_input("Local folder path", placeholder="/home/user/documents")
    if st.button("Index local folder", disabled=not folder_path.strip()):
        with st.spinner("Reading and indexing folder..."):
            try:
                folder_result = index_folder(folder_path.strip())
                st.session_state.messages = []
                st.success(
                    f"Indexed {len(folder_result['files'])} files into "
                    f"{folder_result['chunks']} chunks."
                )
            except Exception:
                st.error("Folder failed. Check the path and use PDF or TXT files.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.write(f"- {source}")

question = st.chat_input("Ask about the documents...")
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
