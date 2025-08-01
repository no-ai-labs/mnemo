"""Custom embeddings for Mnemo memory system."""

import os
from typing import List, Optional
from langchain_core.embeddings import Embeddings

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class MockEmbeddings(Embeddings):
    """Mock embeddings for testing/demo when OpenAI is not available."""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Return simple mock embeddings."""
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Return simple mock embedding."""
        return [0.1, 0.2, 0.3, 0.4]


class MnemoEmbeddings(Embeddings):
    """
    Custom embeddings wrapper for Mnemo.
    
    This can be extended to use different embedding models or
    add custom preprocessing for memory-specific content.
    Falls back to mock embeddings if OpenAI is not available.
    """
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        openai_api_key: Optional[str] = None,
        use_mock: bool = False,
        **kwargs
    ):
        self.model = model
        
        # Check if we should use mock embeddings
        if use_mock or not OPENAI_AVAILABLE or not (openai_api_key or os.getenv("OPENAI_API_KEY")):
            print("⚠️  Using mock embeddings (OpenAI API key not found)")
            self.base_embeddings = MockEmbeddings()
            self.is_mock = True
        else:
            self.base_embeddings = OpenAIEmbeddings(
                model=model,
                openai_api_key=openai_api_key,
                **kwargs
            )
            self.is_mock = False
    
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
        return await self.base_embeddings.aembed_documents(processed_texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query."""
        processed_text = self._preprocess_text(text)
        return await self.base_embeddings.aembed_query(processed_text)