import os

import bcrypt
import streamlit as st
import yaml
from yaml.loader import SafeLoader


DEMO_USERS = {
    "admin": {
        "password": "admin",
        "name": "Administrator",
        "email": "admin@example.com",
    },
    "user": {
        "password": "user",
        "name": "Normal User",
        "email": "user@example.com",
    },
}


class UserAuth:
    def __init__(self, config_path="config/users.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """Load user configuration from YAML file"""
        os.makedirs("config", exist_ok=True)

        if not os.path.exists(self.config_path):
            default_config = {
                'credentials': {
                    'usernames': {}
                },
                'cookie': {
                    'expiry_days': 30,
                    'key': 'chatbot_auth_key',
                    'name': 'chatbot_auth_cookie'
                },
                'preauthorized': {
                    'emails': []
                }
            }

            with open(self.config_path, 'w') as file:
                yaml.dump(default_config, file, default_flow_style=False)

        with open(self.config_path) as file:
            config = yaml.load(file, Loader=SafeLoader) or {}

        config.setdefault('credentials', {}).setdefault('usernames', {})
        config.setdefault('cookie', {
            'expiry_days': 30,
            'key': 'chatbot_auth_key',
            'name': 'chatbot_auth_cookie'
        })
        config.setdefault('preauthorized', {'emails': []})

        changed = False
        for username, user_data in DEMO_USERS.items():
            if username not in config['credentials']['usernames']:
                config['credentials']['usernames'][username] = {
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'password': self._hash_password(user_data['password'])
                }
                changed = True

        if changed:
            with open(self.config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

        return config

    def _hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_credentials(self, username, password):
        """Verify username and password against hardcoded demo users."""
        demo_user = DEMO_USERS.get(username)
        return bool(demo_user and password == demo_user['password'])

    def initialize_auth_state(self):
        """Ensure required auth keys exist in session state."""
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = False
        if 'username' not in st.session_state:
            st.session_state.username = None

    def login(self):
        """Display login form and handle authentication."""
        self.initialize_auth_state()
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            if submitted:
                if self._verify_credentials(username, password):
                    st.session_state.authentication_status = True
                    st.session_state.username = username
                    st.success(f"Welcome *{username}*")
                    st.rerun()
                st.error("Username or password is incorrect")

        return st.session_state.get("username"), bool(st.session_state.get("authentication_status"))

    def render_login_form(self, title="🔐 Log in to RAG Chatbot App"):
        """Render centered login form."""
        st.title(title)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            self.login()

    def logout(self):
        """Handle user logout."""
        st.session_state.authentication_status = False
        st.session_state.username = None
        st.rerun()

    def render_logout_button(self, label="Log out", key="logout_button"):
        """Render a logout button in the current container."""
        if st.button(label, key=key):
            self.logout()

    def register_new_user(self):
        """Registration is disabled in demo mode."""
        st.info("Registration is disabled for demo. Use hardcoded accounts: admin/admin or user/user.")

    def require_authentication(self, title="🔐 Log in to RAG Chatbot App"):
        """Show login form and stop page execution if user is not authenticated."""
        self.initialize_auth_state()
        if not st.session_state.get("authentication_status"):
            self.render_login_form(title=title)
            st.stop()

    def get_user_info(self, username):
        """Get user information"""
        if username in self.config['credentials']['usernames']:
            user_data = self.config['credentials']['usernames'][username]
            return {
                'username': username,
                'name': user_data.get('name', username),
                'email': user_data.get('email', '')
            }
        return None
    