from setuptools import setup, find_packages

setup(
    name="mnemo",
    version="0.2.0",
    description="LangChain-powered Universal Memory System for AI Assistants",
    author="DevHub Team",
    author_email="contact@devhub.com",
    packages=find_packages(),
    python_requires=">=3.11",
        install_requires=[
        "langchain>=0.1.0",
        "langchain-community>=0.0.10", 
        "langchain-openai>=0.0.5",
        "langchain-huggingface>=0.1.0",
        "chromadb>=0.4.0",
        "pydantic>=2.0",
        "typer>=0.9.0",
        "rich>=13.0",
        "sqlite-utils>=3.0",
        "sentence-transformers>=2.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
        ],
        "graph": [
            "langgraph>=0.0.20",
            "langsmith>=0.0.80",
        ],
        "mcp": [
            "structlog>=23.0",
        ],
        "all": [
            "langgraph>=0.0.20",
            "langsmith>=0.0.80",
            "mcp>=1.0.0",
            "redis>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mnemo=mnemo.cli:main",
            "mnemo-mcp=mnemo.mcp.cli:app",
            "mnemo-mcp-stdio=mnemo.mcp.stdio:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)