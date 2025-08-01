"""LangChain chains for memory operations."""

from typing import Any, Dict, List, Optional
from langchain.chains.base import Chain
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain.chains.llm import LLMChain

from mnemo.memory.client import MnemoMemoryClient


class MemoryChain(Chain):
    """
    LangChain chain for memory-enhanced conversations.
    
    This chain automatically retrieves relevant memories and 
    incorporates them into LLM responses.
    """
    
    memory_client: MnemoMemoryClient
    llm: BaseLanguageModel
    prompt: PromptTemplate
    memory_k: int = 5
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_client: MnemoMemoryClient,
        memory_k: int = 5,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.memory_client = memory_client
        self.memory_k = memory_k
        
        # Default prompt template
        self.prompt = PromptTemplate(
            input_variables=["query", "relevant_memories", "context"],
            template="""You are an AI assistant with access to a comprehensive memory system.

Based on the relevant memories and context below, please provide a helpful response to the user's query.

Relevant Memories:
{relevant_memories}

Current Context:
{context}

User Query: {query}

Response:"""
        )
        
        # Create LLM chain
        self.llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    @property
    def input_keys(self) -> List[str]:
        """Input keys for the chain."""
        return ["query"]
    
    @property
    def output_keys(self) -> List[str]:
        """Output keys for the chain."""
        return ["response", "memories_used"]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the memory chain."""
        query = inputs["query"]
        
        # Retrieve relevant memories
        memories = self.memory_client.search(
            query=query,
            limit=self.memory_k
        )
        
        # Format memories for prompt
        if memories:
            formatted_memories = "\n".join([
                f"- [{mem['type']}] {mem['content'][:200]}..." 
                if len(mem['content']) > 200 
                else f"- [{mem['type']}] {mem['content']}"
                for mem in memories
            ])
        else:
            formatted_memories = "No relevant memories found."
        
        # Get current context
        context = self.memory_client.get_context()
        formatted_context = f"Workspace: {context.get('workspace_path', 'None')}, Project: {context.get('project_name', 'None')}"
        
        # Generate response using LLM
        llm_inputs = {
            "query": query,
            "relevant_memories": formatted_memories,
            "context": formatted_context
        }
        
        response = self.llm_chain.run(**llm_inputs)
        
        return {
            "response": response,
            "memories_used": memories
        }


class MemoryLearningChain(Chain):
    """
    Chain that learns from conversations and stores important information.
    """
    
    memory_client: MnemoMemoryClient
    llm: BaseLanguageModel
    extraction_prompt: PromptTemplate
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_client: MnemoMemoryClient,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.memory_client = memory_client
        
        # Prompt for extracting memorable information
        self.extraction_prompt = PromptTemplate(
            input_variables=["conversation"],
            template="""Analyze the following conversation and extract any important information that should be remembered for future interactions.

Focus on:
- Facts about the user, project, or workspace
- User preferences and settings
- Important decisions or conclusions
- Useful patterns or techniques
- Code snippets or configurations

Conversation:
{conversation}

Extract the important information in the following format:
FACTS: [list any factual information]
PREFERENCES: [list any user preferences]
SKILLS: [list any techniques or patterns]
CODE_PATTERNS: [list any code examples with language]

If no important information is found, respond with "NONE"."""
        )
        
        self.extraction_chain = LLMChain(llm=self.llm, prompt=self.extraction_prompt)
    
    @property
    def input_keys(self) -> List[str]:
        return ["conversation"]
    
    @property
    def output_keys(self) -> List[str]:
        return ["extracted_memories", "stored_count"]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and store memories from conversation."""
        conversation = inputs["conversation"]
        
        # Extract memorable information
        extraction_result = self.extraction_chain.run(conversation=conversation)
        
        stored_memories = []
        stored_count = 0
        
        if extraction_result.strip() != "NONE":
            # Parse the extraction result
            lines = extraction_result.split('\n')
            
            for line in lines:
                if line.startswith("FACTS:"):
                    facts = line.replace("FACTS:", "").strip()
                    if facts and facts != "[]":
                        memory_id = self.memory_client.remember_fact(
                            key=f"conversation_fact_{len(stored_memories)}",
                            fact=facts,
                            tags={"extracted", "conversation"}
                        )
                        stored_memories.append(("fact", facts, memory_id))
                        stored_count += 1
                
                elif line.startswith("PREFERENCES:"):
                    prefs = line.replace("PREFERENCES:", "").strip()
                    if prefs and prefs != "[]":
                        memory_id = self.memory_client.remember_preference(
                            key=f"conversation_pref_{len(stored_memories)}",
                            preference=prefs
                        )
                        stored_memories.append(("preference", prefs, memory_id))
                        stored_count += 1
                
                elif line.startswith("SKILLS:"):
                    skills = line.replace("SKILLS:", "").strip()
                    if skills and skills != "[]":
                        memory_id = self.memory_client.remember_skill(
                            key=f"conversation_skill_{len(stored_memories)}",
                            skill_description=skills,
                            tags={"extracted", "conversation"}
                        )
                        stored_memories.append(("skill", skills, memory_id))
                        stored_count += 1
                
                elif line.startswith("CODE_PATTERNS:"):
                    code = line.replace("CODE_PATTERNS:", "").strip()
                    if code and code != "[]":
                        memory_id = self.memory_client.remember(
                            key=f"conversation_code_{len(stored_memories)}",
                            content=code,
                            memory_type="code_pattern",
                            tags={"extracted", "conversation", "code"}
                        )
                        stored_memories.append(("code_pattern", code, memory_id))
                        stored_count += 1
        
        return {
            "extracted_memories": stored_memories,
            "stored_count": stored_count
        }