import streamlit as st
import requests
import uuid
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"

if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your RAG chatbot. How can I help you today?"}
    ]

if 'usage_info' not in st.session_state:
    st.session_state.usage_info = {"used": 0, "remaining": 200}

def get_usage_info():
    """Get current usage information"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/usage/{st.session_state.user_id}")
        if response.status_code == 200:
            data = response.json()
            st.session_state.usage_info = {
                "used": data["messages_used"],
                "remaining": data["messages_remaining"]
            }
    except Exception:
        pass

def send_message(message):
    """Send message to the RAG API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "message": message,
                "user_id": st.session_state.user_id,
                "session_id": "streamlit_session"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "response": data["response"],
                "sources": data.get("sources_used", []),
                "usage_remaining": data.get("usage_remaining", 200)
            }
        else:
            return {"success": False, "error": "API Error"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def upload_files(uploaded_files):
    """Upload files to the RAG system"""
    try:
        files = []
        for uploaded_file in uploaded_files:
            files.append(("files", (uploaded_file.name, uploaded_file.read(), uploaded_file.type)))
        
        response = requests.post(
            f"{API_BASE_URL}/api/upload-documents",
            files=files,
            data={"user_id": st.session_state.user_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": data["message"]}
        else:
            return {"success": False, "error": "Upload failed"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

# Main UI
st.title("🤖 RAG Chatbot")
st.write("Ask questions about your documents or get general assistance")

# Sidebar for document management
with st.sidebar:
    st.header("📚 Document Management")
    
    # Usage information
    get_usage_info()
    usage = st.session_state.usage_info
    st.metric("Messages Used", f"{usage['used']}/200", f"Remaining: {usage['remaining']}")
    
    # File upload
    st.subheader("Upload Documents")
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'docx', 'txt', 'md'],
        accept_multiple_files=True
    )
    
    if st.button("Upload Files") and uploaded_files:
        with st.spinner("Uploading..."):
            result = upload_files(uploaded_files)
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["error"])
    
    # Clear chat
    if st.button("Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your RAG chatbot. How can I help you today?"}
        ]
        st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "sources" in message and message["sources"]:
            st.caption(f"Sources: {', '.join(message['sources'])}")

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    # Check usage limit
    if usage["remaining"] <= 0:
        st.error("Daily message limit exceeded!")
    else:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = send_message(prompt)
            
            if result["success"]:
                st.write(result["response"])
                if result["sources"]:
                    st.caption(f"Sources: {', '.join(result['sources'])}")
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": result["response"],
                    "sources": result["sources"]
                })
                
                # Update usage
                st.session_state.usage_info["remaining"] = result["usage_remaining"]
                st.session_state.usage_info["used"] = 200 - result["usage_remaining"]
            else:
                st.error(f"Error: {result['error']}")
                # Remove user message if error
                st.session_state.messages.pop()

# Footer
st.markdown("---")
st.caption("Make sure your FastAPI server is running on http://localhost:8000")