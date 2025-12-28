import streamlit as st
import os
import boto3
import hmac
import hashlib
import base64

class CognitoAuth:
    def __init__(self):
        self.cognito_region = os.getenv('COGNITO_REGION', 'us-east-1')
        # Define all user pools with their app client credentials
        self.user_pools = [
            {
                'pool_id': 'us-east-1_QOIPBtGBG',
                'client_id': '39i6589c3te3rli38htqdv2epr',
                'client_secret': 'k00betnr4fl4v8lpsolpfhadi0iigjbsdgskbbhjcfdso3dphj6',
                'name': 'cr-score-users'
            },
            {
                'pool_id': 'us-east-1_mjY6yx0YY',
                'client_id': '20mrscnb38mloeupht8rjnnshm',
                'client_secret': '1jkmfc48dda36c9qeor04opsuvm7gr483c747ocg7e0onnm7k4ga',
                'name': 'dev-dashboard-users'
            }
            # Note: CRAI_insurance_app pool (us-east-1_fX3dT8fMy) doesn't support USER_PASSWORD_AUTH
            # so it's excluded for now
        ]

    def get_secret_hash(self, username, client_id, client_secret):
        """Calculate SECRET_HASH for Cognito authentication"""
        message = username + client_id
        dig = hmac.new(
            client_secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def authenticate(self, username, password):
        """Authenticate user with Cognito - try all user pools"""
        client = boto3.client('cognito-idp', region_name=self.cognito_region)
        
        # Try each user pool
        for pool in self.user_pools:
            # Skip pools without client credentials configured
            if not pool['client_id'] or not pool['client_secret']:
                continue
                
            try:
                secret_hash = self.get_secret_hash(username, pool['client_id'], pool['client_secret'])
                
                response = client.initiate_auth(
                    ClientId=pool['client_id'],
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME': username,
                        'PASSWORD': password,
                        'SECRET_HASH': secret_hash
                    }
                )
                # If successful, return immediately
                return True, {'response': response, 'pool': pool['name']}
            except client.exceptions.NotAuthorizedException:
                # Wrong credentials for this pool, try next one
                continue
            except client.exceptions.UserNotFoundException:
                # User doesn't exist in this pool, try next one
                continue
            except Exception as e:
                # Other errors, try next pool
                continue
        
        # If we get here, authentication failed in all pools
        return False, "Invalid username or password"

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
        
        st.markdown("""
        <div style='background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 1rem; margin-bottom: 1rem;'>
            <strong>Password Requirements:</strong><br>
            • Minimum 8 characters<br>
            • At least one uppercase letter (A-Z)<br>
            • At least one lowercase letter (a-z)<br>
            • At least one number (0-9)
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username")
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
        confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
        
        if st.button("Reset Password", use_container_width=True):
            if username and new_password and confirm_password:
                # Validate passwords match
                if new_password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                # Validate password requirements
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif not any(c.isupper() for c in new_password):
                    st.error("Password must contain at least one uppercase letter.")
                elif not any(c.islower() for c in new_password):
                    st.error("Password must contain at least one lowercase letter.")
                elif not any(c.isdigit() for c in new_password):
                    st.error("Password must contain at least one number.")
                else:
                    try:
                        client = boto3.client('cognito-idp', region_name=os.getenv('COGNITO_REGION', 'us-east-1'))
                        
                        # Try to set password for user in each pool
                        password_reset_success = False
                        auth = CognitoAuth()
                        
                        for pool in auth.user_pools:
                            try:
                                # Admin set user password (requires admin privileges)
                                client.admin_set_user_password(
                                    UserPoolId=pool['pool_id'],
                                    Username=username,
                                    Password=new_password,
                                    Permanent=True
                                )
                                password_reset_success = True
                                st.success(f"Password reset successfully for user '{username}'! You can now log in with your new password.")
                                st.session_state['reset_password'] = False
                                st.session_state['reset_code_sent'] = False
                                st.rerun()
                                break
                            except client.exceptions.UserNotFoundException:
                                # User not in this pool, try next one
                                continue
                            except Exception as e:
                                # Try next pool
                                continue
                        
                        if not password_reset_success:
                            st.error(f"User '{username}' not found in any user pool. Please verify the username and try again.")
                            
                    except Exception as e:
                        st.error(f"Error resetting password: {str(e)}")
            else:
                st.warning("Please fill in all fields")
        
        st.markdown("<div style='margin-top: 1em;'></div>", unsafe_allow_html=True)
        if st.button("Back to Login"):
            st.session_state['reset_password'] = False
            st.session_state['reset_code_sent'] = False
            st.rerun()
    
    else:
        # Main login page
        # Styling without max-width constraint
        st.markdown("""
            <style>
            .main {
                padding-top: 2rem;
            }
            /* Remove scrollbars from internal containers */
            [data-testid="stVerticalBlock"] {
                overflow: visible !important;
            }
            section[data-testid="stSidebar"] {
                display: none;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Display CR AI logo
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("static/cr_ai_logo.png", width=150)
        
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
                    # Extract access token from authentication result
                    access_token = result['response']['AuthenticationResult']['AccessToken']
                    
                    # Build redirect URL with access token for dashboard authentication
                    redirect_url = f"https://haugland.cr-ai-dashboard.com/?access_token={access_token}"
                    
                    st.success("Login successful! Redirecting to dashboard...")
                    # Use meta refresh for redirect with access token
                    st.markdown(f"""
                    <meta http-equiv="refresh" content="1;url={redirect_url}" />
                    """, unsafe_allow_html=True)
                    # Also try JavaScript as backup
                    st.markdown(f"""
                    <script>
                        setTimeout(function() {{
                            window.top.location.href = '{redirect_url}';
                        }}, 1000);
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