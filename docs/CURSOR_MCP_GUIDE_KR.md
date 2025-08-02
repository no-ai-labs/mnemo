# 🚀 Cursor와 Mnemo 연동 완벽 가이드

이 가이드는 Cursor를 처음 사용하시는 분들을 위해 Mnemo MCP 서버를 연동하는 방법을 아주 자세히 설명합니다!

## 📌 목차
1. [Cursor란?](#cursor란)
2. [MCP란?](#mcp란)
3. [사전 준비사항](#사전-준비사항)
4. [Mnemo 설치하기](#mnemo-설치하기)
5. [Cursor에 Mnemo 연결하기](#cursor에-mnemo-연결하기)
6. [사용 방법](#사용-방법)
7. [문제 해결](#문제-해결)

---

## Cursor란?

Cursor는 AI가 통합된 코드 에디터입니다. VS Code를 기반으로 만들어졌지만, AI 어시스턴트가 내장되어 있어 코딩을 도와줍니다!

### Cursor 설치하기
1. [https://cursor.sh](https://cursor.sh) 접속
2. 운영체제에 맞는 버전 다운로드
3. 설치 후 실행

## MCP란?

**MCP (Model Context Protocol)**는 AI 어시스턴트가 외부 도구와 소통할 수 있게 해주는 프로토콜입니다. 
쉽게 말해, Cursor의 AI가 우리의 Mnemo 메모리 시스템을 사용할 수 있게 해주는 다리 역할을 합니다!

## 사전 준비사항

### 1. Python 설치 확인
터미널을 열고 다음 명령어를 실행해보세요:

```bash
python --version
# 또는
python3 --version
```

Python 3.11 이상이 설치되어 있어야 합니다!

### 2. Git 설치 확인
```bash
git --version
```

Git이 없다면 [https://git-scm.com](https://git-scm.com)에서 설치하세요.

## Mnemo 설치하기

### 1. 프로젝트 폴더 만들기
```bash
# 원하는 위치에 폴더 생성
mkdir ~/my-projects
cd ~/my-projects
```

### 2. Mnemo 클론하기
```bash
git clone https://github.com/devhub/mnemo.git
cd mnemo
```

### 3. Python 가상환경 만들기

#### macOS/Linux:
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate
```

#### Windows:
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

### 4. Mnemo 설치
```bash
# 기본 설치
pip install -e .

# MCP 지원 포함 설치 (권장)
pip install -e ".[mcp]"
```

### 5. 설치 확인
```bash
# Mnemo가 잘 설치되었는지 확인
mnemo --help

# MCP 서버 테스트
python -m mnemo.mcp.cli test-connection
```

## Cursor에 Mnemo 연결하기

### 1. Python 경로 찾기
먼저 Python 실행 파일의 정확한 경로를 찾아야 합니다:

```bash
# macOS/Linux
which python

# Windows
where python
```

출력 예시:
- macOS: `/Users/yourname/my-projects/mnemo/venv/bin/python`
- Windows: `C:\Users\yourname\my-projects\mnemo\venv\Scripts\python.exe`

**이 경로를 복사해두세요! 📋**

### 2. Cursor 설정 파일 만들기

#### 방법 1: Cursor 내에서 직접 만들기
1. Cursor 열기
2. `Cmd+Shift+P` (Mac) 또는 `Ctrl+Shift+P` (Windows) 눌러서 명령 팔레트 열기
3. "Open Settings (JSON)" 입력하고 선택
4. 설정 파일이 열리면, 같은 폴더에 `mcp.json` 파일 생성

#### 방법 2: 터미널에서 만들기
```bash
# Cursor 설정 폴더로 이동
cd ~/.cursor  # macOS/Linux
# 또는
cd %USERPROFILE%\.cursor  # Windows

# mcp.json 파일 생성
touch mcp.json  # macOS/Linux
# 또는
echo {} > mcp.json  # Windows
```

### 3. mcp.json 설정하기

`~/.cursor/mcp.json` 파일을 열고 다음 내용을 붙여넣으세요:

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

**⚠️ 중요! "command" 부분을 아까 복사한 Python 경로로 바꿔주세요!**

#### Windows 예시:
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

### 4. Cursor 재시작
설정을 적용하려면 Cursor를 완전히 종료했다가 다시 실행해야 합니다!

1. Cursor 완전히 종료 (`Cmd+Q` 또는 `Alt+F4`)
2. Cursor 다시 실행

### 5. 연결 확인
Cursor에서 새 채팅을 열고 다음과 같이 입력해보세요:

```
@mnemo test
```

"Mnemo MCP server is connected!" 같은 응답이 나오면 성공! 🎉

## 사용 방법

### 1. 기억 저장하기
```
@mnemo remember "project_setup" "이 프로젝트는 FastAPI와 PostgreSQL을 사용하는 REST API입니다"
```

### 2. 기억 검색하기
```
@mnemo recall "project setup"
```

### 3. 실제 대화에서 사용하기
```
나: @mnemo 이 프로젝트의 기술 스택이 뭐였지?
AI: 제가 저장된 기억을 확인해보니, 이 프로젝트는 FastAPI와 PostgreSQL을 사용하는 REST API 프로젝트입니다.
```

### 4. 고급 사용법

#### 태그 추가하기
```
@mnemo remember "api_endpoint" "POST /users - 사용자 생성 엔드포인트" --tags "api,users,backend"
```

#### 특정 태그로 검색
```
@mnemo search --tags "api"
```

#### 프로젝트별 기억 관리
```
@mnemo remember "환경설정" "개발 DB는 localhost:5432" --project "my-api"
```

## 문제 해결

### 1. "mnemo: command not found" 오류
- Python 가상환경이 활성화되어 있는지 확인
- `pip list | grep mnemo`로 설치 확인

### 2. Cursor에서 @mnemo가 작동하지 않음
- mcp.json의 Python 경로가 정확한지 확인
- Cursor를 완전히 재시작했는지 확인
- 터미널에서 `python -m mnemo.mcp.stdio` 직접 실행해보기

### 3. "No module named mnemo.mcp" 오류
```bash
pip install -e ".[mcp]"
```

### 4. 권한 오류 (macOS/Linux)
```bash
chmod +x /path/to/python
```

### 5. ChromaDB 관련 오류
```bash
# ChromaDB 재설치
pip uninstall chromadb
pip install chromadb
```

## 💡 Pro Tips

### 1. 별칭(Alias) 설정하기
`.bashrc` 또는 `.zshrc`에 추가:
```bash
alias mnemo-cursor="cd ~/my-projects/mnemo && source venv/bin/activate"
```

### 2. 자동 백업
정기적으로 메모리 백업하기:
```bash
cp -r ./cursor_memories ./cursor_memories_backup_$(date +%Y%m%d)
```

### 3. 메모리 초기화
모든 메모리 삭제하고 새로 시작:
```bash
rm -rf ./cursor_memories
```

### 4. 디버그 모드
문제가 있을 때 상세 로그 보기:
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

## 🎉 축하합니다!

이제 Cursor에서 Mnemo를 사용할 수 있습니다! AI 어시스턴트가 여러분의 프로젝트에 대한 정보를 기억하고, 필요할 때 불러올 수 있게 되었습니다.

궁금한 점이 있다면 GitHub 이슈로 문의해주세요!

---

**Happy Coding with Memory! 🧠✨**