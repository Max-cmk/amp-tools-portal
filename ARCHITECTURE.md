# 📦 AMP Tools Portal - 구성 요소

## 🎯 포탈의 주요 기능

### 1. 홈 페이지 (카드 기반 UI)
- 모든 도구가 카드 형태로 표시
- 각 카드에 도구 아이콘, 이름, 설명 표시
- **클릭 가능한 인터랙션**
  - "ℹ️ 정보" 버튼: 도구 설명 확인
  - "▶ 실행" 버튼: 도구 즉시 실행

### 2. 도구 실행 페이지
- 선택한 도구가 전체 화면에서 실행됨
- **항상 상단에 "⬅ 돌아가기" 버튼 표시**
  - 클릭하면 포탈 홈으로 복귀
  - 도구 상태는 초기화됨

### 3. 포탈 관리 기능 (하단의 "⚙️ 관리자 설정")
- **도구 설명 수정**
  - 드롭다운에서 도구 선택
  - 설명 텍스트 직접 수정
  - "💾 설명 저장" 버튼으로 저장
  - 변경사항은 즉시 적용

- **도구 추가**
  - Python 파일 업로드
  - 도구 키(영문), 아이콘, 이름, 설명 입력
  - "➕ 도구 추가" 클릭하면 자동으로 추가

---

## 📁 파일 설명

### 핵심 파일

#### `portal.py` (포탈 메인 파일)
```python
- home() : 홈 페이지 렌더링
- run()  : 도구 실행 페이지 렌더링
- 세션 상태 관리
- 메타데이터 저장/로드
```
**역할**: 포탈의 모든 UI와 로직을 담당

#### `tool_meta.json` (도구 메타데이터)
```json
{
  "도구키": {
    "icon": "이모지",
    "title": "도구 이름",
    "desc": "도구 설명",
    "file": "파일명.py"
  }
}
```
**역할**: 각 도구의 정보를 저장 (포탈에서 자동으로 수정됨)

#### `core/loader.py` (도구 로더)
```python
load_tool(name, path) : Python 파일을 동적으로 로드
```
**역할**: 도구 .py 파일을 실행 중에 로드

#### `tools/*.py` (각 도구)
```python
def main(): 
    # 도구의 Streamlit 코드
```
**역할**: 각 도구의 실제 기능 구현

### 배포 파일

#### `requirements.txt` (Python 의존성)
```
streamlit>=1.28.0
numpy
matplotlib
pandas
scipy
librosa
soundfile
```
**역할**: 필요한 Python 라이브러리 명시

#### `Dockerfile` (Docker 이미지)
```dockerfile
- Python 3.10 기반 이미지
- 시스템 의존성 설치
- Python 라이브러리 설치
- 포탈 코드 복사
- Streamlit 서버 실행
```
**역할**: Docker 컨테이너 이미지 정의

#### `docker-compose.yml` (Docker 실행 설정)
```yaml
services:
  amp-portal:
    - 포트 8501로 공개
    - 데이터 볼륨 마운트 (도구, 메타데이터 유지)
    - 자동 재시작 설정
```
**역할**: Docker 컨테이너 실행 관리

#### `deploy.sh` (자동 배포 스크립트)
```bash
1. 시스템 요구사항 확인 (Docker)
2. 포트 확인
3. 디렉토리 구조 검증
4. 백업 생성
5. 이미지 빌드 및 컨테이너 시작
6. 헬스 체크
```
**역할**: 한 줄 명령어로 전체 배포

#### `.streamlit/config.toml` (Streamlit 설정)
```toml
[theme] : 포탈 색상 및 테마
[client] : 클라이언트 설정
[server] : 서버 포트/보안 설정
```
**역할**: Streamlit 포탈의 동작 및 외관 설정

### 문서

#### `README.md` (상세 설명서)
- 설치 방법
- 사용 가이드
- 도구 개발 가이드
- 문제 해결
- 외부 배포 방법

#### `QUICKSTART.md` (빠른 시작)
- 5분 안에 시작하기
- 주요 명령어
- 도구 추가 방법
- 문제 해결

---

## 🔄 작동 흐름

### 사용자 관점

```
포탈 시작
    ↓
[홈 화면] 도구 카드들 표시
    ↓
사용자 "▶ 실행" 클릭
    ↓
[도구 화면] 도구가 전체 화면에서 실행
    ↓
사용자 "⬅ 돌아가기" 클릭
    ↓
[홈 화면] 으로 복귀
```

### 관리자 관점

```
포탈 시작
    ↓
[홈 화면] 하단의 "⚙️ 관리자 설정" 펼치기
    ↓
┌─────────────────────────┐
│ 도구 설명 수정          │
│ → 도구 선택             │
│ → 설명 수정             │
│ → 저장                  │
└─────────────────────────┘
        ↓
┌─────────────────────────┐
│ 도구 추가               │
│ → 파일 업로드           │
│ → 정보 입력             │
│ → 추가                  │
└─────────────────────────┘
        ↓
[홈 화면] 새 도구 표시
```

