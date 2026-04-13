# ---- sqlite3 compatibility fix for Chroma on Linux ----
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except Exception as e:
    pass
# ------------------------------------------------------

import streamlit as st

from utils.chat_app import ChatApp
from utils.db_orm import init_db

st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
)

init_db()

chat_app = ChatApp()
chat_app.run()
