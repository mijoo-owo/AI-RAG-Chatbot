import os
# import shutil

import streamlit as st

from .auth import UserAuth
from .chatbot import (
    chat_user_prompt,
    load_chat_history_from_db,
)
from .prepare_vectordb import (
    cleanup_user_data,
    get_user_dirs,
    get_vectorstore_user,
    has_new_files_user,
)
from .save_docs import get_user_documents, save_docs_to_vectordb_user
from .session_state import ensure_default_admin_user
# from .save_urls import save_url_to_vectordb_user
# from .session_state import initialize_session_state_variables


class ChatApp:
    def __init__(self):
        # st.set_page_config(page_title="Chatbot")
        # st.title("Chatbot")

        # Initialize authentication
        self.auth = UserAuth()

        # # Check if user is logged in
        # if 'authentication_status' not in st.session_state:
        #     st.session_state.authentication_status = None
        # if 'username' not in st.session_state:
        #     st.session_state.username = None
        
        st.session_state["authentication_status"] = True
        ensure_default_admin_user()

    # def _reset_session_dirs_and_state(self):
    #     """Clean session state and temporary directories."""
    #     for folder in ["docs"]:
    #         if os.path.exists(folder):
    #             shutil.rmtree(folder)
    #     os.makedirs("docs", exist_ok=True)
    #     # Keep other state variables that should not be reset
    #     st.success("Documents and selected session states have been reset.")

    def render_login_page(self):
        """Render login page"""
        st.title("🔐 Log in to Chatbot")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Tạo form đăng nhập tùy chỉnh
            with st.form("login_form"):
                st.subheader("Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                # Nút submit với tên tùy chỉnh
                submitted = st.form_submit_button("Log in")  # Thay đổi tên nút ở đây
                if submitted:
                    # Kiểm tra thông tin đăng nhập
                    if self.auth._verify_credentials(username, password):
                        st.session_state.authentication_status = True
                        st.session_state.username = username
                        st.success(f'Welcome *{username}*')
                        st.rerun()
                    else:
                        st.error('Username or password is incorrect')

        # Optional: Registration section for admin
        if st.checkbox("Admin: Register new user"):
            self.auth.register_new_user()

    def render_main_app(self):
        """Render main application for authenticated users"""
        username = st.session_state["username"]

        # Kiểm tra và hiển thị thông báo upload thành công
        upload_success_key = f'upload_success_{username}'
        if upload_success_key in st.session_state:
            success_data = st.session_state[upload_success_key]
            for message in success_data['messages']:
                st.success(message)
            st.success(f"Successfully processed {success_data['count']} documents!")
            # Xóa thông báo khỏi session state
            del st.session_state[upload_success_key]

        # Kiểm tra thông báo từ việc xử lý vectorstore
        vectorstore_success_key = f'vectorstore_success_{username}'
        if vectorstore_success_key in st.session_state:
            st.success(st.session_state[vectorstore_success_key])
            del st.session_state[vectorstore_success_key]

        # Header with user info and logout
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"🤖 Chatbot")
            st.write(f"Welcome back, **{username}**!")

        # with col2:
        #     self.auth.logout()

        # Ensure user directories exist
        user_dirs = get_user_dirs(username)
        for dir_path in user_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        # Initialize session state for user
        if f'uploaded_pdfs_{username}' not in st.session_state:
            self.initialize_user_session_state(username)

        # Sidebar: Upload & URL options
        with st.sidebar:
            st.subheader(f"📁 {username}'s Documents")

            # Show current document count
            user_docs = get_user_documents(username)
            suffix = '' if len(user_docs) == 1 else 's'
            st.info(f"📊 You have {len(user_docs)} document{suffix}")

            # Document deletion
            if user_docs:
                st.subheader("🗑️ Manage Documents")
                doc_to_delete = st.selectbox(
                    "Select document to delete:",
                    options=[""] + user_docs,
                    key=f"delete_doc_{username}"
                )

                if doc_to_delete:
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("Delete Document", use_container_width=True, key=f"delete_btn_{username}"):
                            st.session_state[f"confirm_delete_{username}"] = doc_to_delete

                    with col2:
                        if f"confirm_delete_{username}" in st.session_state and st.session_state[f"confirm_delete_{username}"] == doc_to_delete:
                            if st.button("⚠️ Confirm", use_container_width=True, key=f"confirm_btn_{username}"):
                                from utils.save_docs import \
                                    delete_user_document
                                if delete_user_document(username, doc_to_delete):
                                    # Xóa vectorstore để force rebuild
                                    user_vectordb_key = f'vectordb_{username}'
                                    if user_vectordb_key in st.session_state:
                                        del st.session_state[user_vectordb_key]

                                    # Xóa confirm state
                                    if f"confirm_delete_{username}" in st.session_state:
                                        del st.session_state[f"confirm_delete_{username}"]

                                    st.rerun()

            uploaded_docs = st.file_uploader(
                "Upload (.pdf, .txt, .doc, .docx)",
                type=["pdf", "txt", "doc", "docx", "xls", "xlsx"],
                accept_multiple_files=True
            )

            if uploaded_docs:
                new_files = save_docs_to_vectordb_user(username, uploaded_docs, user_docs)
                if new_files:
                    st.success(f"📁 Saved: {', '.join(new_files)}")

            # st.subheader("🌐 Website URLs")
            # crawl_links = st.checkbox("Crawl all links on the same domain", value=False)
            # page_limit = 50
            # if crawl_links:
            #     page_limit = st.number_input(
            #         "Maximum pages to crawl", min_value=1, max_value=1000, value=50
            #     )

            # self._handle_url_inputs_user(username)

            # if st.button("🌐 Process URLs", use_container_width=True):
            #     for url in st.session_state.get(f'url_inputs_{username}', [""]):
            #         url = url.strip()
            #         if url:
            #             save_url_to_vectordb_user(
            #                 username, url, user_docs,
            #                 crawl_links=crawl_links,
            #                 page_limit=page_limit
            #             )
            #     st.success("✅ All valid URLs processed.")

            # # User-specific reset with confirmation stored in session
            # reset_flag = f"confirm_reset_{username}"
            # if st.button("🗑️ Reset my data", use_container_width=True):
            #     st.session_state[reset_flag] = True

            # if st.session_state.get(reset_flag, False):
            #     if st.button("⚠️ Confirm reset", use_container_width=True):
            #         # Drop cached vectordb handle so files are not locked on Windows
            #         user_vectordb_key = f"vectordb_{username}"
            #         st.session_state.pop(user_vectordb_key, None)

            #         self.reset_user_data(username)
            #         st.session_state.pop(reset_flag, None)

        # Vector store and chat for user
        all_user_docs = get_user_documents(username)
        user_vectordb_key = f'vectordb_{username}'

        if (user_vectordb_key not in st.session_state or
                has_new_files_user(username, all_user_docs)):

            with st.spinner(f"Updating {username}'s knowledge base..."):
                try:
                    st.session_state[user_vectordb_key] = get_vectorstore_user(username, all_user_docs)
                    st.success("✅ Knowledge base updated.")
                except Exception as e:
                    st.error(f"Error updating vector store: {e}")

        # Chat interface
        if user_vectordb_key in st.session_state:
            chat_history_key = f'chat_history_{username}'
            
            # # Load chat history from database if not already in session
            loaded_chat_history = load_chat_history_from_db(username)
            # if chat_history_key not in st.session_state:
            st.session_state[chat_history_key] = loaded_chat_history

            st.session_state[chat_history_key] = chat_user_prompt(
                st.session_state[chat_history_key],
                st.session_state[user_vectordb_key],
                username=username
            )
        else:
            st.info("Upload documents or enter URLs to begin chatting.")

    def initialize_user_session_state(self, username):
        """Initialize session state variables for specific user"""
        st.session_state[f'uploaded_pdfs_{username}'] = []
        st.session_state[f'uploaded_urls_{username}'] = []
        st.session_state[f'url_inputs_{username}'] = [""]
        st.session_state[f'chat_history_{username}'] = []

    def reset_user_data(self, username):
        """Reset all data for specific user"""
        cleanup_user_data(username)

        # Clear user-specific session state
        keys_to_remove = [key for key in st.session_state.keys() if key.endswith(f'_{username}')]
        for key in keys_to_remove:
            del st.session_state[key]

        st.success(f"🗑️ All data reset for user: {username}")
        st.rerun()

    def run(self):
        """Main application runner"""
        if st.session_state.get("authentication_status", False):
            self.render_main_app()
        else:
            self.render_login_page()
