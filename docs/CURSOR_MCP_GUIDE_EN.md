# 🚀 Complete Guide: Connecting Cursor with Mnemo (For Beginners)

This guide provides a detailed walkthrough for beginners on how to connect Mnemo MCP server with Cursor!

## 📌 Table of Contents
1. [What is Cursor?](#what-is-cursor)
2. [What is MCP?](#what-is-mcp)
3. [Prerequisites](#prerequisites)
4. [Installing Mnemo](#installing-mnemo)
5. [Connecting Mnemo to Cursor](#connecting-mnemo-to-cursor)
6. [How to Use](#how-to-use)
7. [Troubleshooting](#troubleshooting)

---

## What is Cursor?

Cursor is an AI-integrated code editor. Built on VS Code, it features a built-in AI assistant to help with coding!

### Installing Cursor
1. Visit [https://cursor.sh](https://cursor.sh)
2. Download the version for your OS
3. Install and run

## What is MCP?

**MCP (Model Context Protocol)** enables AI assistants to communicate with external tools. 
Simply put, it's a bridge that allows Cursor's AI to use our Mnemo memory system!

## Prerequisites

### 1. Check Python Installation
Open a terminal and run:

```bash
python --version
# or
python3 --version
```

You need Python 3.11 or higher!

### 2. Check Git Installation
```bash
git --version
```

If you don't have Git, install from [https://git-scm.com](https://git-scm.com).

## Installing Mnemo

### 1. Create Project Folder
```bash
# Create folder in desired location
mkdir ~/my-projects
cd ~/my-projects
```

### 2. Clone Mnemo
```bash
git clone https://github.com/devhub/mnemo.git
cd mnemo
```

### 3. Create Python Virtual Environment

#### macOS/Linux:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

#### Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

### 4. Install Mnemo
```bash
# Basic installation
pip install -e .

# With MCP support (recommended)
pip install -e ".[mcp]"
```

### 5. Verify Installation
```bash
# Check if Mnemo is installed
mnemo --help

# Test MCP server
python -m mnemo.mcp.cli test-connection
```

## Connecting Mnemo to Cursor

### 1. Find Python Path
First, find the exact path to your Python executable:

```bash
# macOS/Linux
which python

# Windows
where python
```

Example output:
- macOS: `/Users/yourname/my-projects/mnemo/venv/bin/python`
- Windows: `C:\Users\yourname\my-projects\mnemo\venv\Scripts\python.exe`

**Copy this path! 📋**

### 2. Create Cursor Configuration File

#### Method 1: Create directly in Cursor
1. Open Cursor
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows) to open command palette
3. Type "Open Settings (JSON)" and select it
4. When settings file opens, create `mcp.json` in the same folder

#### Method 2: Create via terminal
```bash
# Navigate to Cursor settings folder
cd ~/.cursor  # macOS/Linux
# or
cd %USERPROFILE%\.cursor  # Windows

# Create mcp.json file
touch mcp.json  # macOS/Linux
# or
echo {} > mcp.json  # Windows
```

### 3. Configure mcp.json

Open `~/.cursor/mcp.json` and paste the following:

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "/Users/yourname/my-projects/mnemo/venv/bin/python",
      "args": ["-m", "mnemo.mcp.stdio"],
      "env": {
        "MNEMO_DB_PATH": "./cursor_memories",
        "MNEMO_COLLECTION": "my_ai_memories"
      }
    }
  }
}
```

**⚠️ Important! Replace "command" with your copied Python path!**

#### Windows Example:
```json
{
  "mcpServers": {
    "mnemo": {
      "command": "C:\\Users\\yourname\\my-projects\\mnemo\\venv\\Scripts\\python.exe",
      "args": ["-m", "mnemo.mcp.stdio"],
      "env": {
        "MNEMO_DB_PATH": "./cursor_memories",
        "MNEMO_COLLECTION": "my_ai_memories"
      }
    }
  }
}
```

### 4. Restart Cursor
You must fully restart Cursor to apply the settings!

1. Completely quit Cursor (`Cmd+Q` or `Alt+F4`)
2. Start Cursor again

### 5. Verify Connection
Open a new chat in Cursor and type:

```
@mnemo test
```

If you see something like "Mnemo MCP server is connected!", you're all set! 🎉

## How to Use

### 1. Store Memories
```
@mnemo remember "project_setup" "This project is a REST API using FastAPI and PostgreSQL"
```

### 2. Recall Memories
```
@mnemo recall "project setup"
```

### 3. Using in Conversations
```
You: @mnemo what was the tech stack for this project?
AI: Checking stored memories, this project is a REST API using FastAPI and PostgreSQL.
```

### 4. Advanced Usage

#### Adding Tags
```
@mnemo remember "api_endpoint" "POST /users - User creation endpoint" --tags "api,users,backend"
```

#### Search by Tags
```
@mnemo search --tags "api"
```

#### Project-specific Memories
```
@mnemo remember "config" "Dev DB is localhost:5432" --project "my-api"
```

## Troubleshooting

### 1. "mnemo: command not found" Error
- Check if Python virtual environment is activated
- Verify installation with `pip list | grep mnemo`

### 2. @mnemo Not Working in Cursor
- Verify Python path in mcp.json is correct
- Ensure Cursor was fully restarted
- Try running `python -m mnemo.mcp.stdio` directly in terminal

### 3. "No module named mnemo.mcp" Error
```bash
pip install -e ".[mcp]"
```

### 4. Permission Error (macOS/Linux)
```bash
chmod +x /path/to/python
```

### 5. ChromaDB Related Errors
```bash
# Reinstall ChromaDB
pip uninstall chromadb
pip install chromadb
```

## 💡 Pro Tips

### 1. Set Up Aliases
Add to `.bashrc` or `.zshrc`:
```bash
alias mnemo-cursor="cd ~/my-projects/mnemo && source venv/bin/activate"
```

### 2. Automatic Backup
Regularly backup memories:
```bash
cp -r ./cursor_memories ./cursor_memories_backup_$(date +%Y%m%d)
```

### 3. Reset Memories
Delete all memories and start fresh:
```bash
rm -rf ./cursor_memories
```

### 4. Debug Mode
For detailed logs when troubleshooting:
```json
{
  "mcpServers": {
    "mnemo": {
      "command": "/path/to/python",
      "args": ["-m", "mnemo.mcp.stdio", "--debug"],
      "env": {
        "MNEMO_DB_PATH": "./cursor_memories",
        "MNEMO_COLLECTION": "my_ai_memories",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 🎉 Congratulations!

You can now use Mnemo in Cursor! Your AI assistant can remember information about your projects and recall it when needed.

If you have questions, please open a GitHub issue!

---

**Happy Coding with Memory! 🧠✨**