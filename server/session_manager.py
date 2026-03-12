from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
import threading


class SessionManager:
    """
    Stores and manages conversation history per session_id.
    """
    
    MAX_MESSAGES_PER_SESSION = 6  # Keep last 3 user + 3 AI messages
    SESSION_TIMEOUT_HOURS = 24
    
    def __init__(self):
        """Initialize the session storage."""
        self._sessions: dict[str, dict] = {}
        self._lock = threading.Lock()
    
    def get_history(self, session_id: str) -> list[dict]:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of message dicts { "role": "user" | "assistant", "content": str }
            Empty list if session doesn't exist or has expired.
        """
        with self._lock:
            if session_id not in self._sessions:
                return []
            
            session = self._sessions[session_id]
            
            # Check if session has expired
            if self._is_expired(session["created_at"]):
                del self._sessions[session_id]
                return []
            
            # Update last_accessed
            session["last_accessed"] = datetime.now()
            
            return session["messages"].copy()
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the session's conversation history.
        Automatically trims to MAX_MESSAGES_PER_SESSION.
        
        Args:
            session_id: Unique session identifier
            role: "user" or "assistant"
            content: Message text
        """
        with self._lock:
            # Create session if it doesn't exist
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "messages": [],
                    "created_at": datetime.now(),
                    "last_accessed": datetime.now(),
                }
            
            session = self._sessions[session_id]
            
            # Add new message
            session["messages"].append({
                "role": role,
                "content": content,
            })
            
            # Trim to max messages (keep most recent)
            if len(session["messages"]) > self.MAX_MESSAGES_PER_SESSION:
                session["messages"] = session["messages"][-self.MAX_MESSAGES_PER_SESSION:]
            
            session["last_accessed"] = datetime.now()
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear all messages for a session (start fresh conversation).
        
        Args:
            session_id: Unique session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["messages"] = []
                self._sessions[session_id]["last_accessed"] = datetime.now()
    
    def _is_expired(self, created_at: datetime) -> bool:
        """Check if a session has expired based on creation time."""
        return datetime.now() - created_at > timedelta(hours=self.SESSION_TIMEOUT_HOURS)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        (Can be called periodically by a background task.)
        
        Returns:
            Number of sessions deleted
        """
        with self._lock:
            expired_sessions = [
                sid for sid, session in self._sessions.items()
                if self._is_expired(session["created_at"])
            ]
            for sid in expired_sessions:
                del self._sessions[sid]
            return len(expired_sessions)


# Global session manager instance
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return _session_manager
