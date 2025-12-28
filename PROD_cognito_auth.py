import streamlit as st
import os
import boto3
import hmac
import hashlib
import base64

class CognitoAuth:
    def __init__(self):
        self.cognito_region = os.getenv('COGNITO_REGION', 'us-east-1')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_QOIPBtGBG')
        self.client_id = os.getenv('COGNITO_CLIENT_ID', '39i6589c3te3rli38htqdv2epr')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET', '1bbgdaaf4qrnor5l2j4v4etm6fskbh9d29dh2vhp9h7kphdhqk5c')

    def get_secret_hash(self, username):
        """Calculate SECRET_HASH for Cognito authentication"""
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def authenticate(self, username, password):
        """Authenticate user with Cognito"""
        try:
            client = boto3.client('cognito-idp', region_name=self.cognito_region)
            secret_hash = self.get_secret_hash(username)
            
            response = client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash
                }
            )
            return True, response
        except Exception as e:
            return False, str(e)

    def verify_token(self, token):
        """Verify the access token - simplified version without JWT parsing"""
        try:
            # Basic token validation - check if it looks like a valid JWT token
            if token and len(token) > 50 and token.count('.') >= 2:
                # Additional basic checks for JWT format
                parts = token.split('.')
                if len(parts) == 3:  # JWT has 3 parts: header.payload.signature
                    return True
            return False
        except Exception as e:
            # Don't show error to user, just return False for failed validation
            return False

    def get_user_attributes(self, token):
        """Get user attributes - simplified version"""
        try:
            return {
                'username': 'authenticated_user',
                'email': 'user@haugland.com'
            }
        except Exception:
            return {}

def main():
    """Main login page function"""
    
    # Initialize session state for reset password
    if 'reset_password' not in st.session_state:
        st.session_state['reset_password'] = False
    
    # If in reset password mode
    if st.session_state['reset_password']:
        st.title("Reset Password")
        
        email = st.text_input("Enter your email address")
        
        if st.button("Send Reset Code", use_container_width=True):
            if email:
                try:
                    client = boto3.client('cognito-idp', region_name=os.getenv('COGNITO_REGION', 'us-east-1'))
                    client.forgot_password(
                        ClientId=os.getenv('COGNITO_CLIENT_ID', '39i6589c3te3rli38htqdv2epr'),
                        Username=email
                    )
                    st.success("A reset code has been sent to your email. Please check your inbox.")
                    st.session_state['reset_email'] = email
                    st.session_state['reset_code_sent'] = True
                except Exception as e:
                    st.error(f"Error sending reset code: {str(e)}")
            else:
                st.warning("Please enter your email address")

        if st.session_state.get('reset_code_sent', False):
            code = st.text_input("Enter the code you received in your email")
            new_password = st.text_input("Enter your new password", type="password")
            
            if st.button("Confirm Reset", use_container_width=True):
                if code and new_password:
                    try:
                        client = boto3.client('cognito-idp', region_name=os.getenv('COGNITO_REGION', 'us-east-1'))
                        client.confirm_forgot_password(
                            ClientId=os.getenv('COGNITO_CLIENT_ID', '39i6589c3te3rli38htqdv2epr'),
                            Username=st.session_state['reset_email'],
                            ConfirmationCode=code,
                            Password=new_password
                        )
                        st.success("Your password has been reset successfully! Redirecting to login...")
                        st.session_state['reset_password'] = False
                        st.session_state['reset_code_sent'] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error resetting password: {str(e)}")
                else:
                    st.warning("Please enter both the code and new password")
        
        st.markdown("<div style='margin-top: 1em;'></div>", unsafe_allow_html=True)
        if st.button("Back to Login"):
            st.session_state['reset_password'] = False
            st.session_state['reset_code_sent'] = False
            st.rerun()
    
    else:
        # Main login page
        # Center content and styling
        st.markdown("""
            <style>
            .main {
                max-width: 400px;
                margin: 0 auto;
                padding-top: 2rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Display CR AI logo
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("static/cr_ai_logo.png", use_container_width=True)
        
        st.markdown("<div style='text-align: center; margin-bottom: 2em;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #4A5568;'>Login</h2>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Username field
        username = st.text_input("Username", placeholder="Enter your username", key="login_username")
        
        # Password field
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        
        # Login button
        if st.button("Login", use_container_width=True, type="primary"):
            if username and password:
                auth = CognitoAuth()
                success, result = auth.authenticate(username, password)
                if success:
                    st.success("Login successful! Redirecting to dashboard...")
                    st.markdown("""
                    <script>
                        window.location.href = 'https://haugland.cr-ai-dashboard.com/';
                    </script>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Authentication failed: {result}")
            else:
                st.warning("Please enter both username and password")
        
        # Reset password button
        st.markdown("<div style='margin-top: 1em; text-align: center;'>", unsafe_allow_html=True)
        if st.button("Reset Password"):
            st.session_state['reset_password'] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()