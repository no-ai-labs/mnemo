# 🧠 Mnemo

**Memory Orchestration Layer for DAG-based Agents**

Mnemo is a memory architecture for AI agents, especially those powered by DAG-based orchestration frameworks like Mentat or Spice. It separates short-term, personalized memory from long-term, global knowledge using hybrid graph structures (Neo4j + RDF), and enables context-aware reasoning, knowledge promotion, and retrieval workflows.

---

## 🌌 Key Features

- 🧠 **Dual Memory Graphs**  
  - `Neo4j` for real-time, personalized DAG memory  
  - `Fuseki (RDF)` for long-term, structured semantic knowledge

- 🔁 **Flush Layer**  
  Translates ephemeral DAG state into structured RDF triples for persistent knowledge retention

- 📈 **Globalizer**  
  Detects frequently repeated user patterns and promotes them to `@global` namespace

- 🔸 **Namespace-Aware Knowledge Store**  
  Separates memory by `@user`, `@global`, and `@system` prefixes for clarity and traceability

- 🧊 **Vector Store Integration**  
  Embeds agent outputs, user utterances, and DAG episodes to enable similarity search and memory clustering using tools like Qdrant

---

## 🔧 Architecture Overview

```
              ┌───────────────┐
              │  DAG Engine  │
              └──────┬───────┘
                     │
        ┌───────────────────────────────┐
        │     Mnemo Flush Layer         │
        └───┬───────────────────┬───────┘
            │                   │
   ┌────────▼──────┐   ┌────────▼──────────┐
   │  Neo4j (RT)   │   │ RDF Store         │
   │  Short-term   │   │ (Fuseki / Lena)   │
   └───────────────┘   └───────────────┬───┘
                                      │
                              ┌───────▼────────┐
                              │ Globalizer     │
                              └───────────────┬┘
                                              │
                              ┌───────────────▼──────────────┐
                              │ Vector Store (e.g. Qdrant)    │
                              └──────────────────────────────┘
```

---

## 🧍️‍♂️ Memory Model

| Namespace   | Description                                      |
|-------------|--------------------------------------------------|
| `@user`     | Private user-specific memory (per session, per agent) |
| `@global`   | Promoted collective knowledge used as defaults   |
| `@system`   | DAG structure, execution flow, system-level artifacts |

---

## 📦 Modules (planned)

- `mnemo-core`: RDF/Neo4j abstraction, memory schema, triple ops
- `mnemo-flush`: Converts DAG outputs to triple structures
- `mnemo-globalizer`: Pattern detection & memory promotion
- `mnemo-api`: FastAPI endpoint for agent plugin / REST access
- `mnemo-vector`: Vector DB adapters, embedding pipeline, hybrid retrieval
- `examples/`: Mentat or Spice integration guides
- `docs/`: Memory model specs, SPARQL playground, query library

---

## 🥺 Example

```turtle
@prefix : <https://mnemo.noailabs.ai#> .

:user_joosung :prefers :GraphRAG .
:user_joosung :goal :UnifyMemory .
:GraphRAG :hasTrait "LowLatency" .

# After 3+ users express similar:
@global/GraphRAG :isPreferredBy [:joosung, :alice, :bob] .
```

---

## 🚀 Getting Started

Coming soon – first version of `mnemo-core` & flush-layer under construction.

---

## 📜 License

Apache-2.0

---

## ✨ Vision

Mnemo is not just a memory module.  
It’s a **temporal, semantic, identity-aware memory orchestration system** for LLM-powered agents in production.

Built to remember. Built to reason.

---

## 🧙‍♂️ Author

- [@joosunglee](https://github.com/no-ai-labs)  
  Founder of No AI Labs  
  DAG wizard, Memory engineer, GPT whisperer
