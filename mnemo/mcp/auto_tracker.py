"""Automatic project activity tracker for MCP server."""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import os

from mnemo.memory.client import MnemoMemoryClient
from mnemo.trackers import GitActivityTracker, CodeChangeTracker


class AutoProjectTracker:
    """Automatically tracks and records project activities."""
    
    def __init__(self, memory_client: MnemoMemoryClient):
        self.memory_client = memory_client
        self.project_path = os.getcwd()
        self.git_tracker = GitActivityTracker(memory_client, self.project_path)
        self.code_tracker = CodeChangeTracker(memory_client, self.project_path)
        self.tracking_interval = 300  # 5 minutes default
        self.is_tracking = False
        self._tracking_task: Optional[asyncio.Task] = None
    
    async def start_tracking(self, interval: int = 300):
        """Start automatic tracking."""
        if self.is_tracking:
            return
        
        self.tracking_interval = interval
        self.is_tracking = True
        self._tracking_task = asyncio.create_task(self._tracking_loop())
        
        # Initial tracking
        await self._track_once()
        
        print(f"[AUTO-TRACKING] Started tracking for project: {self.project_path}")
        print(f"   Interval: {interval} seconds")
    
    async def stop_tracking(self):
        """Stop automatic tracking."""
        self.is_tracking = False
        if self._tracking_task:
            self._tracking_task.cancel()
            try:
                await self._tracking_task
            except asyncio.CancelledError:
                pass
        
        print("[AUTO-TRACKING] Stopped tracking")
    
    async def _tracking_loop(self):
        """Main tracking loop."""
        while self.is_tracking:
            try:
                await asyncio.sleep(self.tracking_interval)
                await self._track_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in tracking loop: {e}")
    
    async def _track_once(self):
        """Perform one tracking iteration."""
        timestamp = datetime.now()
        
        # Track git activities
        try:
            # Track new commits
            commits = self.git_tracker.track_commits()
            if commits:
                print(f"[AUTO-TRACKING] Tracked {len(commits)} new commits")
            
            # Track file changes
            changes = self.git_tracker.track_file_changes()
            if any(changes.values()):
                print(f"[AUTO-TRACKING] Tracked file changes: {sum(len(v) for v in changes.values())} files")
            
            # Track branch info
            branch_info = self.git_tracker.track_branch_info()
            
        except Exception as e:
            print(f"Git tracking error: {e}")
        
        # Track code changes for modified files
        try:
            if 'modified' in changes:
                for file_path in changes['modified'][:10]:  # Limit to 10 files
                    file_changes = self.code_tracker.track_file_content(file_path)
                    if file_changes:
                        print(f"[AUTO-TRACKING] Tracked code changes in {file_path}")
        except Exception as e:
            print(f"Code tracking error: {e}")
        
        # Save tracking session info
        self._save_tracking_session(timestamp, {
            'commits': len(commits) if 'commits' in locals() else 0,
            'file_changes': sum(len(v) for v in changes.values()) if 'changes' in locals() else 0,
            'branch': branch_info.get('current_branch', 'unknown') if 'branch_info' in locals() else 'unknown'
        })
    
    def _save_tracking_session(self, timestamp: datetime, stats: Dict[str, Any]):
        """Save tracking session information."""
        memory_key = f"tracking_session_{timestamp.strftime('%Y%m%d_%H%M')}"
        memory_content = (
            f"Auto-tracking session at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Project: {os.path.basename(self.project_path)}\n"
            f"Branch: {stats['branch']}\n"
            f"New commits: {stats['commits']}\n"
            f"File changes: {stats['file_changes']}"
        )
        
        self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"tracking", "session", "auto", "mentat"}
        )


class SessionMemoryTracker:
    """Tracks and saves chat session content."""
    
    def __init__(self, memory_client: MnemoMemoryClient):
        self.memory_client = memory_client
        self.session_messages = []
        self.session_start = datetime.now()
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.max_messages_before_summary = 20
        self.important_keywords = {
            'decision', 'implement', 'change', 'fix', 'bug', 'feature',
            'remember', 'important', 'todo', 'plan', 'design'
        }
    
    def add_message(self, role: str, content: str, message_type: str = "chat"):
        """Add a message to the session."""
        message_data = {
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'content': content,
            'type': message_type,
            'is_important': self._is_important_message(content)
        }
        
        self.session_messages.append(message_data)
        
        # Save important messages immediately
        if message_data['is_important']:
            self._save_important_message(message_data)
        
        # Check if we need to create a summary
        if len(self.session_messages) >= self.max_messages_before_summary:
            self._save_session_summary()
    
    def _is_important_message(self, content: str) -> bool:
        """Check if message contains important keywords."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.important_keywords)
    
    def _save_session_summary(self):
        """Save a summary of the session."""
        if not self.session_messages:
            return
        
        # For now, save the full conversation
        # In the future, we could use an LLM to summarize
        session_duration = datetime.now() - self.session_start
        
        memory_key = f"chat_session_{self.session_start.strftime('%Y%m%d_%H%M')}"
        
        # Create conversation text
        conversation_parts = []
        for msg in self.session_messages[-10:]:  # Last 10 messages
            conversation_parts.append(f"{msg['role']}: {msg['content'][:200]}...")
        
        memory_content = (
            f"Chat session from {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Duration: {session_duration}\n"
            f"Messages: {len(self.session_messages)}\n\n"
            f"Recent conversation:\n" + "\n".join(conversation_parts)
        )
        
        self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"chat", "session", "conversation", "mentat"}
        )
        
        # Reset for next batch
        self.session_messages = self.session_messages[-5:]  # Keep last 5 for context
    
    def _save_important_message(self, message_data: Dict[str, Any]):
        """Save an important message immediately."""
        memory_key = f"important_message_{self.session_id}_{datetime.now().strftime('%H%M%S')}"
        
        memory_content = (
            f"Important message in chat session\n"
            f"Role: {message_data['role']}\n"
            f"Time: {message_data['timestamp']}\n"
            f"Content: {message_data['content'][:500]}"
        )
        
        self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"chat", "important", "session", self.session_id}
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary."""
        return {
            'session_id': self.session_id,
            'start_time': self.session_start.isoformat(),
            'message_count': len(self.session_messages),
            'important_messages': sum(1 for msg in self.session_messages if msg.get('is_important', False)),
            'duration': str(datetime.now() - self.session_start)
        }