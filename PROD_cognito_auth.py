import streamlit as st
import os

class CognitoAuth:
    def __init__(self):
        self.cognito_region = os.getenv('COGNITO_REGION', 'us-east-1')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_QOIPBtGBG')
        self.client_id = os.getenv('COGNITO_CLIENT_ID', '39i6589c3te3rli38htqdv2epr')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET', '1bbgdaaf4qrnor5l2j4v4etm6fskbh9d29dh2vhp9h7kphdhqk5c')
        
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
    st.title("Login")
    st.info("Please use the main dashboard URL to access the application.")

    # --- Reset Password Section ---
    if 'reset_password' not in st.session_state:
        st.session_state['reset_password'] = False

    if st.session_state['reset_password']:
        st.subheader("Reset Password")
        email = st.text_input("Enter your email address")
        if st.button("Send Reset Code"):
            import boto3
            client = boto3.client('cognito-idp', region_name=os.getenv('COGNITO_REGION', 'us-east-1'))
            try:
                client.forgot_password(
                    ClientId=os.getenv('COGNITO_CLIENT_ID', ''),
                    Username=email
                )
                st.success("A reset code has been sent to your email. Please check your inbox.")
                st.session_state['reset_email'] = email
                st.session_state['reset_code_sent'] = True
            except Exception as e:
                st.error(f"Error sending reset code: {e}")

        if st.session_state.get('reset_code_sent', False):
            code = st.text_input("Enter the code you received in your email")
            new_password = st.text_input("Enter your new password", type="password")
            if st.button("Confirm Reset"):
                try:
                    client = boto3.client('cognito-idp', region_name=os.getenv('COGNITO_REGION', 'us-east-1'))
                    client.confirm_forgot_password(
                        ClientId=os.getenv('COGNITO_CLIENT_ID', ''),
                        Username=st.session_state['reset_email'],
                        ConfirmationCode=code,
                        Password=new_password
                    )
                    st.success("Your password has been reset. You can now log in with your new password.")
                    st.session_state['reset_password'] = False
                    st.session_state['reset_code_sent'] = False
                except Exception as e:
                    st.error(f"Error resetting password: {e}")
        if st.button("Back to Login"):
            st.session_state['reset_password'] = False
            st.session_state['reset_code_sent'] = False
    else:
        # ...existing login form or redirect logic...
        st.markdown("""
        <script>
            window.location.href = 'https://haugland.cr-ai-dashboard.com/';
        </script>
        """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 2em;'></div>", unsafe_allow_html=True)
        if st.button("Reset Password"):
            st.session_state['reset_password'] = True