---

## 🚀 배포 흐름

### Docker 배포 (권장)

```
사용자가 deploy.sh 실행
    ↓
요구사항 검증 (Docker, 포트 등)
    ↓
데이터 백업 생성
    ↓
Docker 이미지 빌드
    ↓
컨테이너 시작
    ↓
포탈 http://localhost:8501에서 실행
    ↓
24/7 상시 운영 (자동 재시작)
```

### 로컬 개발

```
사용자가 pip install -r requirements.txt 실행
    ↓
Python 라이브러리 설치
    ↓
streamlit run portal.py 실행
    ↓
포탈이 개발 모드로 시작
```

---

## 💾 데이터 흐름

### 메타데이터 저장

```
포탈에서 도구 설명 수정
    ↓
st.button() 클릭 감지
    ↓
meta[도구키]["desc"] 업데이트
    ↓
save_meta() 함수 호출
    ↓
JSON을 tool_meta.json에 저장
    ↓
다음 접속 시 새로운 설명 표시
```

### 도구 파일 저장

```
포탈에서 새 도구 파일 업로드
    ↓
파일 데이터를 바이트로 읽음
    ↓
tools/ 디렉토리에 저장
    ↓
메타데이터 생성 및 저장
    ↓
홈 화면에 새 도구 카드 표시
```

---

## 🔐 보안 고려사항

### 현재 포탈의 보안 수준
- ✅ 로컬 파일 시스템 기반 (보안 적절함)
- ✅ Docker 컨테이너로 격리
- ⚠️ 인증 미구현 (로컬 네트워크용)
- ⚠️ 입력 검증 최소화

### 외부 공개할 경우 추가 필요사항
- [ ] 사용자 인증 추가 (Streamlit Secrets)
- [ ] HTTPS/SSL 인증서 설정
- [ ] 업로드 파일 검증 강화
- [ ] 리소스 제한 (CPU, 메모리)
- [ ] 접근 로깅

---

## 📊 포탈 메타데이터 구조

```json
{
  "a4_audio": {
    "icon": "🎵",
    "title": "A4 오디오 분석",
    "desc": "오디오 파일의 A4 주파수 대역을 분석하고 시각화합니다.",
    "file": "a4_audio.py"
  }
}
```

**필드 설명:**
- `icon`: 도구를 나타내는 이모지 (선택 가능)
- `title`: 사용자 친화적 도구 이름
- `desc`: 도구 설명 (포탈에서 수정 가능)
- `file`: 도구 Python 파일명 (자동 설정)

---

## 🛠️ 도구 개발 가이드

### 최소한의 도구 구조

```python
# tools/my_tool.py
import streamlit as st

def main():
    st.title("My Tool")
    st.write("Tool content here")

if __name__ == "__main__":
    main()
```

### 완전한 도구 예제

```python
# tools/advanced_tool.py
import streamlit as st
import pandas as pd

def main():
    st.title("Advanced Tool")
    
    # 세션 상태 사용
    if "count" not in st.session_state:
        st.session_state.count = 0
    
    # UI 요소
    st.write(f"Count: {st.session_state.count}")
    if st.button("Increment"):
        st.session_state.count += 1
    
    # 파일 업로드
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)

if __name__ == "__main__":
    main()
```

---

## 🎨 UI 스타일

### 포탈 색상 테마 (GitHub Dark)

```css
primaryColor: #58a6ff      /* 밝은 파란색 (강조) */
backgroundColor: #0d1117   /* 검은색 (배경) */
secondaryBackgroundColor: #161b22  /* 진회색 (카드) */
textColor: #e6edf3         /* 밝은 회색 (텍스트) */
```

### 카드 스타일

```css
카드 크기: 280px (고정)
그리드: 자동 3열
간격: 1.5rem
호버 효과: 색상 변화 + 아래로 이동
전환: 0.3s (부드러운 애니메이션)
```

---

## 📈 확장 가능성

포탈은 다음과 같이 확장할 수 있습니다:

- [ ] **사용자 인증**: 각 사용자별 도구 접근 권한 관리
- [ ] **도구 버전 관리**: 여러 버전의 도구 저장 및 선택
- [ ] **실행 이력**: 도구 실행 기록 저장 및 통계
- [ ] **도구 카테고리**: 도구를 카테고리별로 분류
- [ ] **공유 기능**: 포탈 설정 및 도구 내보내기/가져오기
- [ ] **웹훅**: 외부 시스템과의 연동
- [ ] **API**: REST API를 통한 프로그래밍 인터페이스

---

## 📞 지원

더 자세한 정보:
- `README.md`: 상세 설명서 및 문제 해결
- `QUICKSTART.md`: 빠른 시작 가이드
- 로그 확인: `docker-compose logs -f`

---

**마지막 업데이트: 2026년 7월 2일**
