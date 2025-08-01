"""High-level client for Mnemo memory operations."""

from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta

from mnemo.memory.store import MnemoVectorStore
from mnemo.core.types import (
    MemoryDocument, MemoryMetadata, MemoryType, 
    MemoryScope, MemoryPriority, MemoryQuery
)


class MnemoMemoryClient:
    """
    High-level client for interacting with Mnemo memories.
    
    Provides a simple, intuitive API for AI assistants to store
    and retrieve memories using LangChain's vector store capabilities.
    """
    
    def __init__(
        self,
        vector_store: Optional[MnemoVectorStore] = None,
        default_workspace: Optional[str] = None,
        default_project: Optional[str] = None
    ):
        self.vector_store = vector_store or MnemoVectorStore()
        self.context = {
            "workspace_path": default_workspace,
            "project_name": default_project,
            "session_id": None,
            "user_id": None
        }
    
    # Context Management
    def set_context(
        self,
        workspace_path: Optional[str] = None,
        project_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Set the current context for memory operations."""
        if workspace_path is not None:
            self.context["workspace_path"] = workspace_path
        if project_name is not None:
            self.context["project_name"] = project_name
        if session_id is not None:
            self.context["session_id"] = session_id
        if user_id is not None:
            self.context["user_id"] = user_id
    
    def get_context(self) -> Dict[str, Optional[str]]:
        """Get the current context."""
        return self.context.copy()
    
    # Core Memory Operations
    def remember(
        self,
        key: str,
        content: str,
        memory_type: str = "fact",
        scope: str = "workspace",
        priority: str = "medium",
        tags: Optional[Set[str]] = None,
        expires_in_seconds: Optional[int] = None
    ) -> str:
        """Remember something (store a memory)."""
        
        # Create metadata
        metadata = MemoryMetadata(
            memory_type=MemoryType(memory_type),
            scope=MemoryScope(scope),
            priority=MemoryPriority[priority.upper()],
            tags=tags or set(),
            workspace_path=self.context["workspace_path"],
            project_name=self.context["project_name"],
            session_id=self.context["session_id"],
            user_id=self.context["user_id"],
            source=f"mnemo_client_{key}"
        )
        
        # Set expiration if specified
        if expires_in_seconds:
            metadata.expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)
        
        # Store the memory
        memory_id = self.vector_store.add_memory(content, metadata)
        
        return memory_id
    
    def recall(self, query: str, k: int = 1) -> Optional[str]:
        """Recall the most relevant memory for a query."""
        results = self.search(query, limit=k)
        
        if results:
            return results[0]["content"]
        
        return None
    
    def search(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for memories."""
        
        # Create memory query
        memory_query = MemoryQuery(
            query_text=query,
            memory_types={MemoryType(t) for t in memory_types} if memory_types else None,
            scopes={MemoryScope(s) for s in scopes} if scopes else None,
            tags=tags,
            workspace_path=self.context["workspace_path"],
            project_name=self.context["project_name"],
            session_id=self.context["session_id"],
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Perform search
        results = self.vector_store.search_by_metadata(memory_query)
        
        # Convert to simple dict format
        formatted_results = []
        for memory_doc, score in results:
            # Update access tracking
            memory_doc.update_access()
            self.vector_store.update_memory(
                memory_doc.memory_id,
                new_metadata=memory_doc.memory_metadata
            )
            
            formatted_results.append({
                "memory_id": memory_doc.memory_id,
                "content": memory_doc.page_content,
                "type": memory_doc.memory_metadata.memory_type.value,
                "scope": memory_doc.memory_metadata.scope.value,
                "tags": list(memory_doc.memory_metadata.tags),
                "created_at": memory_doc.memory_metadata.created_at.isoformat(),
                "similarity_score": score,
                "relevance_score": memory_doc.memory_metadata.relevance_score
            })
        
        return formatted_results
    
    def forget(self, memory_id: str) -> bool:
        """Forget a memory by ID."""
        return self.vector_store.delete_memory(memory_id)
    
    # Specialized Memory Types
    def remember_fact(
        self,
        key: str,
        fact: str,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Remember a fact."""
        return self.remember(
            key=key,
            content=fact,
            memory_type="fact",
            scope="workspace",
            priority="medium",
            tags=tags
        )
    
    def remember_skill(
        self,
        key: str,
        skill_description: str,
        skill_data: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Remember a skill or technique."""
        
        # Combine description and data
        content = skill_description
        if skill_data:
            content += f"\n\nSkill Data: {skill_data}"
        
        skill_tags = {"skill"}
        if tags:
            skill_tags.update(tags)
        
        return self.remember(
            key=key,
            content=content,
            memory_type="skill",
            scope="global",
            priority="high",
            tags=skill_tags
        )
    
    def remember_code_pattern(
        self,
        pattern_name: str,
        code: str,
        language: str,
        description: str,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Remember a code pattern."""
        
        content = f"# {pattern_name}\n\n{description}\n\n```{language}\n{code}\n```"
        
        pattern_tags = {"code_pattern", language}
        if tags:
            pattern_tags.update(tags)
        
        return self.remember(
            key=f"code_pattern_{pattern_name}",
            content=content,
            memory_type="code_pattern",
            scope="workspace",
            priority="high",
            tags=pattern_tags
        )
    
    def remember_preference(
        self,
        key: str,
        preference: Any,
        scope: str = "global"
    ) -> str:
        """Remember a user preference."""
        
        content = f"Preference: {key}\nValue: {preference}"
        
        return self.remember(
            key=key,
            content=content,
            memory_type="preference",
            scope=scope,
            priority="high",
            tags={"preference", "user_setting"}
        )
    
    def remember_conversation(
        self,
        key: str,
        conversation_data: str,
        expires_in_hours: int = 24
    ) -> str:
        """Remember conversation context."""
        return self.remember(
            key=key,
            content=conversation_data,
            memory_type="conversation",
            scope="session",
            priority="medium",
            tags={"conversation", "chat_history"},
            expires_in_seconds=expires_in_hours * 3600
        )
    
    # Advanced Operations
    def get_memories_by_tags(
        self,
        tags: Set[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get memories by tags."""
        return self.search(
            query="",  # Empty query to search by metadata only
            tags=tags,
            limit=limit,
            similarity_threshold=0.0  # Lower threshold for tag-based search
        )
    
    def get_workspace_context(
        self,
        workspace_path: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all context for a workspace."""
        
        workspace = workspace_path or self.context["workspace_path"]
        if not workspace:
            return {}
        
        # Save current context
        old_context = self.get_context()
        
        # Set workspace context
        self.set_context(workspace_path=workspace)
        
        # Search for different types of memories
        context = {
            "facts": self.search("", memory_types=["fact"], limit=50),
            "skills": self.search("", memory_types=["skill"], limit=30),
            "code_patterns": self.search("", memory_types=["code_pattern"], limit=20),
            "preferences": self.search("", memory_types=["preference"], limit=20),
            "conversations": self.search("", memory_types=["conversation"], limit=10)
        }
        
        # Restore context
        self.set_context(**old_context)
        
        return context
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.vector_store.get_stats()
    
    def cleanup_expired(self) -> int:
        """Clean up expired memories."""
        return self.vector_store.cleanup_expired()
    
    def persist(self) -> None:
        """Persist the vector store."""
        self.vector_store.persist()