from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import json
import os
from app.core.rag_engine import rag_engine
from app.services.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, session_storage_file: str = "chat_sessions.json"):
        self.session_storage_file = session_storage_file
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load chat sessions from file"""
        try:
            if os.path.exists(self.session_storage_file):
                with open(self.session_storage_file, 'r') as f:
                    self.sessions = json.load(f)
                logger.info("Chat sessions loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load chat sessions: {e}")
            self.sessions = {}
    
    def _save_sessions(self):
        """Save chat sessions to file"""
        try:
            with open(self.session_storage_file, 'w') as f:
                json.dump(self.sessions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save chat sessions: {e}")
    
    def _get_session_key(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Generate session key"""
        if session_id:
            return f"{user_id}:{session_id}"
        return f"{user_id}:default"
    
    def _get_conversation_history(self, session_key: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history for context"""
        if session_key not in self.sessions:
            return []
        
        return self.sessions[session_key][-limit:]
    
    def _add_to_history(self, session_key: str, user_message: str, assistant_response: str, metadata: Dict[str, Any] = None):
        """Add exchange to conversation history"""
        if session_key not in self.sessions:
            self.sessions[session_key] = []
        
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": assistant_response,
            "metadata": metadata or {}
        }
        
        self.sessions[session_key].append(exchange)
        
        # Keep only last 50 exchanges to manage memory
        if len(self.sessions[session_key]) > 50:
            self.sessions[session_key] = self.sessions[session_key][-50:]
        
        self._save_sessions()
    
    async def process_message(self, user_id: str, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process user message and return response"""
        try:
            # Check usage limits
            usage_info = usage_tracker.check_and_increment(user_id)
            
            if not usage_info["allowed"]:
                return {
                    "success": False,
                    "error": "Daily message limit exceeded",
                    "usage_info": usage_info,
                    "response": "You have reached your daily message limit of 200 messages. Please try again tomorrow.",
                    "sources_used": []
                }
            
            # Get session key and conversation history
            session_key = self._get_session_key(user_id, session_id)
            conversation_history = self._get_conversation_history(session_key)
            
            # Generate response using RAG
            rag_result = rag_engine.chat(
                query=message,
                conversation_history=conversation_history
            )
            
            # Add to conversation history
            self._add_to_history(
                session_key=session_key,
                user_message=message,
                assistant_response=rag_result["response"],
                metadata={
                    "sources_used": rag_result["sources_used"],
                    "num_sources": rag_result["num_sources"],
                    "has_context": rag_result["has_context"]
                }
            )
            
            return {
                "success": True,
                "response": rag_result["response"],
                "sources_used": rag_result["sources_used"],
                "usage_info": usage_info,
                "session_info": {
                    "session_key": session_key,
                    "message_count": len(self.sessions[session_key])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process message for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                "sources_used": []
            }
    
    def get_session_history(self, user_id: str, session_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        session_key = self._get_session_key(user_id, session_id)
        
        if session_key not in self.sessions:
            return []
        
        return self.sessions[session_key][-limit:]
    
    def clear_session(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Clear conversation history for a session"""
        try:
            session_key = self._get_session_key(user_id, session_id)
            
            if session_key in self.sessions:
                del self.sessions[session_key]
                self._save_sessions()
                logger.info(f"Cleared session: {session_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to clear session {session_key}: {e}")
            return False
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        user_sessions = []
        
        for session_key in self.sessions:
            if session_key.startswith(f"{user_id}:"):
                session_data = self.sessions[session_key]
                if session_data:
                    last_message = session_data[-1]
                    session_info = {
                        "session_key": session_key,
                        "session_id": session_key.split(":", 1)[1],
                        "message_count": len(session_data),
                        "last_activity": last_message.get("timestamp"),
                        "last_message_preview": last_message.get("user", "")[:100] + "..." if len(last_message.get("user", "")) > 100 else last_message.get("user", "")
                    }
                    user_sessions.append(session_info)
        
        # Sort by last activity
        user_sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return user_sessions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chat service statistics"""
        total_sessions = len(self.sessions)
        total_messages = sum(len(session) for session in self.sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": total_messages / max(total_sessions, 1)
        }

# Global chat service instance
chat_service = ChatService()