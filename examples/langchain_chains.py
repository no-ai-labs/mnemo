"""Example using LangChain chains with Mnemo."""

import os
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.chains.memory import MemoryChain
from mnemo.chains.rag import MemoryRAGChain, CodePatternRAGChain


def main():
    """Demonstrate LangChain chains with Mnemo."""
    
    print("🔗 Mnemo LangChain Chains Example")
    print("=" * 40)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found. Using mock responses.")
        # For demo purposes, we'll create a mock LLM
        from langchain.llms.fake import FakeListLLM
        llm = FakeListLLM(responses=[
            "Based on the memories, I can help you with that topic.",
            "Here's what I found in the knowledge base about that.",
            "I've learned something new from our conversation."
        ])
    else:
        llm = ChatOpenAI(temperature=0.7, model="gpt-3.5-turbo")
    
    # Initialize Mnemo
    print("\n📦 Initializing Mnemo...")
    vector_store = MnemoVectorStore(
        collection_name="chains_example",
        persist_directory="./chains_db"
    )
    
    client = MnemoMemoryClient(vector_store)
    client.set_context(
        workspace_path="/examples/langchain_project",
        project_name="chains_demo"
    )
    
    # Populate with some initial memories
    print("\n📝 Populating with example memories...")
    
    client.remember_fact(
        key="langchain_definition",
        fact="LangChain is a framework for building applications with large language models",
        tags={"langchain", "llm", "framework"}
    )
    
    client.remember_skill(
        key="prompt_engineering",
        skill_description="Prompt engineering involves crafting effective prompts to get better results from LLMs",
        tags={"prompting", "llm", "techniques"}
    )
    
    client.remember_code_pattern(
        pattern_name="retrieval_chain",
        code="""
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

vectorstore = Chroma(embeddings=OpenAIEmbeddings())
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)
        """.strip(),
        language="python",
        description="Basic retrieval-augmented generation chain pattern",
        tags={"langchain", "retrieval", "qa", "rag"}
    )
    
    print("✅ Example memories stored!")
    
    # Demonstrate Memory Chain
    print("\n🔗 Testing Memory Chain...")
    memory_chain = MemoryChain(llm=llm, memory_client=client)
    
    result = memory_chain({"query": "What is LangChain and how can I use it?"})
    
    print("Query: What is LangChain and how can I use it?")
    print(f"Response: {result['response']}")
    print(f"Memories used: {len(result['memories_used'])}")
    
    # Demonstrate RAG Chain
    print("\n📚 Testing Memory RAG Chain...")
    rag_chain = MemoryRAGChain(llm=llm, memory_client=client, retrieval_k=3)
    
    rag_result = rag_chain({"question": "How do I implement retrieval-augmented generation?"})
    
    print("Question: How do I implement retrieval-augmented generation?")
    print(f"Answer: {rag_result['answer']}")
    print(f"Source memories: {len(rag_result['source_memories'])}")
    
    # Demonstrate Code Pattern RAG Chain
    print("\n🔧 Testing Code Pattern RAG Chain...")
    code_rag_chain = CodePatternRAGChain(llm=llm, memory_client=client)
    
    code_result = code_rag_chain({"question": "Show me how to create a retrieval chain in LangChain"})
    
    print("Question: Show me how to create a retrieval chain in LangChain")
    print(f"Answer: {code_result['answer']}")
    print(f"Code patterns used: {len(code_result['source_memories'])}")
    
    # Show detailed source information
    if code_result['source_memories']:
        print("\n📋 Source patterns used:")
        for i, memory in enumerate(code_result['source_memories'], 1):
            print(f"  {i}. [{memory['type']}] Similarity: {memory['similarity_score']:.3f}")
            print(f"     {memory['content'][:100]}...")
    
    # Demonstrate learning (if using real LLM)
    if os.getenv("OPENAI_API_KEY"):
        print("\n🧠 Testing Memory Learning...")
        from mnemo.chains.memory import MemoryLearningChain
        
        learning_chain = MemoryLearningChain(llm=llm, memory_client=client)
        
        sample_conversation = """
        User: I prefer using temperature 0.3 for code generation tasks
        Assistant: That's a good choice. Lower temperatures like 0.3 provide more deterministic outputs which is ideal for code generation.
        User: Also, I always use the 'stuff' chain type for my QA chains
        Assistant: The 'stuff' chain type is reliable for most QA use cases.
        """
        
        learning_result = learning_chain({"conversation": sample_conversation})
        
        print(f"Extracted {learning_result['stored_count']} new memories from conversation")
        
        if learning_result['extracted_memories']:
            print("Learned:")
            for mem_type, content, mem_id in learning_result['extracted_memories']:
                print(f"  • [{mem_type}] {content[:100]}...")
    
    print("\n✅ Chains example completed!")
    print("💾 Data persisted to: ./chains_db")


if __name__ == "__main__":
    main()