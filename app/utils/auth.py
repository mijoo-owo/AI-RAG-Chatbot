import os

import bcrypt
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


class UserAuth:
    def __init__(self, config_path="config/users.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.authenticator = self._create_authenticator()

    def _load_config(self):
        """Load user configuration from YAML file"""
        os.makedirs("config", exist_ok=True)

        if not os.path.exists(self.config_path):
            # Tạo config mặc định với admin user
            default_config = {
                'credentials': {
                    'usernames': {
                        'admin': {
                            'email': 'admin@example.com',
                            'name': 'Administrator',
                            'password': self._hash_password('admin')
                        }
                    }
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
            return yaml.load(file, Loader=SafeLoader)

    def _hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _create_authenticator(self):
        """Create streamlit-authenticator instance"""
        return stauth.Authenticate(
            self.config['credentials'],
            self.config['cookie']['name'],
            self.config['cookie']['key'],
            self.config['cookie']['expiry_days'],
            self.config['preauthorized']
        )

    def _verify_credentials(self, username, password):
        """Verify username and password"""
        if username in self.config['credentials']['usernames']:
            stored_password = self.config['credentials']['usernames'][username]['password']
            return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
        return False

    def login(self):
        """Display login form and handle authentication"""
        name, authentication_status, username = self.authenticator.login('Login', 'main')

        if authentication_status == False:
            st.error('Username/password is incorrect')
            return None, False
        elif authentication_status == None:
            st.warning('Please enter your username and password')
            return None, False
        elif authentication_status:
            return username, True

        return None, False

    def logout(self):
        """Handle user logout"""
        try:
            self.authenticator.logout('Log out', 'sidebar')
            # Clear session state sau khi logout
            if st.session_state.get('authentication_status') is None:
                st.session_state.authentication_status = None
                st.session_state.username = None
                st.rerun()
        except KeyError:
            # Cookie không tồn tại, force logout bằng cách clear session
            st.session_state.authentication_status = None
            st.session_state.username = None
            st.success("Logged out successfully")
            st.rerun()
        except Exception as e:
            # Các lỗi khác, vẫn force logout
            st.warning(f"Logout warning: {e}")
            st.session_state.authentication_status = None
            st.session_state.username = None
            st.rerun()

    def register_new_user(self):
        """Register new user (optional - for admin)"""
        try:
            if self.authenticator.register_user('Register user', preauthorization=False):
                with open(self.config_path, 'w') as file:
                    yaml.dump(self.config, file, default_flow_style=False)
                st.success('User registered successfully')
        except Exception as e:
            st.error(f'Registration failed: {e}')

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