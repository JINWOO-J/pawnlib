#!/bin/bash

# 기본 설정
CONTAINER_NAME="${CONTAINER_NAME:-pawnlib_tmp}"
IMAGE_NAME="jinwoo/pawnlib"
LOG_FILE="/tmp/pawnlib_docker.log"
HOST_MOUNT_DIR="$(pwd)"
CONTAINER_MOUNT_DIR="/mount"
BACKGROUND_MODE=0
LOG_TO_FILE=0
SHOW_HELP=0

# 색상 설정
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m' # No Color

# 로그 함수
log() {
    local message="$1"
    echo -e "[${GREEN}INFO${NC}] $message"
    if [[ $LOG_TO_FILE -eq 1 ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $message" >> "$LOG_FILE" || {
            echo -e "[${RED}ERROR${NC}] Failed to write to log file: $LOG_FILE" >&2
        }
    fi
}

error() {
    local message="$1"
    echo -e "[${RED}ERROR${NC}] $message" >&2
    if [[ $LOG_TO_FILE -eq 1 ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $message" >> "$LOG_FILE" 2>/dev/null
    fi
    exit 1
}

# 도움말 출력
usage() {
    cat << EOF
${YELLOW}Usage:${NC} $0 [options]
${YELLOW}Options:${NC}
  -d    Run container in background mode (detached)
  -l    Enable logging to file ($LOG_FILE)
  -h    Show this help message
EOF
}

# 사전 점검
check_requirements() {
    command -v docker >/dev/null 2>&1 || error "Docker is not installed or not in PATH"
    [[ -w "$(dirname "$LOG_FILE")" ]] || error "Log directory is not writable"
}

# 옵션 파싱
while getopts "dlh" opt; do
    case "$opt" in
        d) BACKGROUND_MODE=1 ;;
        l) LOG_TO_FILE=1 ;;
        h) SHOW_HELP=1 ;;
        ?) usage; exit 1 ;;
    esac
done

# 도움말 출력 후 종료
if [[ $SHOW_HELP -eq 1 ]]; then
    usage
    exit 0
fi

# 로그 디렉토리 생성
if [[ $LOG_TO_FILE -eq 1 ]]; then
    mkdir -p "$(dirname "$LOG_FILE")" || error "Failed to create log directory"
fi

# 사전 점검 실행
check_requirements

# 최신 이미지 가져오기
log "Pulling the latest Docker image: $IMAGE_NAME..."
docker pull "$IMAGE_NAME" || error "Failed to pull Docker image!"

# 종료 시 컨테이너 자동 삭제
trap 'docker rm -f "$CONTAINER_NAME" 2>/dev/null; log "Container $CONTAINER_NAME removed"' EXIT

# 실행 모드 결정
if [[ $BACKGROUND_MODE -eq 1 ]]; then
    log "Running container in background mode..."
    docker run -d --rm --name "$CONTAINER_NAME" \
        -v "$HOST_MOUNT_DIR:$CONTAINER_MOUNT_DIR" \
        --tmpfs /tmp \
        --read-only \
        "$IMAGE_NAME" || error "Failed to start container in background mode!"
    log "Container started in detached mode. Use 'docker logs $CONTAINER_NAME' to check logs."
else
    log "Running container interactively..."
    docker run -it --rm --name "$CONTAINER_NAME" \
        -v "$HOST_MOUNT_DIR:$CONTAINER_MOUNT_DIR" \
        --tmpfs /tmp \
        --read-only \
        "$IMAGE_NAME" bash || error "Failed to start container interactively!"
fi