"""LangGraph workflow for complex memory operations."""

try:
    from typing import Any, Dict, List, TypedDict
    from langgraph import StateGraph, END
    from langchain.schema import BaseLanguageModel
    
    from mnemo.memory.client import MnemoMemoryClient
    from mnemo.chains.memory import MemoryChain, MemoryLearningChain
    
    
    class MemoryWorkflowState(TypedDict):
        """State for memory workflow graph."""
        query: str
        response: str
        memories_used: List[Dict[str, Any]]
        extracted_memories: List[Any]
        should_learn: bool
        conversation_history: List[str]
    
    
    class MemoryWorkflowGraph:
        """
        LangGraph workflow for advanced memory operations.
        
        This graph handles complex memory workflows including:
        - Memory retrieval and response generation
        - Learning from conversations
        - Multi-step reasoning with memory
        """
        
        def __init__(
            self,
            llm: BaseLanguageModel,
            memory_client: MnemoMemoryClient
        ):
            self.llm = llm
            self.memory_client = memory_client
            
            # Initialize chains
            self.memory_chain = MemoryChain(llm, memory_client)
            self.learning_chain = MemoryLearningChain(llm, memory_client)
            
            # Build the graph
            self.graph = self._build_graph()
        
        def _build_graph(self) -> StateGraph:
            """Build the memory workflow graph."""
            
            # Create the graph
            workflow = StateGraph(MemoryWorkflowState)
            
            # Add nodes
            workflow.add_node("retrieve_and_respond", self._retrieve_and_respond)
            workflow.add_node("learn_from_conversation", self._learn_from_conversation)
            workflow.add_node("finalize_response", self._finalize_response)
            
            # Define the workflow
            workflow.set_entry_point("retrieve_and_respond")
            
            # Add conditional edges
            workflow.add_conditional_edges(
                "retrieve_and_respond",
                self._should_learn,
                {
                    True: "learn_from_conversation",
                    False: "finalize_response"
                }
            )
            
            workflow.add_edge("learn_from_conversation", "finalize_response")
            workflow.add_edge("finalize_response", END)
            
            return workflow.compile()
        
        def _retrieve_and_respond(self, state: MemoryWorkflowState) -> MemoryWorkflowState:
            """Retrieve memories and generate response."""
            
            result = self.memory_chain({"query": state["query"]})
            
            state["response"] = result["response"]
            state["memories_used"] = result["memories_used"]
            
            return state
        
        def _learn_from_conversation(self, state: MemoryWorkflowState) -> MemoryWorkflowState:
            """Learn from the conversation."""
            
            # Create conversation context
            conversation = f"Query: {state['query']}\nResponse: {state['response']}"
            
            # Add previous conversation history if available
            if state.get("conversation_history"):
                full_conversation = "\n".join(state["conversation_history"]) + "\n" + conversation
            else:
                full_conversation = conversation
            
            # Extract and store memories
            learning_result = self.learning_chain({"conversation": full_conversation})
            
            state["extracted_memories"] = learning_result["extracted_memories"]
            
            return state
        
        def _finalize_response(self, state: MemoryWorkflowState) -> MemoryWorkflowState:
            """Finalize the response."""
            
            # Add metadata about memory usage
            if state["memories_used"]:
                memory_info = f"\n\n[Used {len(state['memories_used'])} memories from knowledge base]"
                state["response"] += memory_info
            
            if state.get("extracted_memories"):
                learning_info = f"\n[Learned {len(state['extracted_memories'])} new things from this conversation]"
                state["response"] += learning_info
            
            return state
        
        def _should_learn(self, state: MemoryWorkflowState) -> bool:
            """Decide whether to learn from this conversation."""
            
            # Learn if explicitly requested or if it's a substantial conversation
            return (
                state.get("should_learn", False) or 
                len(state["query"]) > 50 or
                any(keyword in state["query"].lower() for keyword in [
                    "remember", "learn", "important", "note", "save"
                ])
            )
        
        def run(
            self,
            query: str,
            should_learn: bool = False,
            conversation_history: List[str] = None
        ) -> Dict[str, Any]:
            """Run the memory workflow."""
            
            initial_state = {
                "query": query,
                "response": "",
                "memories_used": [],
                "extracted_memories": [],
                "should_learn": should_learn,
                "conversation_history": conversation_history or []
            }
            
            final_state = self.graph.invoke(initial_state)
            
            return {
                "response": final_state["response"],
                "memories_used": final_state["memories_used"],
                "extracted_memories": final_state.get("extracted_memories", [])
            }

except ImportError:
    # LangGraph not available
    class MemoryWorkflowGraph:
        """Placeholder when LangGraph is not installed."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "LangGraph is required for MemoryWorkflowGraph. "
                "Install with: pip install 'mnemo[graph]'"
            )