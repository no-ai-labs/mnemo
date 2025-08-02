"""Code change tracker for automatic code modification recording."""

import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import hashlib

from mnemo.memory.client import MnemoMemoryClient


class CodeChangeTracker:
    """Tracks code changes and patterns automatically."""
    
    def __init__(self, memory_client: MnemoMemoryClient, project_path: str = "."):
        self.memory_client = memory_client
        self.project_path = Path(project_path).resolve()
        self.file_snapshots: Dict[str, str] = {}
        self.tracked_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.rs', '.go'}
    
    def track_file_content(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Track changes in a specific file."""
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_path / file_path
        
        if not file_path.exists() or file_path.suffix not in self.tracked_extensions:
            return None
        
        try:
            current_content = file_path.read_text(encoding='utf-8')
            file_key = str(file_path.relative_to(self.project_path))
            
            # Check if we have a previous snapshot
            if file_key in self.file_snapshots:
                previous_content = self.file_snapshots[file_key]
                
                if previous_content != current_content:
                    # Analyze changes
                    changes = self._analyze_changes(file_key, previous_content, current_content)
                    
                    # Save significant changes to memory
                    if changes['significant']:
                        self._save_code_change_memory(file_key, changes)
                    
                    # Update snapshot
                    self.file_snapshots[file_key] = current_content
                    
                    return changes
            else:
                # First time tracking this file
                self.file_snapshots[file_key] = current_content
                
            return None
            
        except Exception as e:
            print(f"Error tracking file {file_path}: {e}")
            return None
    
    def _analyze_changes(self, file_path: str, old_content: str, new_content: str) -> Dict[str, Any]:
        """Analyze the changes between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        differ = difflib.unified_diff(old_lines, new_lines, fromfile=file_path, tofile=file_path)
        diff_lines = list(differ)
        
        # Count changes
        added_lines = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        
        # Detect what kind of changes
        changes_summary = self._summarize_changes(diff_lines, file_path)
        
        return {
            'file': file_path,
            'added_lines': added_lines,
            'removed_lines': removed_lines,
            'diff': ''.join(diff_lines[:100]),  # Limit diff size
            'summary': changes_summary,
            'significant': added_lines + removed_lines > 5  # Consider significant if > 5 lines changed
        }
    
    def _summarize_changes(self, diff_lines: List[str], file_path: str) -> str:
        """Create a human-readable summary of the changes."""
        summaries = []
        
        # Simple heuristics to detect change types
        added_functions = []
        modified_functions = []
        added_classes = []
        
        for i, line in enumerate(diff_lines):
            if line.startswith('+') and not line.startswith('+++'):
                content = line[1:].strip()
                if 'def ' in content:
                    func_name = content.split('def ')[1].split('(')[0] if 'def ' in content else ''
                    if func_name:
                        added_functions.append(func_name)
                elif 'class ' in content:
                    class_name = content.split('class ')[1].split('(')[0].split(':')[0] if 'class ' in content else ''
                    if class_name:
                        added_classes.append(class_name)
        
        if added_functions:
            summaries.append(f"Added functions: {', '.join(added_functions[:3])}")
        if added_classes:
            summaries.append(f"Added classes: {', '.join(added_classes[:3])}")
        
        if not summaries:
            summaries.append("Code modifications")
        
        return '; '.join(summaries)
    
    def _save_code_change_memory(self, file_path: str, changes: Dict[str, Any]) -> str:
        """Save code changes to memory."""
        timestamp = datetime.now()
        
        # Create unique key
        change_hash = hashlib.md5(f"{file_path}{timestamp}".encode()).hexdigest()[:8]
        memory_key = f"code_change_{timestamp.strftime('%Y%m%d_%H%M')}_{change_hash}"
        
        memory_content = (
            f"Code changes in {file_path} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Summary: {changes['summary']}\n"
            f"Lines added: {changes['added_lines']}, removed: {changes['removed_lines']}\n"
            f"Project: {self.project_path.name}"
        )
        
        memory_id = self.memory_client.remember(
            key=memory_key,
            content=memory_content,
            memory_type="fact",
            tags={"code", "changes", "auto-tracked", self.project_path.name, Path(file_path).suffix[1:]}
        )
        
        return memory_id
    
    def track_project_files(self, extensions: Optional[Set[str]] = None) -> Dict[str, int]:
        """Track all project files of given extensions."""
        extensions = extensions or self.tracked_extensions
        
        file_counts = {}
        for ext in extensions:
            count = len(list(self.project_path.rglob(f'*{ext}')))
            file_counts[ext] = count
        
        return file_counts
    
    def detect_patterns(self, file_path: str) -> List[Dict[str, Any]]:
        """Detect common code patterns in a file."""
        patterns = []
        
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Detect TODOs and FIXMEs
            for i, line in enumerate(lines):
                if 'TODO' in line or 'FIXME' in line:
                    patterns.append({
                        'type': 'todo',
                        'line': i + 1,
                        'content': line.strip(),
                        'file': file_path
                    })
            
            # Detect imports (Python example)
            if file_path.endswith('.py'):
                imports = [line for line in lines if line.startswith('import ') or line.startswith('from ')]
                if imports:
                    patterns.append({
                        'type': 'imports',
                        'count': len(imports),
                        'samples': imports[:5],
                        'file': file_path
                    })
            
            return patterns
            
        except Exception as e:
            print(f"Error detecting patterns in {file_path}: {e}")
            return []