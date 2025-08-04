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
- **🔍 Cross-Project Context Storage**: Build knowledge graphs across multiple projects
- **🛡️ Minimal Guardrails for Vibe Coding**: Prevent duplicate implementations and maintain consistency
- **🤖 Auto-Tracking**: Automatically tracks Git activities, code changes, and chat sessions
- **📈 Code Intelligence**: Analyze patterns, find duplicates, check quality across projects

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
# Run in a terminal (FastAPI mode - recommended)
python -m mnemo.mcp.cli serve-fastapi

# NEW: Streamable mode with SSE support (for better compatibility)
python -m mnemo.mcp.cli serve-streamable --port 3334

# Alternative: stdio mode for direct MCP protocol
python -m mnemo.mcp.cli serve-stdio
```

**💡 SSE Troubleshooting**: If you encounter "Not SSE format" errors in corporate environments, use the streamable server or see [SSE Troubleshooting Guide](docs/SSE_TROUBLESHOOTING.md).

2. Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "mnemo": {
      "url": "http://localhost:3333/mcp",
      "env": {
        "MNEMO_AUTO_TRACKING": "true",
        "MNEMO_TRACKING_INTERVAL": "300",
        "MNEMO_SESSION_TRACKING": "true"
      }
    },
    "mnemo-streamable": {
      "url": "http://localhost:3334/mcp",
      "env": {
        "MNEMO_AUTO_TRACKING": "true",
        "MNEMO_TRANSPORT": "streamable"
      }
    }
  }
}
```

3. Restart Cursor and start using mnemo!

### 📱 Available MCP Tools

After installation, these tools are available in Cursor:

#### Memory Tools
- **remember**: Store information with semantic memory
- **recall**: Retrieve the most relevant memory
- **search**: Search through all memories
- **forget**: Delete specific memories
- **remember_code_pattern**: Store reusable code patterns
- **session_status**: View current session tracking status

#### Code Intelligence Tools (NEW!)
- **analyze_project**: Build knowledge graph of any project
  - Supports Python, Kotlin, JavaScript, TypeScript
  - Depth levels: `basic`, `deep`, `complete` (default: complete)
  - Example: `analyze_project("/path/to/project", "project-name", "python")`
- **find_pattern**: Find similar code patterns across projects
  - Uses semantic search to find related patterns
  - Example: `find_pattern("authentication", "project-name")`
- **compare_projects**: Compare coding patterns between projects
  - Finds common patterns and differences
  - Example: `compare_projects("project1", "project2")`
- **check_guardrails**: Analyze code quality and detect issues
  - Returns health score (0-100) with percentage-based metrics
  - Checks: duplicates, unused code, complexity, consistency
  - Example: `check_guardrails("project-name")`

### 🔍 Auto-Tracking Features (NEW!)

#### Project Tracking
Mnemo automatically tracks and remembers:
- **Git commits**: New commits are automatically saved
- **Code changes**: Significant code modifications are tracked  
- **Branch switches**: Branch changes are recorded
- **File status**: Working directory changes are monitored

#### Session Tracking
Mnemo also tracks your chat sessions:
- **Important messages**: Messages with keywords like 'implement', 'fix', 'todo' are highlighted
- **Session summaries**: Automatically saves conversation summaries every 20 messages
- **Tool usage**: Tracks when and how you use mnemo tools

Configuration:
- `MNEMO_AUTO_TRACKING`: Enable/disable project tracking (default: "true")
- `MNEMO_TRACKING_INTERVAL`: Tracking interval in seconds (default: 300)
- `MNEMO_SESSION_TRACKING`: Enable/disable session tracking (default: "true")

📚 **Detailed guides for beginners:**
- [한국어 가이드](docs/CURSOR_MCP_GUIDE_KR.md) - Cursor 초보자를 위한 완벽 가이드
- [English Guide](docs/CURSOR_MCP_GUIDE_EN.md) - Complete guide for Cursor beginners

## 🔍 Cross-Project Context & Code Intelligence (NEW!)

### Why Cross-Project Context?

When AI assistants like Cursor work on multiple projects, they often "vibe code" - creating duplicate implementations, using different libraries for the same features, or ignoring existing patterns. Mnemo solves this with **knowledge graphs** that capture and reuse patterns across all your projects.

### 🛡️ Code Guardrails - Health Check for Your Codebase

Mnemo's Code Guardrails analyze your project and provide a health score based on percentage metrics:

#### Health Score System (0-100)
- **🌟 85-100**: Excellent code quality
- **👍 70-84**: Good, minor improvements needed  
- **🤔 50-69**: Fair, room for improvement
- **⚠️ 30-49**: Warning, several issues need attention
- **😱 0-29**: Critical, major refactoring needed

#### What We Check

**1. Duplicate Implementations** (중복 구현)
- Finds functions with same names in different modules
- Example: `"You already have CustomError in errors.py!"`
- Penalty based on duplicate rate (% of total functions)

