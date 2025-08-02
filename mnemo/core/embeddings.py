"""Custom embeddings for Mnemo memory system."""

import os
from typing import List, Optional
from langchain_core.embeddings import Embeddings

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    try:
        # Fallback to community version
        from langchain_community.embeddings import HuggingFaceEmbeddings
        SENTENCE_TRANSFORMERS_AVAILABLE = True
    except ImportError:
        SENTENCE_TRANSFORMERS_AVAILABLE = False


class MockEmbeddings(Embeddings):
    """Mock embeddings for testing/demo when no real embeddings available."""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Return simple mock embeddings (384 dims like sentence-transformers)."""
        return [[0.1] * 384 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Return simple mock embedding."""
        return [0.1] * 384


class MnemoEmbeddings(Embeddings):
    """
    Custom embeddings wrapper for Mnemo.
    
    Priority order:
    1. OpenAI embeddings (if API key available)
    2. Sentence Transformers (local, multilingual)
    3. Mock embeddings (fallback)
    
    Recommended models:
    - Qwen/Qwen3-Embedding-0.6B (multilingual, lightweight, M3 optimized) ⭐
    - Qwen/Qwen3-Embedding-4B (multilingual, high quality, 2560 dims)
    - intfloat/multilingual-e5-large (multilingual, large, 1024 dims)
    - paraphrase-multilingual-mpnet-base-v2 (multilingual, balanced, 768 dims)
    - sentence-transformers/all-MiniLM-L6-v2 (English only, fast, 384 dims)
    """
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        openai_api_key: Optional[str] = None,
        use_mock: bool = False,
        sentence_transformer_model: str = "Qwen/Qwen3-Embedding-0.6B",
        **kwargs
    ):
        self.model = model
        import sys
        
        # Priority 1: Try OpenAI if available
        if not use_mock and OPENAI_AVAILABLE and (openai_api_key or os.getenv("OPENAI_API_KEY")):
            try:
                self.base_embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=openai_api_key,
                    **kwargs
                )
                self.embedding_type = "openai"
                if hasattr(sys, 'stderr'):
                    print("✅ Using OpenAI embeddings", file=sys.stderr)
                return
            except Exception:
                pass
        
        # Priority 2: Try Sentence Transformers (local, free)
        if not use_mock and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.base_embeddings = HuggingFaceEmbeddings(
                    model_name=sentence_transformer_model,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                self.embedding_type = "sentence_transformers"
                if hasattr(sys, 'stderr'):
                    print(f"🤗 Using local embeddings: {sentence_transformer_model}", file=sys.stderr)
                return
            except Exception as e:
                if hasattr(sys, 'stderr'):
                    print(f"⚠️  Failed to load sentence transformers: {e}", file=sys.stderr)
        
        # Priority 3: Fallback to mock embeddings
        if hasattr(sys, 'stderr'):
            print("⚠️  Using mock embeddings (install sentence-transformers for better results)", file=sys.stderr)
        self.base_embeddings = MockEmbeddings()
        self.embedding_type = "mock"
    
    @property
    def is_mock(self) -> bool:
        """Check if using mock embeddings."""
        return self.embedding_type == "mock"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        # Preprocess texts for memory-specific content
        processed_texts = [self._preprocess_text(text) for text in texts]
        return self.base_embeddings.embed_documents(processed_texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        processed_text = self._preprocess_text(text)
        return self.base_embeddings.embed_query(processed_text)
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for better memory embeddings.
        
        This could include:
        - Normalizing code snippets
        - Enhancing context with metadata
        - Adding memory-specific tokens
        """
        # For now, just return the text as-is
        # Can be extended for memory-specific preprocessing
        return text
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        processed_texts = [self._preprocess_text(text) for text in texts]
        if hasattr(self.base_embeddings, 'aembed_documents'):
            return await self.base_embeddings.aembed_documents(processed_texts)
        else:
            # Fallback to sync version for embeddings that don't support async
            return self.base_embeddings.embed_documents(processed_texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query."""
        processed_text = self._preprocess_text(text)
        if hasattr(self.base_embeddings, 'aembed_query'):
            return await self.base_embeddings.aembed_query(processed_text)
        else:
            # Fallback to sync version for embeddings that don't support async
            return self.base_embeddings.embed_query(processed_text)