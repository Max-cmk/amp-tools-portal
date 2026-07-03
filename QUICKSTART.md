# 🚀 AMP Tools Portal - 빠른 시작 가이드

## 5분 안에 시작하기

### 1️⃣ Docker로 바로 실행 (가장 쉬운 방법)

```bash
# 배포 스크립트 실행 (자동으로 모든 것을 설정합니다)
chmod +x deploy.sh
./deploy.sh
```

✅ 완료! 브라우저에서 `http://localhost:8501` 열기

---

### 2️⃣ 수동 Docker Compose 실행

```bash
# Docker 이미지 빌드 및 실행
docker-compose up -d

# 상태 확인
docker-compose ps

# 로그 보기
docker-compose logs -f
```

✅ 포탈이 `http://localhost:8501`에서 실행 중입니다

---

### 3️⃣ 로컬 개발 환경에서 실행

```bash
# Python 의존성 설치
pip install -r requirements.txt

# 포탈 실행
streamlit run portal.py
```

✅ 포탈이 `http://localhost:8501`에서 열립니다

---

## 📚 포탈 사용법

### 홈 화면
- **카드 UI**: 모든 도구가 카드 형태로 표시됩니다
- **정보 보기**: 각 카드의 "ℹ️ 정보" 버튼으로 도구 설명 확인
- **실행**: "▶ 실행" 버튼으로 도구 바로 실행

### 도구 내부
- **뒤로가기**: 포탈 홈으로 돌아갑니다
- **상단의 뒤로가기 버튼**: "⬅ 돌아가기" 클릭

### 관리자 설정 (하단)

#### 📝 도구 설명 수정
1. "⚙️ 관리자 설정" 펼치기
2. 수정할 도구 선택
3. 설명 입력하고 "💾 설명 저장"

#### ➕ 새 도구 추가
1. "⚙️ 관리자 설정" 펼치기
2. Python 파일 선택
3. 도구 정보 입력
4. "➕ 도구 추가" 클릭

---

## 🛠️ 주요 명령어

### Docker 관리
```bash
# 포탈 시작
docker-compose up -d

# 포탈 중지
docker-compose down

# 포탈 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps
```

### Streamlit 개발
```bash
# 포탈 실행
streamlit run portal.py

# 캐시 초기화
streamlit cache clear

# 개별 도구 테스트
streamlit run tools/a4_audio.py
```

---

## 📁 파일 구조

```
amp-tools-portal/
├── portal.py              ← 메인 포탈
├── tool_meta.json         ← 도구 메타데이터 (자동 수정됨)
├── requirements.txt       ← Python 의존성
├── Dockerfile             ← Docker 이미지
├── docker-compose.yml     ← Docker 실행 설정
├── deploy.sh              ← 자동 배포 스크립트
├── README.md              ← 상세 설명서
├── .streamlit/config.toml ← Streamlit 설정
├── core/
│   └── loader.py          ← 도구 로더
└── tools/
    ├── a4_audio.py        ← A4 오디오 분석
    ├── acoustic_shift.py  ← 어쿠스틱 시뮬레이터
    ├── excursion.py       ← 편차 분석기
    └── comparator.py      ← 파일 비교도구
```

---

## 🔧 새 도구 추가 방법

### Step 1: Python 파일 준비
```python
# my_tool.py
import streamlit as st

def main():
    st.title("My Tool")
    st.write("도구 내용")
    # 도구 로직 구현

if __name__ == "__main__":
    main()
```

### Step 2: 포탈에서 추가
1. "⚙️ 관리자 설정" → "도구 추가"
2. 파일 선택 및 정보 입력
3. "➕ 도구 추가" 클릭

### Step 3: 자동으로 추가됨
- 도구가 홈 화면에 나타남
- 메타데이터가 자동 저장됨

---

## 🌐 서버에 배포 (상시 운영)

### Linux 서버에서 실행

```bash
# 1. 저장소 클론 또는 파일 업로드
git clone <repository> amp-tools-portal
cd amp-tools-portal

# 2. 배포 스크립트 실행
chmod +x deploy.sh
./deploy.sh

# 3. 자동으로 시작됨 (재부팅 후에도 자동 시작)
```

### 자동 재시작 설정 (systemd)

```bash
# /etc/systemd/system/amp-portal.service 생성
sudo vi /etc/systemd/system/amp-portal.service
```

```ini
[Unit]
Description=AMP Tools Portal
After=docker.service
Requires=docker.service

[Service]
Type=forking
WorkingDirectory=/path/to/amp-tools-portal
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable amp-portal
sudo systemctl start amp-portal

# 상태 확인
sudo systemctl status amp-portal
```

---

## 🆘 문제 해결

### 포탈이 열리지 않음
```bash
# Docker 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 재시작
docker-compose restart
```

### 포트 8501이 이미 사용 중
```bash
# 다른 포트 사용 (docker-compose.yml 수정)
ports:
  - "8080:8501"  # 8501 대신 8080 사용
```

### 도구가 실행되지 않음
- 도구에 `main()` 함수가 있는지 확인
- 필요한 라이브러리가 `requirements.txt`에 있는지 확인
- 포탈 재시작

---

## 💾 데이터 백업

```bash
# 메타데이터 및 도구 백업
cp tool_meta.json tool_meta.json.backup
cp -r tools tools.backup

# 자동 백업 스크립트
# crontab -e 에서 아래 추가:
0 2 * * * cd /path/to/amp-tools-portal && cp tool_meta.json backups/tool_meta_$(date +\%Y\%m\%d).json
```

---

## 📖 더 많은 정보

더 자세한 설명과 고급 기능은 `README.md`를 참고하세요.

---

## ✨ 특징 정리

✅ **누구나 접근 가능** - 웹 브라우저만 있으면 됨  
✅ **상시 운영** - Docker로 24/7 실행 가능  
✅ **포탈에서 수정 가능** - 도구 설명을 웹에서 바로 수정  
✅ **쉬운 배포** - 한 줄 명령어로 시작  
✅ **도구 추가 간편** - 클릭몇 번으로 새 도구 추가  
✅ **예쁜 UI** - 모던하고 사용자 친화적인 카드 디자인  

---

**행운을 빕니다! 🚀**

질문이나 문제가 있으면 README.md를 참고하세요.
