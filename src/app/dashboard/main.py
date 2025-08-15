import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api"

def main():
    st.set_page_config(
        page_title="User Invitation System",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 User Invitation System")
    st.markdown("---")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Invitation Page", "View Users", "Verify User"]
    )
    
    if page == "Invitation Page":
        invitation_page()
    elif page == "View Users":
        view_users_page()
    elif page == "Verify User":
        verify_user_page()

def invitation_page():
    st.header("📤 Invitation Page")
    st.write("Upload a CSV file with user details to send invitations.")
    
    # Initialize session state for storing CSV results
    if 'csv_results' not in st.session_state:
        st.session_state.csv_results = None
    if 'uploaded_file_name' not in st.session_state:
        st.session_state.uploaded_file_name = None
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with columns: email, name, college, branch, year"
    )
    
    if uploaded_file is not None:
        # Show CSV preview
        st.write("**CSV Preview:**")
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        
        # Process button
        if st.button("🔄 Process CSV"):
            process_csv(uploaded_file)
    
    # Display results if they exist in session state
    if st.session_state.csv_results and st.session_state.csv_results['newly_added'] > 0:
        st.subheader("Newly Added Users")
        
        # Create DataFrame for display
        users_data = []
        for user in st.session_state.csv_results['newly_added_users']:
            users_data.append({
                'Email': user['email'],
                'Name': user['name'],
                'College': user['college'],
                'Branch': user['branch'],
                'Year': user['year'],
                'Token': user['token']
            })
        
        users_df = pd.DataFrame(users_data)
        st.dataframe(users_df)
        
        # Send emails button - DIRECT CALL
        if st.button("📧 Send Verification Emails", key="send_emails_bulk"):
            st.info(f"🔄 Sending verification emails to {len(st.session_state.csv_results['newly_added_users'])} users...")
            
            # Loop through each newly added user and send email individually
            for user in st.session_state.csv_results['newly_added_users']:
                st.toast(f"📧 Sending email to {user['email']}...")
                send_verification_email_single(user['id'])
            
            st.success(f"✅ Finished sending verification emails to all {len(st.session_state.csv_results['newly_added_users'])} users!")

