# ---- sqlite3 compatibility fix for Chroma on Linux ----
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except Exception as e:
    pass
# ------------------------------------------------------

import streamlit as st

from utils.auth import UserAuth
from utils.db_orm import init_db


st.set_page_config(
    page_title="Home",
    page_icon="🏠",
)

init_db()

auth = UserAuth()
auth.require_authentication()

st.title("🏠 Homepage")
auth.render_logout_button(key="home_page_logout")
