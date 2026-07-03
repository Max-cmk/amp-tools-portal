#!/bin/bash

# AMP Tools Portal 자동 배포 스크립트

set -e

echo "🚀 AMP Tools Portal 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️ $1${NC}"
}

# 시스템 확인
check_requirements() {
    log_info "시스템 요구사항 확인 중..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되어 있지 않습니다"
        exit 1
    fi
    
    log_success "Docker & Docker Compose 설치 확인됨"
}

# 포트 확인
check_port() {
    log_info "포트 8501 확인 중..."
    
    if netstat -tuln 2>/dev/null | grep -q ":8501 "; then
        log_error "포트 8501이 이미 사용 중입니다"
        exit 1
    fi
    
    log_success "포트 8501 사용 가능"
}

# 디렉토리 구조 확인
check_structure() {
    log_info "디렉토리 구조 확인 중..."
    
    required_files=("portal.py" "tool_meta.json" "requirements.txt" "Dockerfile" "docker-compose.yml")
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "필수 파일 누락: $file"
            exit 1
        fi
    done
    
    if [ ! -d "tools" ]; then
        log_error "tools 디렉토리가 없습니다"
        exit 1
    fi
    
    if [ ! -d "core" ]; then
        log_error "core 디렉토리가 없습니다"
        exit 1
    fi
    
    log_success "디렉토리 구조 확인됨"
}

# 백업 생성
create_backup() {
    log_info "백업 생성 중..."
    
    backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    cp -r tool_meta.json "$backup_dir/" 2>/dev/null || true
    cp -r tools "$backup_dir/" 2>/dev/null || true
    
    log_success "백업 생성됨: $backup_dir"
}

# Docker 이미지 빌드 및 실행
deploy() {
    log_info "Docker 이미지 빌드 중..."
    docker-compose build --no-cache
    
    log_success "Docker 이미지 빌드 완료"
    
    log_info "컨테이너 시작 중..."
    docker-compose up -d
    
    log_success "컨테이너 시작 완료"
    
    # 헬스 체크
    log_info "포탈이 시작되기를 기다리는 중 (약 30초)..."
    sleep 30
    
    if curl -s http://localhost:8501 > /dev/null; then
        log_success "포탈이 정상적으로 시작되었습니다"
    else
        log_error "포탈 헬스 체크 실패"
        docker-compose logs
        exit 1
    fi
}

# 배포 후 정보 출력
show_info() {
    echo ""
    echo "════════════════════════════════════════════"
    echo -e "${GREEN}🎉 배포 완료!${NC}"
    echo "════════════════════════════════════════════"
    echo ""
    echo "📍 포탈 주소: http://localhost:8501"
    echo ""
    echo "🛠️ 유용한 명령어:"
    echo "  - 로그 보기: docker-compose logs -f"
    echo "  - 컨테이너 중지: docker-compose down"
    echo "  - 컨테이너 재시작: docker-compose restart"
    echo "  - 상태 확인: docker-compose ps"
    echo ""
    echo "📚 더 많은 정보는 README.md를 참고하세요"
    echo "════════════════════════════════════════════"
}

# 메인 실행
main() {
    echo ""
    echo "╔═══════════════════════════════════════════╗"
    echo "║   AMP Tools Portal 배포 시스템           ║"
    echo "╚═══════════════════════════════════════════╝"
    echo ""
    
    check_requirements
    check_port
    check_structure
    create_backup
    deploy
    show_info
}

# 실행
main
