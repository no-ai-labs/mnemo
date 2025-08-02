# 🧠 Mnemo

LangChain-powered Universal Memory System for AI Assistants  
Advanced memory orchestration with optional LangGraph workflows.

A modern memory system built on LangChain with ChromaDB, designed to work seamlessly with AI assistants like Cursor. Features sophisticated memory management, RAG capabilities, and optional advanced workflows with LangGraph.

## 🚀 Features

- **🔗 LangChain-Powered**: Built on LangChain for seamless integration
- **🧠 Vector Memory**: ChromaDB-based semantic memory with embeddings
- **🤖 Flexible Embeddings**: Choose from multiple embedding models:
  - Qwen3-Embedding-0.6B (lightweight, M3 optimized)
  - E5-Large (high quality, multilingual)
  - OpenAI (if API key available)
- **⛓️ Memory Chains**: Pre-built LangChain chains for memory-enhanced conversations
- **🛠️ LangChain Tools**: Memory tools for agents and complex workflows
- **📊 LangGraph Support**: Optional advanced workflows for complex scenarios
- **🎯 RAG Capabilities**: Retrieval-Augmented Generation with memory
- **🏷️ Rich Metadata**: Type-safe memory with tags, scopes, and priorities
- **🔌 MCP Compatible**: Full Model Context Protocol integration for Cursor

## 🏃 Quick Start

### Installation

```bash
# Create conda environment
conda create -n mnemo python=3.11 -y
conda activate mnemo

# Basic installation
pip install -e .

# With optional dependencies
pip install -e ".[graph]"  # For LangGraph workflows
pip install -e ".[all]"    # Everything included

# For MCP support with Cursor
pip install -e ".[mcp]"
```

### Basic Usage

```python
from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient

# Create memory system
vector_store = MnemoVectorStore(
    collection_name="my_memories",
    persist_directory="./memory_db"
)
client = MnemoMemoryClient(vector_store)

# Set context
client.set_context(workspace_path="/my/project")

# Remember something
memory_id = client.remember_fact(
    key="project_goal",
    fact="Build an awesome AI assistant with LangChain",
    tags={"project", "goals", "langchain"}
)

# Search memories (semantic search with embeddings)
results = client.search("AI assistant", limit=5)
print(f"Found {len(results)} related memories")

# Recall most relevant
content = client.recall("What is the project goal?")
print(f"Goal: {content}")
```

### CLI Usage

```bash
# Remember a fact
mnemo remember "project_structure" "LangChain app with FastAPI backend" --memory-type "fact" --tags "architecture,langchain"

# Search memories (semantic search)
mnemo search "LangChain" --memory-types "fact,skill" --limit 5

# Store code patterns
mnemo code-pattern "fastapi_basic" "from fastapi import FastAPI; app = FastAPI()" "python" "Basic FastAPI setup"

# Get workspace context
mnemo workspace-context "/my/project"

# Get statistics
mnemo stats
```

## 🔧 Memory Types

- **Facts**: Static information and knowledge
- **Skills**: Learned patterns and techniques  
- **Preferences**: User preferences and settings
- **Conversations**: Chat history and context
- **Context**: Contextual information
- **Code Patterns**: Reusable code snippets and templates
- **Workspace**: Workspace-specific data
- **Project**: Project-specific information

## 🎯 Memory Scopes

- **Global**: Available everywhere
- **Workspace**: Available in current workspace
- **Project**: Available in current project
- **Session**: Available in current session
- **Temporary**: Auto-expires

## 🤖 Embedding Models

Mnemo supports multiple embedding models for different use cases:

### Recommended Models
- **Qwen3-Embedding-0.6B** ⭐: Best for M3/M2 Macs, lightweight (2GB), 100+ languages
- **intfloat/multilingual-e5-large**: High quality, 1024 dims, 3GB memory
- **paraphrase-multilingual-mpnet-base-v2**: Balanced performance, 768 dims

### Configuration
```python
# Use Qwen3 (default, lightweight)
from mnemo.core.embeddings import MnemoEmbeddings
embeddings = MnemoEmbeddings()  # Uses Qwen3-0.6B by default

# Use E5-Large (higher quality)
embeddings = MnemoEmbeddings(
    sentence_transformer_model="intfloat/multilingual-e5-large"
)

# Use OpenAI (requires API key)
embeddings = MnemoEmbeddings(
    use_mock=False,  # Force OpenAI if available
    openai_api_key="your-key"
)
```

## 🔌 MCP Integration (Cursor)

### Quick Setup 🚀
1. Start the MCP server:
```bash
# Run in a terminal
python -m mnemo.mcp.cli serve-fastapi
# or
python -m mnemo.mcp.fastapi_server
```

2. Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "mnemo": {
      "url": "http://localhost:3333/mcp"
    }
  }
}
```

3. Restart Cursor and use:
```
@mnemo remember "project_info" "This is a FastAPI project with PostgreSQL"
@mnemo recall "project info"
```

📚 **Detailed guides for beginners:**
- [한국어 가이드](docs/CURSOR_MCP_GUIDE_KR.md) - Cursor 초보자를 위한 완벽 가이드
- [English Guide](docs/CURSOR_MCP_GUIDE_EN.md) - Complete guide for Cursor beginners

## 🏗️ Architecture

```
┌─────────────────┐
│ LangChain Tools │  ← Agents & workflows
│ Memory Chains   │
├─────────────────┤
│ Memory Client   │  ← High-level API
├─────────────────┤
│ Vector Store    │  ← LangChain integration
│ (ChromaDB)      │
├─────────────────┤
│ Embeddings      │  ← Semantic search
│ (OpenAI/Custom) │
└─────────────────┘

Optional:
┌─────────────────┐
│ LangGraph       │  ← Advanced workflows
│ Workflows       │
└─────────────────┘
```

## 🔗 LangChain Integration

### Memory Chains

```python
from langchain_openai import ChatOpenAI
from mnemo.chains.memory import MemoryChain

llm = ChatOpenAI()
memory_chain = MemoryChain(llm=llm, memory_client=client)

result = memory_chain({"query": "How do I use LangChain?"})
print(result["response"])  # Enhanced with relevant memories
```

### RAG Chains

```python
from mnemo.chains.rag import MemoryRAGChain

rag_chain = MemoryRAGChain(llm=llm, memory_client=client)
result = rag_chain({"question": "Show me FastAPI examples"})
```

### Memory Tools for Agents

```python
from langchain.agents import initialize_agent, AgentType
from mnemo.tools.memory import MemorySearchTool, MemoryStoreTool

tools = [
    MemorySearchTool(memory_client=client),
    MemoryStoreTool(memory_client=client)
]

agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
response = agent.run("Search for Python examples and store any new patterns you find")
```

### LangGraph Workflows (Optional)

```python
from mnemo.graph.memory_graph import MemoryWorkflowGraph

workflow = MemoryWorkflowGraph(llm=llm, memory_client=client)
result = workflow.run(
    query="Help me understand LangChain",
    should_learn=True  # Learn from this conversation
)
```

## 📁 Project Structure

```
mnemo/
├── core/            # Core types and utilities
│   ├── types.py     # Memory types and models
│   └── embeddings.py # Custom embeddings
├── memory/          # Memory system
│   ├── store.py     # Vector store wrapper
│   └── client.py    # High-level client
├── chains/          # LangChain chains
│   ├── memory.py    # Memory-enhanced chains
│   └── rag.py       # RAG implementations
├── tools/           # LangChain tools
│   └── memory.py    # Memory tools for agents
├── graph/           # LangGraph workflows (optional)
│   └── memory_graph.py
├── cli.py           # Command line interface
└── examples/        # Usage examples
```

## 🎮 Examples

Check out the `examples/` directory for detailed usage examples:

- `basic_langchain.py`: Basic LangChain-based memory operations
- `langchain_chains.py`: Memory chains and RAG examples  
- `langchain_tools.py`: Tools and agents with memory
- `langgraph_workflow.py`: Advanced LangGraph workflows (optional)

## 🗺️ Roadmap

### Phase 1: MCP Integration 🔌
- [ ] MCP server implementation
- [ ] Cursor memory assistance integration
- [ ] Real-time memory sync
- [ ] Context injection for Cursor

### Phase 2: Multi-Vector DB Support 🗄️
- [x] ChromaDB (Current)
- [ ] Qdrant integration
- [ ] Pinecone support
- [ ] Weaviate adapter
- [ ] Abstract vector store interface

### Phase 3: Knowledge Graph Support 🕸️
- [ ] RDF/SPARQL support
- [ ] Neo4j integration
- [ ] Graph-based memory relationships
- [ ] Hybrid vector + graph search

### Phase 4: Advanced Features 🚀
- [ ] Multi-modal memories (images, audio)
- [ ] Distributed memory sync
- [ ] Memory compression & optimization
- [ ] Fine-tuned embeddings for specific domains

## 🔧 Development

### Requirements
- Python 3.11+
- ChromaDB (default vector store)
- OpenAI API key (optional, for embeddings)

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=mnemo
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

Apache License 2.0 - see LICENSE file for details.

---

Built with ❤️ for the AI assistant community