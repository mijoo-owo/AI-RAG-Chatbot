import streamlit as st

# def initialize_session_state_variables(st):
#     if "uploaded_pdfs" not in st.session_state:
#         st.session_state.uploaded_pdfs = []
#     if "uploaded_urls" not in st.session_state:
#         st.session_state.uploaded_urls = []
#     if "previous_upload_docs_length" not in st.session_state:
#         st.session_state.previous_upload_docs_length = 0
#     if "vectordb" not in st.session_state:
#         st.session_state.vectordb = None
#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []
#     if "url_inputs" not in st.session_state:
#         st.session_state.url_inputs = [""]


def ensure_default_admin_user():
    """Ensure development default user is initialized once in session state."""
    if not st.session_state.get("username"):
        st.session_state["username"] = "admin"
