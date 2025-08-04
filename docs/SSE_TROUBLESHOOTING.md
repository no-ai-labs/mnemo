# SSE (Server-Sent Events) Troubleshooting Guide

## 문제 상황

회사 환경에서 MCP 서버가 "SSE 형식이 아니다"라는 오류와 함께 작동하지 않는 경우가 있습니다.
이는 주로 다음과 같은 원인으로 발생합니다:

1. **프록시/방화벽 설정**: 회사 네트워크가 SSE 연결을 차단
2. **HTTP 버전 차이**: HTTP/2가 SSE를 다르게 처리
3. **타임아웃 설정**: 긴 연결이 자동으로 끊김
4. **헤더 검증**: 엄격한 보안 정책이 SSE 헤더를 거부

## 해결 방법

### 1. Streamable 서버 사용 (권장)

새로운 StreamableHTTP 서버는 SSE와 일반 JSON 모드를 모두 지원합니다:

```bash
# 설치
pip install -r requirements.txt

# 서버 실행
python -m mnemo.mcp.cli serve-streamable --port 3334
```

### 2. 클라이언트 설정 수정

#### JSON 모드 강제 사용

클라이언트가 SSE 대신 JSON 모드를 사용하도록 설정:

```python
# Accept 헤더를 명시적으로 설정
headers = {
    "Accept": "application/json",  # SSE 대신 JSON 사용
    "Content-Type": "application/json"
}
```

#### 환경 변수 설정

```bash
export MNEMO_TRANSPORT=json  # SSE 비활성화
export MNEMO_TIMEOUT=30      # 타임아웃 증가
```

### 3. 프록시 우회

회사 프록시를 우회하여 직접 연결:

```bash
# 로컬호스트는 프록시 제외
export NO_PROXY=localhost,127.0.0.1,0.0.0.0
export no_proxy=localhost,127.0.0.1,0.0.0.0
```

### 4. 디버깅 방법

#### SSE 연결 테스트

```bash
# SSE 테스트 스크립트 실행
python test_sse_client.py
```

#### curl로 직접 테스트

```bash
# JSON 모드 테스트
curl -X POST http://localhost:3334/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# SSE 모드 테스트
curl -X POST http://localhost:3334/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
```

#### 로그 확인

```bash
# 서버 로그 확인
tail -f mnemo_server.log

# 네트워크 문제 확인
netstat -an | grep 3334
```

### 5. 대체 방법

#### A. 기본 FastAPI 서버 사용 (SSE 없음)

```bash
# 기존 FastAPI 서버 (SSE 미지원)
python -m mnemo.mcp.cli serve-fastapi --port 3333
```

#### B. 터널링 사용

```bash
# SSH 터널링 (회사 → 집)
ssh -L 3334:localhost:3334 your-home-server

# ngrok 사용 (주의: 보안 검토 필요)
ngrok http 3334
```

### 6. 회사별 특수 설정

#### A. 엔터프라이즈 프록시

```python
# 프록시 인증이 필요한 경우
import os
os.environ['HTTP_PROXY'] = 'http://user:pass@proxy.company.com:8080'
os.environ['HTTPS_PROXY'] = 'http://user:pass@proxy.company.com:8080'
```

#### B. 자체 서명 인증서

```python
# SSL 검증 비활성화 (개발 환경에서만)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

## 추가 도움말

### 증상별 해결책

| 증상 | 원인 | 해결책 |
|------|------|--------|
| "SSE 형식이 아니다" | 헤더 불일치 | Accept 헤더를 application/json으로 설정 |
| 연결 즉시 끊김 | 타임아웃 | Keep-alive 설정 및 타임아웃 증가 |
| 403 Forbidden | 보안 정책 | IT 부서에 SSE 허용 요청 |
| 연결 거부 | 방화벽 | 포트 변경 또는 터널링 사용 |

### 문의처

- GitHub Issues: https://github.com/yourusername/mnemo/issues
- 이메일: support@mnemo.dev

## 테스트 체크리스트

- [ ] 로컬에서 JSON 모드 작동 확인
- [ ] 로컬에서 SSE 모드 작동 확인  
- [ ] 회사 네트워크에서 JSON 모드 테스트
- [ ] 회사 네트워크에서 SSE 모드 테스트
- [ ] 프록시 설정 확인
- [ ] 방화벽 포트 확인