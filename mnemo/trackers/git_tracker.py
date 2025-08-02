"""Git activity tracker for automatic project history recording."""

import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib

from mnemo.memory.client import MnemoMemoryClient


class GitActivityTracker:
    """Tracks git activities and automatically records them to memory."""
    
    def __init__(self, memory_client: MnemoMemoryClient, project_path: str = "."):
        self.memory_client = memory_client
        self.project_path = Path(project_path).resolve()
        self.last_commit_hash = None
        self._init_tracking()
    
    def _init_tracking(self):
        """Initialize tracking by storing current state."""
        try:
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.last_commit_hash = result.stdout.strip()
        except Exception:
            pass
    
    def track_commits(self, since_hash: Optional[str] = None) -> List[Dict[str, Any]]:
        """Track new commits since last check."""
        since = since_hash or self.last_commit_hash
        if not since:
            # If no reference point, get last 10 commits
            git_cmd = ["git", "log", "--pretty=format:%H|%an|%ae|%at|%s", "-10"]
        else:
            git_cmd = ["git", "log", f"{since}..HEAD", "--pretty=format:%H|%an|%ae|%at|%s"]
        
        try:
            result = subprocess.run(
                git_cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or not result.stdout:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 5:
                    commit_info = {
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'timestamp': int(parts[3]),
                        'message': '|'.join(parts[4:])  # Handle messages with |
                    }
                    commits.append(commit_info)
                    
                    # Automatically save to memory
                    self._save_commit_memory(commit_info)
            
            # Update last tracked commit
            if commits:
                self.last_commit_hash = commits[0]['hash']
            
            return commits
            
        except Exception as e:
            print(f"Error tracking commits: {e}")
            return []
    
    def _save_commit_memory(self, commit_info: Dict[str, Any]) -> str:
        """Save commit information to memory."""
        commit_time = datetime.fromtimestamp(commit_info['timestamp'])
        
        memory_key = f"git_commit_{commit_info['hash'][:8]}"
        memory_content = (
            f"Git commit by {commit_info['author']} at {commit_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Hash: {commit_info['hash']}\n"
            f"Message: {commit_info['message']}"
        )
        
        memory_id = self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"git", "commit", "auto-tracked", self.project_path.name}
        )
        
        return memory_id
    
    def track_file_changes(self) -> Dict[str, List[str]]:
        """Track current file changes (staged, modified, untracked)."""
        changes = {
            'staged': [],
            'modified': [],
            'untracked': []
        }
        
        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                changes['staged'] = [f for f in result.stdout.strip().split('\n') if f]
            
            # Get modified files
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                changes['modified'] = [f for f in result.stdout.strip().split('\n') if f]
            
            # Get untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                changes['untracked'] = [f for f in result.stdout.strip().split('\n') if f]
            
            # Save significant changes to memory
            if any(changes.values()):
                self._save_changes_memory(changes)
            
            return changes
            
        except Exception as e:
            print(f"Error tracking file changes: {e}")
            return changes
    
    def _save_changes_memory(self, changes: Dict[str, List[str]]) -> str:
        """Save file changes to memory."""
        timestamp = datetime.now()
        
        # Create a hash of the changes for deduplication
        changes_str = json.dumps(changes, sort_keys=True)
        changes_hash = hashlib.md5(changes_str.encode()).hexdigest()[:8]
        
        memory_key = f"git_changes_{timestamp.strftime('%Y%m%d_%H%M')}_{changes_hash}"
        
        parts = []
        if changes['staged']:
            parts.append(f"Staged files: {', '.join(changes['staged'])}")
        if changes['modified']:
            parts.append(f"Modified files: {', '.join(changes['modified'])}")
        if changes['untracked']:
            parts.append(f"Untracked files: {', '.join(changes['untracked'][:5])}")  # Limit untracked
        
        memory_content = (
            f"Git working directory status at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Project: {self.project_path.name}\n" +
            '\n'.join(parts)
        )
        
        memory_id = self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"git", "status", "auto-tracked", self.project_path.name}
        )
        
        return memory_id
    
    def track_branch_info(self) -> Dict[str, Any]:
        """Track current branch information."""
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get remote tracking info
            result = subprocess.run(
                ["git", "status", "-sb"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            branch_info = {
                'current_branch': current_branch,
                'tracking_info': result.stdout.strip() if result.returncode == 0 else ""
            }
            
            # Save branch switch if detected
            self._save_branch_memory(branch_info)
            
            return branch_info
            
        except Exception as e:
            print(f"Error tracking branch info: {e}")
            return {'current_branch': 'unknown', 'tracking_info': ''}
    
    def _save_branch_memory(self, branch_info: Dict[str, Any]) -> Optional[str]:
        """Save branch information to memory if significant."""
        current_branch = branch_info['current_branch']
        
        # Store current branch in a specific key
        branch_memory_key = f"current_branch_{self.project_path.name}"
        
        # Check if this is a branch switch by looking for recent memories
        # Use search to get the most recent branch memory
        results = self.memory_client.search(
            query=f"current branch {self.project_path.name}",
            tags={"git", "branch", "current"},
            limit=1
        )
        recent_branch_memory = results[0]['content'] if results else None
        
        # First time or branch changed
        if not recent_branch_memory or current_branch not in recent_branch_memory:
            # Save current branch state
            self.memory_client.remember(
                key=branch_memory_key,
                content=f"Current branch: {current_branch}",
                memory_type="fact",
                tags={"git", "branch", "current", self.project_path.name}
            )
            
            # If this is a branch switch (not first time)
            if recent_branch_memory:
                # Extract previous branch from memory
                prev_branch = recent_branch_memory.split("Current branch: ")[-1].strip()
                
                memory_key = f"branch_switch_{datetime.now().strftime('%Y%m%d_%H%M')}"
                memory_content = (
                    f"Branch switch in project {self.project_path.name}\n"
                    f"From: {prev_branch}\n"
                    f"To: {current_branch}\n"
                    f"Status: {branch_info['tracking_info']}"
                )
                
                memory_id = self.memory_client.remember(
                    key=memory_key,
                    content=memory_content,
                    memory_type="fact",
                    tags={"git", "branch", "switch", "auto-tracked", self.project_path.name}
                )
                
                return memory_id
        
        return None