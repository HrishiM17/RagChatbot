from datetime import datetime, date
from typing import Dict, Any
import json
import os
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class UsageTracker:
    def __init__(self, storage_file: str = "usage_data.json"):
        self.storage_file = storage_file
        self.usage_data: Dict[str, Dict[str, Any]] = {}
        self._load_usage_data()
    
    def _load_usage_data(self):
        """Load usage data from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    # Convert date strings back to date objects for comparison
                    for user_id, user_data in data.items():
                        if 'date' in user_data:
                            user_data['date'] = datetime.strptime(user_data['date'], '%Y-%m-%d').date()
                    self.usage_data = data
                logger.info("Usage data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load usage data: {e}")
            self.usage_data = {}
    
    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            # Convert date objects to strings for JSON serialization
            data_to_save = {}
            for user_id, user_data in self.usage_data.items():
                data_to_save[user_id] = user_data.copy()
                if 'date' in data_to_save[user_id]:
                    data_to_save[user_id]['date'] = data_to_save[user_id]['date'].isoformat()
            
            with open(self.storage_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")
    
    def check_and_increment(self, user_id: str) -> Dict[str, Any]:
        """Check if user can send message and increment counter"""
        today = date.today()
        
        # Initialize user data if doesn't exist
        if user_id not in self.usage_data:
            self.usage_data[user_id] = {
                "date": today,
                "count": 0,
                "total_messages": 0
            }
        
        user_data = self.usage_data[user_id]
        
        # Reset count if new day
        if user_data["date"] != today:
            user_data["date"] = today
            user_data["count"] = 0
        
        # Check if limit exceeded
        if user_data["count"] >= settings.DAILY_MESSAGE_LIMIT:
            return {
                "allowed": False,
                "remaining": 0,
                "used": user_data["count"],
                "limit": settings.DAILY_MESSAGE_LIMIT,
                "reset_time": "midnight"
            }
        
        # Increment counters
        user_data["count"] += 1
        user_data["total_messages"] = user_data.get("total_messages", 0) + 1
        
        # Save data
        self._save_usage_data()
        
        remaining = settings.DAILY_MESSAGE_LIMIT - user_data["count"]
        
        return {
            "allowed": True,
            "remaining": remaining,
            "used": user_data["count"],
            "limit": settings.DAILY_MESSAGE_LIMIT,
            "reset_time": "midnight"
        }
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get usage information for a user"""
        today = date.today()
        
        if user_id not in self.usage_data:
            return {
                "used": 0,
                "remaining": settings.DAILY_MESSAGE_LIMIT,
                "limit": settings.DAILY_MESSAGE_LIMIT,
                "total_messages": 0,
                "limit_exceeded": False
            }
        
        user_data = self.usage_data[user_id]
        
        # Reset if new day
        if user_data["date"] != today:
            daily_used = 0
        else:
            daily_used = user_data["count"]
        
        remaining = settings.DAILY_MESSAGE_LIMIT - daily_used
        
        return {
            "used": daily_used,
            "remaining": max(0, remaining),
            "limit": settings.DAILY_MESSAGE_LIMIT,
            "total_messages": user_data.get("total_messages", 0),
            "limit_exceeded": daily_used >= settings.DAILY_MESSAGE_LIMIT
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get overall usage statistics"""
        today = date.today()
        total_users = len(self.usage_data)
        active_today = 0
        total_messages_today = 0
        total_messages_all_time = 0
        
        for user_data in self.usage_data.values():
            if user_data["date"] == today:
                active_today += 1
                total_messages_today += user_data["count"]
            total_messages_all_time += user_data.get("total_messages", 0)
        
        return {
            "total_users": total_users,
            "active_users_today": active_today,
            "messages_today": total_messages_today,
            "total_messages": total_messages_all_time,
            "daily_limit": settings.DAILY_MESSAGE_LIMIT
        }

# Global usage tracker instance
usage_tracker = UsageTracker()