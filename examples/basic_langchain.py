"""Basic LangChain-based Mnemo usage example."""

import os
from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.core.types import MemoryType, MemoryScope


def main():
    """Demonstrate basic LangChain-based Mnemo usage."""
    
    print("🧠 Mnemo LangChain Basic Usage Example")
    print("=" * 50)
    
    # Create vector store and client
    print("\n📦 Initializing Mnemo with ChromaDB...")
    vector_store = MnemoVectorStore(
        collection_name="example_memories",
        persist_directory="./example_db"
    )
    
    client = MnemoMemoryClient(vector_store)
    
    # Set context
    client.set_context(
        workspace_path="/path/to/my/langchain/project",
        project_name="awesome_langchain_app",
        session_id="session_123"
    )
    
    print("✅ Mnemo initialized!")
    
    # Store different types of memories
    print("\n📝 Storing memories...")
    
    # Store a fact
    fact_id = client.remember_fact(
        key="langchain_purpose",
        fact="LangChain is a framework for developing applications powered by language models",
        tags={"langchain", "definition", "framework"}
    )
    print(f"✅ Stored fact: {fact_id}")
    
    # Store a skill
    skill_id = client.remember_skill(
        key="chain_composition",
        skill_description="Chain composition allows you to combine multiple LangChain components into complex workflows",
        skill_data={
            "pattern": "chain1 | chain2 | chain3",
            "use_case": "Sequential processing",
            "benefits": ["Modularity", "Reusability", "Testability"]
        },
        tags={"langchain", "chains", "composition", "patterns"}
    )
    print(f"✅ Stored skill: {skill_id}")
    
    # Store a code pattern
    code_id = client.remember_code_pattern(
        pattern_name="simple_llm_chain",
        code="""
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

prompt = PromptTemplate(
    input_variables=["topic"],
    template="Tell me about {topic}"
)

llm = OpenAI(temperature=0.7)
chain = LLMChain(llm=llm, prompt=prompt)

result = chain.run(topic="artificial intelligence")
        """.strip(),
        language="python",
        description="Basic LLM chain pattern with prompt template",
        tags={"langchain", "llm", "chain", "basic"}
    )
    print(f"✅ Stored code pattern: {code_id}")
    
    # Store a preference
    pref_id = client.remember_preference(
        key="default_temperature",
        preference={"llm_temperature": 0.7, "max_tokens": 1000},
        scope="workspace"
    )
    print(f"✅ Stored preference: {pref_id}")
    
    # Search for memories
    print("\n🔍 Searching memories...")
    
    # Search for LangChain-related memories
    langchain_memories = client.search(
        query="LangChain framework",
        limit=5
    )
    
    print(f"Found {len(langchain_memories)} LangChain memories:")
    for i, memory in enumerate(langchain_memories, 1):
        print(f"  {i}. [{memory['type']}] {memory['content'][:100]}...")
        print(f"     Similarity: {memory['similarity_score']:.3f}")
    
    # Search for code patterns
    print("\n🔧 Searching for code patterns...")
    code_patterns = client.search(
        query="LLM chain",
        memory_types=["code_pattern"],
        limit=3
    )
    
    print(f"Found {len(code_patterns)} code patterns:")
    for pattern in code_patterns:
        print(f"  • {pattern['content'][:150]}...")
    
    # Search by tags
    print("\n🏷️ Searching by tags...")
    chain_memories = client.get_memories_by_tags(
        tags={"chains", "patterns"},
        limit=5
    )
    
    print(f"Found {len(chain_memories)} memories with chain/pattern tags:")
    for memory in chain_memories:
        print(f"  • [{memory['type']}] {memory['content'][:100]}...")
    
    # Get workspace context
    print("\n📁 Getting workspace context...")
    workspace_context = client.get_workspace_context()
    
    print("Workspace context summary:")
    for category, memories in workspace_context.items():
        print(f"  {category}: {len(memories)} items")
    
    # Get statistics
    print("\n📊 Memory statistics...")
    stats = client.get_stats()
    print(f"Total memories: {stats['total_count']}")
    print(f"Backend: {stats['backend']}")
    print(f"Memory types: {stats.get('type_counts', {})}")
    
    # Persist the data
    print("\n💾 Persisting data...")
    client.persist()
    
    print("\n✅ Example completed!")
    print(f"Data persisted to: ./example_db")


if __name__ == "__main__":
    main()