def process_csv(file):
    """Process the uploaded CSV file"""
    try:
        # Reset file pointer
        file.seek(0)
        
        # Send to API
        files = {"file": file}
        response = requests.post(f"{API_BASE_URL}/upload-csv", files=files)
        
        if response.status_code == 200:
            result = response.json()
            
            # Store results in session state
            st.session_state.csv_results = result
            st.session_state.uploaded_file_name = file.name
            
            st.success(f"✅ CSV processed successfully!")
            st.info(f"Total processed: {result['total_processed']}")
            st.info(f"Newly added: {result['newly_added']}")
            st.info(f"Skipped: {result['skipped']}")
            
            # Rerun to show the results section
            st.rerun()
        else:
            st.error(f"Error processing CSV: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def send_emails(user_ids):
    """Send verification emails to users"""
    try:
        st.info(f"📡 Making API call to send emails to {len(user_ids)} users...")
        
        response = requests.post(
            f"{API_BASE_URL}/send-emails",
            json=user_ids
        )
        
        st.info(f"📡 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                st.success(f"✅ {result['message']}")
                # Clear the session state after successful send
                if 'newly_added_users' in st.session_state:
                    del st.session_state.newly_added_users
            else:
                st.warning(f"⚠️ {result['message']}")
        else:
            st.error(f"Error sending emails: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Error sending emails: {str(e)}")
        st.error(f"Exception type: {type(e).__name__}")

def view_users_page():
    st.header("👥 View Users")
    st.write("View all users and manage their verification status.")
    
    # Initialize session state for delete confirmation
    if 'show_delete_confirmation' not in st.session_state:
        st.session_state.show_delete_confirmation = False
    
    if st.button("🔄 Refresh Page"):
        st.rerun()
    
    # Load users automatically when page loads
    load_users()
    
    # Delete all users button and confirmation
    if not st.session_state.show_delete_confirmation:
        if st.button("🗑️ Delete All Users", type="primary"):
            st.session_state.show_delete_confirmation = True
            st.rerun()
    else:
        st.warning("⚠️ Are you sure you want to delete ALL users? This cannot be undone!")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ Yes, Delete All Users", type="primary"):
                delete_all_users()
                st.session_state.show_delete_confirmation = False
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_delete_confirmation = False
                st.rerun()

def load_users():
    """Load and display all users"""
    try:
        response = requests.get(f"{API_BASE_URL}/users")
        
        if response.status_code == 200:
            users = response.json()
            
            if not users:
                st.info("No users found in the database.")
                return
            
            # Create DataFrame for display (without ID column)
            users_data = []
            for user in users:
                users_data.append({
                    'Email': user['email'],
                    'Name': user['name'],
                    'College': user['college'],
                    'Branch': user['branch'],
                    'Year': user['year'],
                    'Token': mask_token(user['token']),
                    'Verified': '✅' if user['is_verified'] else '❌',
                    'Created': format_date(user['created_at'])
                })
            
            users_df = pd.DataFrame(users_data)
            
            # Display users table
            st.subheader("All Users")
            st.dataframe(users_df, use_container_width=True)
            
            # Action buttons for each user
            st.subheader("Individual User Actions")
            
            for user in users:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{user['name']}** ({user['email']})")
                
                with col2:
                    status = "✅ Verified" if user['is_verified'] else "❌ Not Verified"
                    st.write(f"{status}")

                with col3:
                    if not user['is_verified']:
                        if st.button(f"🔄 Refresh Token", key=f"refresh_{user['id']}"):
                            refresh_user_token(user['id'])
                
                with col4:
                    if not user['is_verified']:
                        if st.button(f"📧 Resend Email", key=f"resend_{user['id']}"):
                            send_verification_email_single(user['id'])
                
                with col5:
                    if st.button(f"🗑️ Delete", key=f"delete_{user['id']}", type="secondary"):
                        delete_single_user(user['id'])
                
                st.markdown("---")
        else:
            st.error(f"Error loading users: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def delete_all_users():
    """Delete all users from the database"""
    try:
        response = requests.delete(f"{API_BASE_URL}/all")
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Successfully deleted all users!")
        else:
            st.error(f"Error deleting all users: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Error deleting all users: {str(e)}")

def refresh_user_token(user_id):
    """Refresh token for a specific user"""
    try:
        response = requests.post(f"{API_BASE_URL}/refresh-token/{user_id}")
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Token refreshed successfully!")
            st.info(f"New token: {result['new_token']}")
            # Reload users to show updated data
            st.rerun()
        else:
            st.error(f"Error refreshing token: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Error refreshing token: {str(e)}")

def send_verification_email_single(user_id):
    """Send verification email to a single user"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/send-emails",
            json=[user_id]
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                st.toast(f"✅ Email sent successfully!")
            else:
                st.toast(f"⚠️ {result['message']}")
        else:
            st.error(f"Error sending email: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def verify_user_page():
    st.header("🔐 Verify User")
    st.write("Verify a user with their email and token.")
    
    with st.form("verify_form"):
        email = st.text_input("Email")
        token = st.text_input("Verification Token")
        
        submitted = st.form_submit_button("Verify User")
        
        if submitted:
            if email and token:
                verify_user(email, token)
            else:
                st.error("Please provide both email and token.")

def verify_user(email, token):
    """Verify a user with email and token"""
    try:
        data = {"email": email, "token": token}
        response = requests.post(f"{API_BASE_URL}/verify", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                st.success(f"✅ {result['message']}")
            else:
                st.error(f"❌ {result['message']}")
        else:
            st.error(f"Error: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def mask_token(token):
    """Mask token for display (show only first and last character)"""
    if len(token) <= 2:
        return token
    return token[0] + "*" * (len(token) - 2) + token[-1]

def format_date(date_string):
    """Format date string for display"""
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return date_string

def delete_single_user(user_id):
    """Delete a single user"""
    try:
        response = requests.delete(f"{API_BASE_URL}/users/{user_id}")
        
        if response.status_code == 200:
            st.success(f"✅ User deleted successfully!")
            st.rerun()
        else:
            st.error(f"Error deleting user: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Error deleting user: {str(e)}")

if __name__ == "__main__":
    main() 