"""Core types for Mnemo memory system."""

from typing import Any, Dict, List, Optional, Set
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.documents import Document

from uuid import uuid4


class MemoryType(Enum):
    """Types of memories in the system."""
    FACT = "fact"
    SKILL = "skill"
    PREFERENCE = "preference"
    CONVERSATION = "conversation"
    CONTEXT = "context"
    CODE_PATTERN = "code_pattern"
    WORKSPACE = "workspace"
    PROJECT = "project"


class MemoryScope(Enum):
    """Scope of memory availability."""
    GLOBAL = "global"
    WORKSPACE = "workspace"
    PROJECT = "project"
    SESSION = "session"
    TEMPORARY = "temporary"


class MemoryPriority(Enum):
    """Priority levels for memory importance."""
    CRITICAL = 100
    HIGH = 80
    MEDIUM = 50
    LOW = 20
    BACKGROUND = 10


class MemoryMetadata(BaseModel):
    """Metadata for memory documents."""
    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    memory_type: MemoryType
    scope: MemoryScope = MemoryScope.WORKSPACE
    priority: MemoryPriority = MemoryPriority.MEDIUM
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Context
    workspace_path: Optional[str] = None
    project_name: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Relationships and tags
    tags: Set[str] = Field(default_factory=set)
    related_memories: Set[str] = Field(default_factory=set)
    
    # Usage tracking
    access_count: int = 0
    relevance_score: float = 1.0
    
    # Source information
    source: Optional[str] = None
    source_type: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def is_expired(self) -> bool:
        """Check if memory is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def update_access(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now()
        self.access_count += 1


class MemoryDocument(Document):
    """
    Enhanced LangChain Document with Mnemo metadata.
    
    This extends LangChain's Document class to include rich metadata
    for memory management.
    """
    
    @classmethod
    def create(
        cls,
        page_content: str,
        memory_metadata: MemoryMetadata,
        **kwargs
    ) -> "MemoryDocument":
        """Create a MemoryDocument from content and metadata."""
        # Convert memory metadata to dict for LangChain metadata
        # ChromaDB only accepts str, int, float, bool, or None for metadata
        metadata = {
            "memory_id": memory_metadata.memory_id,
            "memory_type": memory_metadata.memory_type.value,
            "scope": memory_metadata.scope.value,
            "priority": memory_metadata.priority.value,
            "created_at": memory_metadata.created_at.isoformat(),
            "workspace_path": memory_metadata.workspace_path or "",
            "project_name": memory_metadata.project_name or "",
            "session_id": memory_metadata.session_id or "",
            "tags": ",".join(memory_metadata.tags) if memory_metadata.tags else "",
            "access_count": memory_metadata.access_count,
            "relevance_score": memory_metadata.relevance_score,
        }
        
        doc = cls(page_content=page_content, metadata=metadata, **kwargs)
        # Store the original metadata object for easy access
        doc._memory_metadata = memory_metadata
        return doc
    
    @property
    def memory_metadata(self) -> MemoryMetadata:
        """Get the memory metadata."""
        return getattr(self, '_memory_metadata', None)
    
    def update_access(self) -> None:
        """Update access tracking."""
        if hasattr(self, '_memory_metadata'):
            self._memory_metadata.update_access()
            # Update the base metadata dict as well
            self.metadata["access_count"] = self._memory_metadata.access_count
            self.metadata["accessed_at"] = self._memory_metadata.accessed_at.isoformat()
    
    @classmethod
    def from_text(
        cls,
        text: str,
        memory_type: MemoryType,
        scope: MemoryScope = MemoryScope.WORKSPACE,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[Set[str]] = None,
        workspace_path: Optional[str] = None,
        project_name: Optional[str] = None,
        **kwargs
    ) -> "MemoryDocument":
        """Create a MemoryDocument from text with metadata."""
        
        memory_metadata = MemoryMetadata(
            memory_type=memory_type,
            scope=scope,
            priority=priority,
            tags=tags or set(),
            workspace_path=workspace_path,
            project_name=project_name,
            **kwargs
        )
        
        return cls.create(page_content=text, memory_metadata=memory_metadata)
    
    @property
    def memory_id(self) -> str:
        """Get the memory ID."""
        if self.memory_metadata:
            return self.memory_metadata.memory_id
        return self.metadata.get("memory_id", "")
    
    @property
    def is_expired(self) -> bool:
        """Check if the memory is expired."""
        if self.memory_metadata:
            return self.memory_metadata.is_expired
        return False


class MemoryQuery(BaseModel):
    """Query for retrieving memories."""
    query_text: str
    memory_types: Optional[Set[MemoryType]] = None
    scopes: Optional[Set[MemoryScope]] = None
    tags: Optional[Set[str]] = None
    workspace_path: Optional[str] = None
    project_name: Optional[str] = None
    session_id: Optional[str] = None
    include_expired: bool = False
    limit: int = 10
    similarity_threshold: float = 0.7
    
    class Config:
        arbitrary_types_allowed = True