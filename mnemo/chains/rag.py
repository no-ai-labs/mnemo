"""RAG (Retrieval-Augmented Generation) chain using Mnemo memories."""

from typing import Any, Dict, List, Optional
from langchain.chains.base import Chain
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain.chains.llm import LLMChain

from mnemo.memory.client import MnemoMemoryClient


class MemoryRAGChain(Chain):
    """
    Retrieval-Augmented Generation chain using Mnemo as the knowledge base.
    
    This chain retrieves relevant memories and uses them to generate
    informed responses to user queries.
    """
    
    memory_client: MnemoMemoryClient
    llm: BaseLanguageModel
    prompt: PromptTemplate
    retrieval_k: int = 10
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_client: MnemoMemoryClient,
        retrieval_k: int = 10,
        custom_prompt: Optional[PromptTemplate] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.memory_client = memory_client
        self.retrieval_k = retrieval_k
        
        # Use custom prompt or default
        if custom_prompt:
            self.prompt = custom_prompt
        else:
            self.prompt = PromptTemplate(
                input_variables=["question", "context"],
                template="""Answer the question based on the context below. If the context doesn't contain enough information to answer the question, say so clearly.

Context from memory:
{context}

Question: {question}

Answer:"""
            )
        
        self.llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    @property
    def input_keys(self) -> List[str]:
        return ["question"]
    
    @property
    def output_keys(self) -> List[str]:
        return ["answer", "source_memories"]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RAG chain."""
        question = inputs["question"]
        
        # Retrieve relevant memories
        memories = self.memory_client.search(
            query=question,
            limit=self.retrieval_k,
            similarity_threshold=0.6
        )
        
        # Format context from memories
        if memories:
            context_parts = []
            for i, memory in enumerate(memories):
                memory_context = f"""
Memory {i+1} (Type: {memory['type']}, Score: {memory['similarity_score']:.3f}):
{memory['content']}
"""
                context_parts.append(memory_context.strip())
            
            context = "\n\n".join(context_parts)
        else:
            context = "No relevant information found in memory."
        
        # Generate answer
        answer = self.llm_chain.run(question=question, context=context)
        
        return {
            "answer": answer,
            "source_memories": memories
        }


class CodePatternRAGChain(MemoryRAGChain):
    """
    Specialized RAG chain for code patterns and programming help.
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_client: MnemoMemoryClient,
        **kwargs
    ):
        # Custom prompt for code-related queries
        code_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template="""You are a programming assistant with access to a knowledge base of code patterns and examples.

Based on the code patterns and examples below, help answer the programming question.

Code Patterns and Examples:
{context}

Programming Question: {question}

Provide a helpful response that may include:
- Relevant code examples
- Best practices
- Explanations of patterns
- Step-by-step guidance

Response:"""
        )
        
        super().__init__(
            llm=llm,
            memory_client=memory_client,
            custom_prompt=code_prompt,
            **kwargs
        )
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code pattern RAG with specialized filtering."""
        question = inputs["question"]
        
        # Search specifically for code patterns and skills
        memories = self.memory_client.search(
            query=question,
            memory_types=["code_pattern", "skill"],
            limit=self.retrieval_k,
            similarity_threshold=0.5
        )
        
        # If no code patterns found, search all memory types
        if not memories:
            memories = self.memory_client.search(
                query=question,
                limit=self.retrieval_k,
                similarity_threshold=0.6
            )
        
        # Format context with code highlighting
        if memories:
            context_parts = []
            for i, memory in enumerate(memories):
                memory_type = memory['type']
                content = memory['content']
                
                # Add context about the memory type
                if memory_type == "code_pattern":
                    prefix = f"🔧 Code Pattern {i+1}:"
                elif memory_type == "skill":
                    prefix = f"💡 Skill/Technique {i+1}:"
                else:
                    prefix = f"📝 Knowledge {i+1}:"
                
                memory_context = f"{prefix}\n{content}"
                context_parts.append(memory_context)
            
            context = "\n\n" + "\n\n".join(context_parts)
        else:
            context = "No relevant code patterns or examples found in memory."
        
        # Generate answer
        answer = self.llm_chain.run(question=question, context=context)
        
        return {
            "answer": answer,
            "source_memories": memories
        }