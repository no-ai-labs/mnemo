"""Example using LangGraph workflow with Mnemo (optional)."""

import os

try:
    from langchain.chat_models import ChatOpenAI
    from mnemo.memory.store import MnemoVectorStore
    from mnemo.memory.client import MnemoMemoryClient
    from mnemo.graph.memory_graph import MemoryWorkflowGraph
    
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def main():
    """Demonstrate LangGraph workflow with Mnemo."""
    
    print("📊 Mnemo LangGraph Workflow Example")
    print("=" * 40)
    
    if not LANGGRAPH_AVAILABLE:
        print("⚠️  LangGraph is not installed.")
        print("Install with: pip install 'mnemo[graph]'")
        print("This example requires LangGraph for advanced workflows.")
        return
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found.")
        print("This example requires an OpenAI API key.")
        print("Set OPENAI_API_KEY environment variable and try again.")
        return
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0.7, model="gpt-3.5-turbo")
    
    # Initialize Mnemo
    print("\n📦 Initializing Mnemo...")
    vector_store = MnemoVectorStore(
        collection_name="workflow_example",
        persist_directory="./workflow_db"
    )
    
    client = MnemoMemoryClient(vector_store)
    client.set_context(
        workspace_path="/examples/workflow_project",
        project_name="langgraph_demo"
    )
    
    # Populate with initial knowledge
    print("\n📝 Populating with initial knowledge...")
    
    client.remember_fact(
        key="langgraph_purpose",
        fact="LangGraph is a library for building stateful, multi-actor applications with LLMs",
        tags={"langgraph", "stateful", "multi-actor"}
    )
    
    client.remember_skill(
        key="graph_design",
        skill_description="Design graphs by defining nodes (functions) and edges (connections) to create complex workflows",
        tags={"langgraph", "design", "workflow"}
    )
    
    client.remember_code_pattern(
        pattern_name="simple_graph",
        code="""
from langgraph import StateGraph, END

def node_function(state):
    # Process state
    return updated_state

graph = StateGraph(StateSchema)
graph.add_node("process", node_function)
graph.set_entry_point("process")
graph.add_edge("process", END)
app = graph.compile()
        """.strip(),
        language="python",
        description="Basic LangGraph pattern with state management",
        tags={"langgraph", "graph", "state", "basic"}
    )
    
    # Initialize workflow graph
    print("\n📊 Creating memory workflow graph...")
    workflow_graph = MemoryWorkflowGraph(llm=llm, memory_client=client)
    
    # Test basic workflow
    print("\n🔄 Testing basic workflow...")
    result1 = workflow_graph.run(
        query="What is LangGraph and how do I use it?",
        should_learn=False
    )
    
    print("Query: What is LangGraph and how do I use it?")
    print(f"Response: {result1['response']}")
    print(f"Memories used: {len(result1['memories_used'])}")
    
    # Test workflow with learning
    print("\n🧠 Testing workflow with learning...")
    result2 = workflow_graph.run(
        query="I prefer using conditional edges in my graphs because they make the workflow more dynamic",
        should_learn=True,
        conversation_history=[
            "User: I'm learning about LangGraph",
            "Assistant: Great! LangGraph is excellent for building stateful applications."
        ]
    )
    
    print("Query: I prefer using conditional edges in my graphs because they make the workflow more dynamic")
    print(f"Response: {result2['response']}")
    print(f"Memories used: {len(result2['memories_used'])}")
    print(f"New memories learned: {len(result2['extracted_memories'])}")
    
    if result2['extracted_memories']:
        print("Learned:")
        for mem_type, content, mem_id in result2['extracted_memories']:
            print(f"  • [{mem_type}] {content[:100]}...")
    
    # Test complex workflow
    print("\n🔧 Testing complex technical workflow...")
    result3 = workflow_graph.run(
        query="Show me a code example of using conditional edges in LangGraph",
        should_learn=False
    )
    
    print("Query: Show me a code example of using conditional edges in LangGraph")
    print(f"Response: {result3['response']}")
    print(f"Code patterns retrieved: {len([m for m in result3['memories_used'] if m['type'] == 'code_pattern'])}")
    
    # Show workflow benefits
    print("\n✨ Workflow Benefits Demonstrated:")
    print("  1. ✅ Automated memory retrieval based on query")
    print("  2. ✅ Intelligent learning from conversations")
    print("  3. ✅ Contextual response generation")
    print("  4. ✅ Multi-step reasoning with memory")
    print("  5. ✅ Stateful conversation handling")
    
    # Show final statistics
    print("\n📊 Final memory statistics...")
    stats = client.get_stats()
    print(f"Total memories: {stats['total_count']}")
    print(f"Memory types: {stats.get('type_counts', {})}")
    
    # Search for preferences to show learning worked
    print("\n🔍 Checking learned preferences...")
    preferences = client.search(
        query="conditional edges preference",
        memory_types=["preference"],
        limit=5
    )
    
    if preferences:
        print("✅ Successfully learned user preferences:")
        for pref in preferences:
            print(f"  • {pref['content'][:100]}...")
    
    print("\n✅ LangGraph workflow example completed!")
    print("💾 Data persisted to: ./workflow_db")


if __name__ == "__main__":
    main()