**2. Unused Functions** (미사용 함수)
- Detects dead code that's never called
- Helps maintain a clean, efficient codebase
- Penalty based on unused rate (% of total functions)

**3. Complexity Hotspots** (복잡도 핫스팟)
- Identifies overly complex files and functions
- Highlights areas that need refactoring
- Progressive penalty for high complexity

**4. Consistency Issues** (일관성 문제)
- Detects style drift and pattern violations
- Example: `"Keep using snake_case like the rest of the codebase"`
- Checks module size consistency

**5. Potential Risks** (잠재적 위험)
- Security issues and dangerous patterns
- High penalty (10 points each) for critical risks

**6. DSL Pattern Analysis** (Kotlin)
- Tracks underused DSL patterns
- Helps identify experimental or abandoned features

#### Usage

```bash
# Check project health
mcp check-guardrails <project-name>

# Example output:
# Health Score: 97/100 🌟 Excellent!
# - Duplicate rate: 2.1%
# - Unused rate: 5.2%
# - Issue density: 0.9
```

Real-world Results:
- **Spice Framework (Kotlin)**: 97/100 🌟 (2.1% duplicates, 5.2% unused)
- **Mnemo (Python)**: 75/100 👍 (37.7% duplicates, 47.2% unused)

### 📊 Code Knowledge Graph with Neo4j

Build a searchable graph of your codebase:

```bash
# Start Neo4j
docker-compose -f docker-compose/docker-compose.yml up -d

# Analyze a Python project (Complete Analysis)
from mnemo.graph.complete_python_analyzer import CompletePythonAnalyzer

analyzer = CompletePythonAnalyzer()
results = analyzer.analyze_complete("./my-project", "my-project-name", ["all"])

# Analyze a Kotlin project  
from mnemo.graph.complete_kotlin_analyzer import CompleteKotlinAnalyzer

analyzer = CompleteKotlinAnalyzer()
results = analyzer.analyze_complete("./kotlin-project", "project-name", ["all"])

# Check code health
from mnemo.graph.code_guardrails import CodeGuardrails

guardrails = CodeGuardrails()
health = guardrails.analyze_project_health("my-project-name")
print(f"Health Score: {health['health_score']}/100")
```

### 🌍 Multi-Language Support

Currently supported:
- **Python** (.py) - Full AST analysis, function calls, imports
- **Kotlin** (.kt) - Classes, functions, Gradle modules
- **JavaScript/TypeScript** (.js/.ts/.jsx/.tsx) - ES6/CommonJS, Vue/React components
- **More coming soon**: Java, Go, Rust, C++

### 🔄 Real-World Example

```python
# Analyze multiple projects
from mnemo.graph.project_context_manager import ProjectContextManager

manager = ProjectContextManager()

# Analyze your Spring Boot backend
manager.analyze_project("/path/to/spring-app", "spring-app", "java")

# Analyze your React frontend  
manager.analyze_project("/path/to/react-app", "react-app", "javascript")

# Later, when working on a new FastAPI project:
# "Create REST endpoints like my Spring Boot project"
patterns = manager.get_pattern_from_project("spring-app", "RestController")
# → AI references actual Spring patterns and adapts them to FastAPI!
```

### 🎯 Key Benefits

1. **Pattern Reuse**: "Use the same auth pattern as project X"
2. **Consistency**: Maintain coding standards across projects
3. **Knowledge Transfer**: Learn from your best implementations
4. **No More Vibe Coding**: AI understands your actual code, not just vibes

### 🤖 MCP Integration

All code intelligence features are exposed as MCP tools:

```python
# In Cursor, you can directly call:
# - analyze_project(project_path, project_name, language)
# - find_pattern(pattern, project)
# - compare_projects(project1, project2)
# - check_guardrails(project, checks)
```

No need for manual scripts - Cursor can use these tools automatically!

### 📈 What Gets Tracked

- **Function/Method calls** - Who calls whom
- **Class hierarchies** - Inheritance and interfaces  
- **Dependencies** - What imports what
- **Patterns** - Common architectural patterns
- **Cross-references** - How projects relate

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

### Phase 1: MCP Integration 🔌 ✅
- [x] MCP server implementation
- [x] Cursor memory assistance integration
- [x] Real-time memory sync
- [x] Context injection for Cursor
- [x] Auto-tracking (Git, code changes, sessions)
- [x] Code intelligence tools via MCP

### Phase 2: Multi-Vector DB Support 🗄️
- [x] ChromaDB (Current)
- [ ] Qdrant integration
- [ ] Pinecone support
- [ ] Weaviate adapter
- [ ] Abstract vector store interface

### Phase 3: Knowledge Graph Support 🕸️ ✅
- [ ] RDF/SPARQL support
- [x] Neo4j integration
- [x] Graph-based memory relationships
- [x] Code knowledge graphs
- [x] Cross-project pattern analysis
- [x] Vibe coding guardrails
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