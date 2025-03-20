#!/bin/bash

# Default configurations
CONTAINER_NAME="${CONTAINER_NAME:-pawnlib_tmp}"
IMAGE_NAME="jinwoo/pawnlib"
LOG_FILE="/tmp/pawnlib_docker.log"
HOST_MOUNT_DIR="$(pwd)"
CONTAINER_MOUNT_DIR="/mount"
BACKGROUND_MODE=0
LOG_TO_FILE=0
SHOW_HELP=0
FORCE_PULL=1

# Color settings (ANSI escape codes as default)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if colors should be disabled (e.g., no TERM or tput unavailable)
if [[ -z "$TERM" ]] || ! command -v tput >/dev/null 2>&1 || [[ "$TERM" == "dumb" ]]; then
    GREEN=''
    RED=''
    YELLOW=''
    NC=''
fi

# Log functions
log() {
    local message="$1"
    echo -e "[${GREEN}INFO${NC}] $message"
    if [[ $LOG_TO_FILE -eq 1 ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $message" >> "$LOG_FILE" 2>/dev/null || {
            echo -e "[${RED}ERROR${NC}] Failed to write to log file: $LOG_FILE" >&2
            return 1
        }
    fi
}

error() {
    local message="$1"
    local exit_code="${2:-1}"
    echo -e "[${RED}ERROR${NC}] $message" >&2
    if [[ $LOG_TO_FILE -eq 1 ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $message" >> "$LOG_FILE" 2>/dev/null
    fi
    exit "$exit_code"
}

# Help message
usage() {
    cat << EOF
${YELLOW}Usage:${NC} $0 [options]
${YELLOW}Options:${NC}
  -d          Run container in background mode (detached)
  -l          Enable logging to file ($LOG_FILE)
  -c          Use cached image if available (disables default force pull)
  -n NAME     Set custom container name (default: $CONTAINER_NAME)
  -h          Show this help message
${YELLOW}Environment Variables:${NC}
  CONTAINER_NAME    Override default container name
  HOST_MOUNT_DIR    Override default host mount directory
EOF
}

# Check system requirements
check_requirements() {
    command -v docker >/dev/null 2>&1 || error "Docker is not installed or not in PATH"
    [[ -d "$HOST_MOUNT_DIR" ]] || error "Host mount directory does not exist: $HOST_MOUNT_DIR"
    [[ -w "$HOST_MOUNT_DIR" ]] || error "Host mount directory is not writable: $HOST_MOUNT_DIR"
    if [[ $LOG_TO_FILE -eq 1 ]]; then
        local log_dir
        log_dir=$(dirname "$LOG_FILE")
        [[ -w "$log_dir" ]] || error "Log directory is not writable: $log_dir"
    fi
}

# Cleanup function
cleanup() {
    if [[ $BACKGROUND_MODE -eq 0 ]] && docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
        docker rm -f "$CONTAINER_NAME" 2>/dev/null
        log "Container $CONTAINER_NAME removed"
    fi
}

# Parse command line options
while getopts "dlcn:h" opt; do
    case "$opt" in
        d) BACKGROUND_MODE=1 ;;
        l) LOG_TO_FILE=1 ;;
        c) FORCE_PULL=0 ;;
        n) CONTAINER_NAME="$OPTARG" ;;
        h) SHOW_HELP=1 ;;
        ?) usage; exit 1 ;;
    esac
done

# Show help and exit if requested
[[ $SHOW_HELP -eq 1 ]] && { usage; exit 0; }

# Create log directory if needed
if [[ $LOG_TO_FILE -eq 1 ]]; then
    mkdir -p "$(dirname "$LOG_FILE")" || error "Failed to create log directory"
fi

# Set trap for cleanup (only for interactive mode)
[[ $BACKGROUND_MODE -eq 0 ]] && trap 'cleanup' EXIT INT TERM

# Perform system checks
check_requirements

# Pull Docker image based on FORCE_PULL setting
if [[ $FORCE_PULL -eq 1 ]]; then
    log "Pulling the latest Docker image: $IMAGE_NAME..."
    docker pull "$IMAGE_NAME" || error "Failed to pull Docker image!"
elif docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    log "Using cached image: $IMAGE_NAME"
else
    log "No cached image found, pulling $IMAGE_NAME..."
    docker pull "$IMAGE_NAME" || error "Failed to pull Docker image!"
fi

# Check and handle existing container with confirmation
if docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo ""
    log "Container '$CONTAINER_NAME' already exists. Current status:"
    docker ps -a -f name="$CONTAINER_NAME"
    echo ""
    echo -e "${YELLOW}WARNING:${NC} This will remove the existing container '$CONTAINER_NAME'."
    echo ""
    read -p "Do you want to proceed and remove it? (y/n): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Aborted by user. Container '$CONTAINER_NAME' was not removed."
    fi
    log "Removing existing container '$CONTAINER_NAME'..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || error "Failed to remove existing container '$CONTAINER_NAME'"
    log "Existing container '$CONTAINER_NAME' removed"
fi

# Common docker run options
DOCKER_OPTIONS=(
    "--name" "$CONTAINER_NAME"
    "-v" "$HOST_MOUNT_DIR:$CONTAINER_MOUNT_DIR"
    "--tmpfs" "/tmp"
)

# Run container based on mode
if [[ $BACKGROUND_MODE -eq 1 ]]; then
    log "Running container in background mode..."
    docker run -d "${DOCKER_OPTIONS[@]}" --entrypoint tail "$IMAGE_NAME" -f /dev/null || {
        error "Failed to start container in background mode! The image might not have 'tail' installed."
    }
    log "Container started in detached mode with tail -f /dev/null"
    log "Use 'docker exec -it $CONTAINER_NAME bash' to access the container"
    log "Use 'docker stop $CONTAINER_NAME' to stop the container"
else
    log "Running container interactively..."
    docker run -it --rm "${DOCKER_OPTIONS[@]}" "$IMAGE_NAME" bash || 
        error "Failed to start container interactively! The image might not have 'bash' installed."
fi