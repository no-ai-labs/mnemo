# 🔌 Mnemo MCP Integration with Cursor

This guide shows how to integrate Mnemo's MCP server with Cursor for persistent memory capabilities.

## 📋 Prerequisites

1. Install Mnemo with MCP support:
```bash
pip install -e ".[mcp]"
```

2. Make sure you have Cursor installed

## 🚀 Setup Steps

### 1. Configure Cursor's MCP Settings

Add Mnemo to your Cursor's MCP configuration:

**Option A: Global Configuration**
Add to `~/.cursor/config/mcp.json`:

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "python",
      "args": ["-m", "mnemo.mcp.stdio"],
      "env": {
        "MNEMO_DB_PATH": "~/.cursor/mnemo_db",
        "MNEMO_COLLECTION": "cursor_memories"
      }
    }
  }
}
```

**Option B: Project-specific Configuration**
Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "python",
      "args": ["-m", "mnemo.mcp.stdio"],
      "env": {
        "MNEMO_DB_PATH": "./project_memories",
        "MNEMO_COLLECTION": "project_cursor_memories"
      }
    }
  }
}
```

### 2. Test the Connection

Run the MCP test server:
```bash
mnemo-mcp serve --port 3333
```

In another terminal, test the connection:
```bash
mnemo-mcp test-connection
```

### 3. Using Mnemo in Cursor

Once configured, you can use Mnemo's memory features directly in Cursor:

#### Store memories:
```
@mnemo remember "api_endpoint" "The main API runs on port 8000"
```

#### Recall memories:
```
@mnemo recall "api endpoint"
```

#### Search memories:
```
@mnemo search "database configuration"
```

#### Store code patterns:
```
@mnemo remember_code_pattern "fastapi_basic" "from fastapi import FastAPI; app = FastAPI()" "python" "Basic FastAPI setup"
```

## 🎯 Advanced Usage

### Context-aware Memory

Mnemo automatically tracks your workspace and project context:

```python
# Memories are automatically tagged with:
# - Current workspace path
# - Active project name
# - Session ID
```

### Memory Types

Different memory types for different purposes:
- `fact` - Static information
- `skill` - Learned techniques
- `preference` - User preferences
- `code_pattern` - Reusable code snippets

### Using Memory in Prompts

Cursor can access stored memories when generating code:

```
Generate a FastAPI endpoint using the patterns I've stored
```

## 🛠️ Troubleshooting

### Check MCP Server Status
```bash
# View logs (written to stderr)
tail -f ~/.cursor/logs/mcp-mnemo.log
```

### Reset Memory Database
```bash
# Remove the database directory
rm -rf ~/.cursor/mnemo_db
```

### Debug Mode
Set environment variable for verbose logging:
```json
{
  "mcpServers": {
    "mnemo": {
      "command": "python",
      "args": ["-m", "mnemo.mcp.stdio"],
      "env": {
        "MNEMO_DB_PATH": "~/.cursor/mnemo_db",
        "MNEMO_COLLECTION": "cursor_memories",
        "MNEMO_DEBUG": "true"
      }
    }
  }
}
```

## 🎉 Example Workflow

1. **Start a new project**
   ```
   @mnemo remember "project_type" "FastAPI microservice with PostgreSQL"
   ```

2. **Store API patterns**
   ```
   @mnemo remember_code_pattern "crud_endpoint" "..." "python" "CRUD endpoint pattern"
   ```

3. **Later, use stored knowledge**
   ```
   Generate a new endpoint based on my stored CRUD pattern
   ```

4. **Check what Mnemo knows**
   ```
   @mnemo search "project"
   ```

Now Cursor has persistent memory across sessions! 🧠✨