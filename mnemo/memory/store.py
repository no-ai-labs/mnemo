"""LangChain-based vector store for Mnemo."""

from typing import Any, Dict, List, Optional, Set, Tuple
import os
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from mnemo.core.types import MemoryDocument, MemoryMetadata, MemoryType, MemoryScope, MemoryQuery
from mnemo.core.embeddings import MnemoEmbeddings


class MnemoVectorStore:
    """
    LangChain-based vector store for Mnemo memories.
    
    Built on ChromaDB for fast similarity search with rich metadata filtering.
    """
    
    def __init__(
        self,
        collection_name: str = "mnemo_memories",
        persist_directory: str = "./mnemo_db",
        embedding_function: Optional[MnemoEmbeddings] = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        # Initialize embeddings
        if embedding_function is None:
            self.embeddings = MnemoEmbeddings()
        else:
            self.embeddings = embedding_function
        
        # Initialize ChromaDB
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
    
    def add_memory(
        self,
        content: str,
        memory_metadata: MemoryMetadata,
        memory_id: Optional[str] = None
    ) -> str:
        """Add a memory to the vector store."""
        
        # Create memory document
        memory_doc = MemoryDocument.create(
            page_content=content,
            memory_metadata=memory_metadata
        )
        
        # Use provided ID or generate one
        if memory_id:
            memory_doc.memory_metadata.memory_id = memory_id
            memory_doc.metadata["memory_id"] = memory_id
        
        # Add to vector store
        ids = self.vectorstore.add_documents([memory_doc], ids=[memory_doc.memory_id])
        
        return memory_doc.memory_id
    
    def add_memories(self, memories: List[MemoryDocument]) -> List[str]:
        """Add multiple memories to the vector store."""
        ids = [mem.memory_id for mem in memories]
        self.vectorstore.add_documents(memories, ids=ids)
        return ids
    
    def search_memories(
        self,
        query: str,
        k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[MemoryDocument, float]]:
        """Search for similar memories."""
        
        # Perform similarity search with scores
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict
        )
        
        # Convert results to MemoryDocuments and apply post-processing filters
        memory_results = []
        for doc, score in results:
            if score_threshold is None or score >= score_threshold:
                # Reconstruct MemoryDocument from regular Document
                memory_doc = self._doc_to_memory_doc(doc)
                memory_results.append((memory_doc, score))
        
        return memory_results
    
    def search_by_metadata(
        self,
        memory_query: MemoryQuery
    ) -> List[Tuple[MemoryDocument, float]]:
        """Search memories using Mnemo query structure."""
        
        # Build filter dictionary for ChromaDB
        # ChromaDB requires specific filter format: {"$and": [conditions]} or {"$or": [conditions]}
        conditions = []
        
        if memory_query.memory_types:
            if len(memory_query.memory_types) == 1:
                conditions.append({"memory_type": {"$eq": list(memory_query.memory_types)[0].value}})
            else:
                conditions.append({"memory_type": {"$in": [mt.value for mt in memory_query.memory_types]}})
        
        if memory_query.scopes:
            if len(memory_query.scopes) == 1:
                conditions.append({"scope": {"$eq": list(memory_query.scopes)[0].value}})
            else:
                conditions.append({"scope": {"$in": [s.value for s in memory_query.scopes]}})
        
        if memory_query.workspace_path:
            conditions.append({"workspace_path": {"$eq": memory_query.workspace_path}})
        
        if memory_query.project_name:
            conditions.append({"project_name": {"$eq": memory_query.project_name}})
        
        if memory_query.session_id:
            conditions.append({"session_id": {"$eq": memory_query.session_id}})
        
        # Skip tag filtering for now as ChromaDB has limitations with string matching
        # We'll filter tags in post-processing
        # if memory_query.tags:
        #     # For tags stored as comma-separated string, we need to check if any tag is contained
        #     for tag in memory_query.tags:
        #         conditions.append({"tags": {"$contains": tag}})
        
        # Create final filter
        if len(conditions) == 0:
            filter_dict = None
        elif len(conditions) == 1:
            filter_dict = conditions[0]
        else:
            filter_dict = {"$and": conditions}
        
        # Perform search
        results = self.search_memories(
            query=memory_query.query_text,
            k=memory_query.limit * 2,  # Get more results for tag filtering
            filter_dict=filter_dict if filter_dict else None,
            score_threshold=memory_query.similarity_threshold
        )
        
        # Post-process for tag filtering if needed
        if memory_query.tags:
            filtered_results = []
            for memory_doc, score in results:
                # Check if any of the required tags are in the document's tags
                doc_tags = memory_doc.metadata.get("tags", "").split(",")
                doc_tags = [tag.strip() for tag in doc_tags if tag.strip()]
                
                if any(tag in doc_tags for tag in memory_query.tags):
                    filtered_results.append((memory_doc, score))
            
            # Limit to requested number
            results = filtered_results[:memory_query.limit]
        
        return results
    
    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryDocument]:
        """Retrieve a specific memory by ID."""
        
        # Use ChromaDB's get method
        try:
            result = self.vectorstore.get(ids=[memory_id])
            if result['documents'] and len(result['documents']) > 0:
                # Reconstruct document
                doc_data = {
                    'page_content': result['documents'][0],
                    'metadata': result['metadatas'][0] if result['metadatas'] else {}
                }
                doc = Document(**doc_data)
                return self._doc_to_memory_doc(doc)
        except Exception:
            pass
        
        return None
    
    def update_memory(
        self,
        memory_id: str,
        new_content: Optional[str] = None,
        new_metadata: Optional[MemoryMetadata] = None
    ) -> bool:
        """Update an existing memory."""
        
        # Get existing memory
        existing_memory = self.get_memory_by_id(memory_id)
        if not existing_memory:
            return False
        
        # Update content and metadata
        content = new_content if new_content else existing_memory.page_content
        metadata = new_metadata if new_metadata else existing_memory.memory_metadata
        
        # Delete old memory
        self.delete_memory(memory_id)
        
        # Add updated memory
        self.add_memory(content, metadata, memory_id)
        
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            self.vectorstore.delete(ids=[memory_id])
            return True
        except Exception:
            return False
    
    def delete_memories(self, memory_ids: List[str]) -> int:
        """Delete multiple memories."""
        deleted_count = 0
        for memory_id in memory_ids:
            if self.delete_memory(memory_id):
                deleted_count += 1
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store."""
        
        # Get all documents to calculate stats
        try:
            all_docs = self.vectorstore.get()
            total_count = len(all_docs['documents']) if all_docs['documents'] else 0
            
            # Count by type and scope
            type_counts = {}
            scope_counts = {}
            
            if all_docs['metadatas']:
                for metadata in all_docs['metadatas']:
                    # Count by memory type
                    mem_type = metadata.get('memory_type', 'unknown')
                    type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
                    
                    # Count by scope
                    scope = metadata.get('scope', 'unknown')
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1
            
            return {
                "total_count": total_count,
                "type_counts": type_counts,
                "scope_counts": scope_counts,
                "backend": "chromadb",
                "collection_name": self.collection_name
            }
        
        except Exception:
            return {
                "total_count": 0,
                "type_counts": {},
                "scope_counts": {},
                "backend": "chromadb",
                "collection_name": self.collection_name
            }
    
    def _doc_to_memory_doc(self, doc: Document) -> MemoryDocument:
        """Convert a LangChain Document to MemoryDocument."""
        
        # Extract memory metadata from document metadata
        metadata_dict = doc.metadata
        
        # Reconstruct MemoryMetadata
        memory_metadata = MemoryMetadata(
            memory_id=metadata_dict.get("memory_id", ""),
            memory_type=MemoryType(metadata_dict.get("memory_type", "fact")),
            scope=MemoryScope(metadata_dict.get("scope", "workspace")),
            workspace_path=metadata_dict.get("workspace_path"),
            project_name=metadata_dict.get("project_name"),
            session_id=metadata_dict.get("session_id"),
            tags=set(metadata_dict.get("tags", [])),
            access_count=metadata_dict.get("access_count", 0),
            relevance_score=metadata_dict.get("relevance_score", 1.0)
        )
        
        return MemoryDocument(
            page_content=doc.page_content,
            memory_metadata=memory_metadata
        )
    
    def persist(self) -> None:
        """Persist the vector store to disk."""
        self.vectorstore.persist()
    
    def cleanup_expired(self) -> int:
        """Remove expired memories."""
        # This would require getting all documents and checking expiration
        # For now, return 0 as ChromaDB doesn't have built-in expiration
        return 0