"""Example using LangChain tools with Mnemo."""

import os
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.tools.memory import MemoryTool, MemorySearchTool, MemoryStoreTool


def main():
    """Demonstrate LangChain tools with Mnemo."""
    
    print("🛠️ Mnemo LangChain Tools Example")
    print("=" * 40)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found.")
        print("This example requires an OpenAI API key to demonstrate agents.")
        print("Set OPENAI_API_KEY environment variable and try again.")
        
        # Show tool usage without agent
        print("\n🔧 Demonstrating tools directly...")
        
        # Initialize Mnemo
        vector_store = MnemoVectorStore(
            collection_name="tools_example",
            persist_directory="./tools_db"
        )
        client = MnemoMemoryClient(vector_store)
        
        # Create tools
        memory_tool = MemoryTool(memory_client=client)
        search_tool = MemorySearchTool(memory_client=client)
        store_tool = MemoryStoreTool(memory_client=client)
        
        # Store some memories
        print("\n📝 Storing memories with tools...")
        store_result = store_tool._run(
            key="example_fact",
            content="Python is a high-level programming language",
            memory_type="fact",
            tags="python,programming"
        )
        print(f"Store result: {store_result}")
        
        # Search memories
        print("\n🔍 Searching memories with tools...")
        search_result = search_tool._run(
            query="Python programming",
            memory_types="fact",
            limit=3
        )
        print(f"Search result: {search_result}")
        
        print("\n✅ Direct tool usage completed!")
        return
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
    
    # Initialize Mnemo
    print("\n📦 Initializing Mnemo...")
    vector_store = MnemoVectorStore(
        collection_name="agent_example",
        persist_directory="./agent_db"
    )
    
    client = MnemoMemoryClient(vector_store)
    client.set_context(
        workspace_path="/examples/agent_project",
        project_name="memory_agent_demo"
    )
    
    # Create memory tools
    print("\n🛠️ Creating memory tools...")
    memory_tools = [
        MemorySearchTool(memory_client=client),
        MemoryStoreTool(memory_client=client)
    ]
    
    # Initialize agent
    print("\n🤖 Initializing agent with memory tools...")
    agent = initialize_agent(
        tools=memory_tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    
    # Demonstrate agent usage
    print("\n🎯 Testing agent with memory operations...")
    
    # Store information
    print("\n1. Storing information via agent...")
    response1 = agent.run(
        "Store the fact that 'FastAPI is a modern Python web framework for building APIs' "
        "with the key 'fastapi_definition' and tags 'python,web,api'"
    )
    print(f"Agent response: {response1}")
    
    # Store code pattern
    print("\n2. Storing a code pattern...")
    response2 = agent.run(
        "Store a code pattern with key 'fastapi_basic' and content "
        "'from fastapi import FastAPI; app = FastAPI(); @app.get(\"/\"); def read_root(): return {\"Hello\": \"World\"}' "
        "with memory_type 'code_pattern' and tags 'fastapi,python,basic'"
    )
    print(f"Agent response: {response2}")
    
    # Search for information
    print("\n3. Searching for information...")
    response3 = agent.run(
        "Search for information about FastAPI and Python web frameworks"
    )
    print(f"Agent response: {response3}")
    
    # Complex query combining storage and retrieval
    print("\n4. Complex memory task...")
    response4 = agent.run(
        "First, search for any information about FastAPI. "
        "Then, if you find relevant information, store a preference that "
        "the user likes FastAPI for API development."
    )
    print(f"Agent response: {response4}")
    
    # Show memory statistics
    print("\n📊 Final memory statistics...")
    stats = client.get_stats()
    print(f"Total memories stored: {stats['total_count']}")
    print(f"Memory types: {stats.get('type_counts', {})}")
    
    # Show all memories
    print("\n📋 All stored memories:")
    all_memories = client.search(query="", limit=20, similarity_threshold=0.0)
    
    for i, memory in enumerate(all_memories, 1):
        print(f"  {i}. [{memory['type']}] {memory['content'][:100]}...")
        if memory['tags']:
            print(f"     Tags: {', '.join(memory['tags'])}")
    
    print("\n✅ Agent tools example completed!")
    print("💾 Data persisted to: ./agent_db")


if __name__ == "__main__":
    main()