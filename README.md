# 🧰 AMP Tools Portal

AMP Tools Portal은 모든 오디오 및 데이터 분석 도구를 한 곳에서 관리하고 실행할 수 있는 통합 포탈입니다.

## 📋 기능

### 홈 페이지
- **카드 기반 UI**: 모든 도구가 카드 형태로 표시됩니다
- **정보 보기**: 각 도구의 설명을 확인할 수 있습니다
- **빠른 실행**: "실행" 버튼으로 즉시 도구를 실행할 수 있습니다

### 도구 관리
- **설명 수정**: 포탈에서 직접 각 도구의 설명을 수정할 수 있습니다
- **도구 추가**: 새로운 Python 도구를 추가할 수 있습니다
- **메타데이터 관리**: 아이콘, 제목, 설명 등을 관리합니다

### 도구 실행
- **독립적 실행**: 각 도구는 Streamlit 기반으로 독립적으로 실행됩니다
- **뒤로가기**: 도구 실행 중 언제든 포탈 홈으로 돌아갈 수 있습니다
- **상시 운영**: 24/7 접근 가능합니다

---

## 🚀 설치 및 실행

### 방법 1: 로컬 실행

#### 요구사항
- Python 3.9+
- pip

#### 설치
```bash
pip install -r requirements.txt
```

#### 실행
```bash
streamlit run portal.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

---

### 방법 2: Docker로 실행 (권장 - 상시 운영)

#### 설치
```bash
docker-compose up -d
```

#### 중지
```bash
docker-compose down
```

#### 로그 확인
```bash
docker-compose logs -f
```

포탈은 `http://localhost:8501`에서 접근 가능합니다.

---

## 📁 파일 구조

```
amp-tools-portal/
├── portal.py                  # 메인 포탈 애플리케이션
├── tool_meta.json            # 도구 메타데이터
├── requirements.txt          # Python 의존성
├── Dockerfile                # Docker 이미지 정의
├── docker-compose.yml        # Docker Compose 설정
├── .streamlit/
│   └── config.toml          # Streamlit 설정
├── core/
│   └── loader.py            # 도구 로더 모듈
└── tools/
    ├── a4_audio.py          # A4 오디오 분석 도구
    ├── acoustic_shift.py    # 어쿠스틱 시뮬레이터
    ├── excursion.py         # 편차 분석기
    └── comparator.py        # 파일 비교도구
```

---

## ⚙️ 관리자 설정

### 도구 설명 수정
1. 포탈 하단의 "⚙️ 관리자 설정" 섹션을 펼칩니다
2. "도구 설명 수정" 탭에서 수정할 도구를 선택합니다
3. 설명을 입력하고 "💾 설명 저장"을 클릭합니다

### 도구 추가
1. "⚙️ 관리자 설정" 섹션의 "도구 추가" 탭을 확인합니다
2. 다음 정보를 입력합니다:
   - **Python 파일**: .py 파일 선택
   - **도구 키**: 영문 및 언더스코어만 사용 (예: `my_tool`)
   - **아이콘**: 이모지 선택 (예: 🧩)
   - **도구 이름**: 사용자 친화적 이름
   - **설명**: 도구에 대한 설명

3. "➕ 도구 추가" 버튼을 클릭합니다

---

## 🛠️ 도구 개발 가이드

새로운 도구를 추가하려면 다음 요구사항을 충족해야 합니다:

### Python 파일 요구사항
```python
# 예시: my_tool.py

import streamlit as st

def main():
    st.title("My Tool")
    st.write("도구 내용을 여기에 작성하세요")
    
    # 도구 로직
    # ...

if __name__ == "__main__":
    main()
```

**필수 조건:**
- `main()` 함수가 반드시 존재해야 합니다
- Streamlit 기반으로 작성되어야 합니다
- 모든 필요한 라이브러리는 `requirements.txt`에 추가되어야 합니다

---

## 🌐 외부 접근 (상시 운영)

### nginx를 통한 프록시 설정

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL 설정 (Let's Encrypt)
```bash
sudo certbot certonly --standalone -d your-domain.com
# nginx 설정에 SSL 인증서 경로 추가
```

---

## 🔒 보안 고려사항

포탈을 공개적으로 운영할 경우:

1. **인증 추가**: Streamlit Secrets를 사용한 인증 구현
2. **입력 검증**: 도구 업로드 시 파일 검증
3. **리소스 제한**: 업로드 파일 크기 제한 설정
4. **로깅**: 접근 기록 및 에러 로깅 활성화

---

## 📊 포탈 메타데이터 (tool_meta.json)

```json
{
  "tool_key": {
    "icon": "🎵",
    "title": "도구 이름",
    "desc": "도구 설명",
    "file": "tool_filename.py"
  }
}
```

---

## 💡 팁

### 로컬 테스트
```bash
# 포탈 실행
streamlit run portal.py

# 캐시 초기화 (필요시)
streamlit cache clear
```

### 도구 개발 중 빠른 테스트
```bash
# 도구를 직접 실행하여 테스트
streamlit run tools/my_tool.py
```

### 주기적 백업
```bash
# 메타데이터 및 도구 파일 백업
cp -r . backup_$(date +%Y%m%d)
```

---

## 🐛 문제 해결

### 포탈이 로드되지 않음
```bash
# 캐시 초기화
rm -rf ~/.streamlit/cache

# 포탈 재실행
streamlit run portal.py
```

### 도구 실행 시 에러
- `main()` 함수가 존재하는지 확인
- 필요한 라이브러리가 `requirements.txt`에 있는지 확인
- 파일 경로가 올바른지 확인

### Docker 컨테이너 문제
```bash
# 로그 확인
docker-compose logs -f amp-portal

# 컨테이너 재시작
docker-compose restart amp-portal

# 완전 재빌드
docker-compose up -d --build
```

---

## 📞 지원

문제가 발생하거나 기능 요청이 있으시면:
1. `docker-compose logs` 명령으로 로그 확인
2. Streamlit 캐시 초기화
3. 컨테이너/애플리케이션 재시작

---

## 라이센스

이 프로젝트는 내부 사용을 목적으로 합니다.

---

**마지막 업데이트**: 2026년 7월 2일
