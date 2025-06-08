#!/bin/bash
set -e

# 로깅을 위해 프로젝트 이름을 미리 파싱합니다.
PROJECT_NAME_ARG=$(echo "$@" | grep -oP '(?<=--project\s)\S+')
PROJECT_NAME="${PROJECT_NAME_ARG:-qcbm}"
LOG_FILE="/var/log/${PROJECT_NAME}-setup.log"

# 로깅 함수 정의
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

error_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "${LOG_FILE}"
}

success_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "${LOG_FILE}"
}

# --- 디버깅: EC2 사용자 데이터 컨텍스트 로깅 ---
log "==== 스크립트 실행 컨텍스트 디버깅 시작 ===="
log "수신된 인자 개수: $#"
log "모든 인자 (\$*): $*"
log "모든 인자 (\$@): $@"
log "--- 전체 환경 변수 목록 ---"
env | tee -a "${LOG_FILE}"
log "--- 디버깅 종료 ---"


# --- 인자 파싱 ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --instance-type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        --volume-size)
            VOLUME_SIZE="$2"
            shift 2
            ;;
        --git)
            GIT_REPO="$2"
            shift 2
            ;;
        --branch)
            GIT_BRANCH="$2"
            shift 2
            ;;
        --ssh-public-key)
            SSH_PUBLIC_KEY="$2"
            shift 2
            ;;
        --ssh-private-key)
            SSH_PRIVATE_KEY="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

PROJECT_NAME="${PROJECT_NAME:-qcbm}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.large}"
VOLUME_SIZE="${VOLUME_SIZE:-50}"
GIT_REPO="${GIT_REPO:-https://github.com/Q-BFD/QCBM-LSTM.git}"
GIT_BRANCH="${GIT_BRANCH:-automation}"

# --- SSH 키 처리 로직 ---
log "🚀 SSH 키를 처리합니다..."

# 환경 변수 이름의 대소문자 차이를 보완합니다.
if [ -z "${SSH_PRIVATE_KEY}" ] && [ -n "${SSHPrivateKey}" ]; then
    log "환경 변수 'SSHPrivateKey'에서 개인 키를 찾았습니다. 'SSH_PRIVATE_KEY'로 사용합니다."
    SSH_PRIVATE_KEY="${SSHPrivateKey}"
fi

if [ -z "${SSH_PRIVATE_KEY}" ]; then
    error_log "SSH 개인 키가 없습니다. --ssh-private-key 인자 또는 SSH_PRIVATE_KEY/SSHPrivateKey 환경 변수로 전달해주세요."
    exit 1
fi
success_log "SSH 개인 키를 성공적으로 로드했습니다."

log "🔏 제공된 개인 키에서 공개 키를 생성합니다..."
PRIVATE_KEY_FILE=$(mktemp)
echo -e "${SSH_PRIVATE_KEY}" > "${PRIVATE_KEY_FILE}"
chmod 600 "${PRIVATE_KEY_FILE}"

# ssh-keygen이 없으면 설치합니다. (openssh-server 패키지에 보통 포함됨)
if ! command -v ssh-keygen &> /dev/null; then
    log "ssh-keygen을 찾을 수 없어 openssh-client를 설치합니다..."
    apt-get update -qq && apt-get install -y -qq openssh-client
fi

# 공개 키를 생성합니다.
GENERATED_PUBLIC_KEY=$(ssh-keygen -y -f "${PRIVATE_KEY_FILE}")
rm -f "${PRIVATE_KEY_FILE}" # 임시 파일 삭제

if [ -z "${GENERATED_PUBLIC_KEY}" ]; then
    error_log "개인 키로부터 공개 키를 생성하는 데 실패했습니다. 개인 키가 유효한지 확인해주세요."
    exit 1
fi
SSH_PUBLIC_KEY="${GENERATED_PUBLIC_KEY}"
success_log "SSH 공개 키를 성공적으로 생성했습니다."


log "==== setup_full.sh 시작 ===="
log "🚀 Starting ${PROJECT_NAME} development environment setup..."
log "🧪 Instance Type: ${INSTANCE_TYPE} (CPU Testing)"
log "📂 Git Repository: ${GIT_REPO}"
log "🌿 Git Branch: ${GIT_BRANCH}"
log "💾 Checking initial disk space..."
df -h | tee -a "${LOG_FILE}"

log "📦 Updating system packages..."
for i in {1..3}; do
    if apt update; then
        success_log "System packages updated successfully"
        break
    else
        error_log "Failed to update packages (attempt ${i}/3)"
        sleep 10
    fi
done

log "📦 Installing basic packages..."
log "Installing git..."
apt install -y git && success_log "git installed successfully" || error_log "Failed to install git"
log "Installing docker.io..."
apt install -y docker.io && success_log "docker.io installed successfully" || error_log "Failed to install docker.io"
log "Installing python3-pip..."
apt install -y python3-pip && success_log "python3-pip installed successfully" || error_log "Failed to install python3-pip"
log "Installing awscli..."
apt install -y awscli && success_log "awscli installed successfully" || error_log "Failed to install awscli"
log "Installing basic tools..."
apt install -y curl wget unzip nodejs openssh-server jq htop vim nano && success_log "Basic tools installed" || error_log "Some basic tools failed"

log "💾 Checking disk space after package installation..."
df -h | tee -a "${LOG_FILE}"

log "💾 Starting enhanced EBS volume detection..."
get_block_devices() {
    lsblk -J -o NAME,SIZE,MOUNTPOINT,TYPE | jq -r '.blockdevices[] | "\(.name) \(.size) \(.mountpoint // "none") \(.type)"'
}

is_mounted() {
    local device="$1"
    mount | grep -q "^${device}"
}

EBS_DEVICE=""
EBS_SUCCESS=false

log "🔍 Strategy 1: Looking for NVMe devices around ${VOLUME_SIZE}GB..."
for attempt in {1..60}; do
    log "⏳ Attempt ${attempt}/60: Scanning for EBS volume..."
    log "📊 Current block devices:"
    lsblk | tee -a "${LOG_FILE}"
    
    for nvme_device in /dev/nvme*n1; do
        if [ -e "${nvme_device}" ]; then
            if ls "${nvme_device}p1" 1>/dev/null 2>&1; then
                target="${nvme_device}p1"
            else
                target="${nvme_device}"
            fi
            
            DEVICE_SIZE=$(lsblk -b -n -o SIZE "${nvme_device}" 2>/dev/null | head -1)
            if [ -n "${DEVICE_SIZE}" ]; then
                device_size_gb=$((DEVICE_SIZE / 1024 / 1024 / 1024))
                log "🔍 Found NVMe device ${target} with size: ${device_size_gb} GB"
                
                if [ "${device_size_gb}" -ge 48 ] && [ "${device_size_gb}" -le 52 ] && ! is_mounted "${target}"; then
                    if ! lsblk "${target}" | grep -q "/"; then
                        EBS_DEVICE="${target}"
                        success_log "Found EBS volume: ${EBS_DEVICE} (${device_size_gb} GB)"
                        EBS_SUCCESS=true
                        break 2
                    fi
                fi
            fi
        fi
    done
    
    if [ -z "${EBS_DEVICE}" ]; then
        log "🔍 Strategy 2: Looking for any unmounted ${VOLUME_SIZE}GB device..."
        while IFS= read -r line; do
            device_name=$(echo "${line}" | awk '{print $1}')
            device_size=$(echo "${line}" | awk '{print $2}')
            mount_point=$(echo "${line}" | awk '{print $3}')
            device_type=$(echo "${line}" | awk '{print $4}')
            
            if [ "${device_type}" = "disk" ] && [ "${mount_point}" = "none" ]; then
                if echo "${device_size}" | grep -E "(4[89]|5[0-2])(\.|G|$)"; then
                    full_device="/dev/${device_name}"
                    if [ -e "${full_device}" ] && ! is_mounted "${full_device}"; then
                        EBS_DEVICE="${full_device}"
                        success_log "Found EBS volume via strategy 2: ${EBS_DEVICE} (${device_size})"
                        EBS_SUCCESS=true
                        break 2
                    fi
                fi
            fi
        done < <(get_block_devices)
    fi
    
    if [ -z "${EBS_DEVICE}" ] && command -v aws >/dev/null 2>&1; then
        log "🔍 Strategy 3: Using AWS CLI to find attached volumes..."
        INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
        if [ -n "${INSTANCE_ID}" ]; then
            aws ec2 describe-volumes \
                --filters "Name=attachment.instance-id,Values=${INSTANCE_ID}" \
                --query 'Volumes[?Size==`'"${VOLUME_SIZE}"'`].Attachments[0].Device' \
                --output text 2>/dev/null | while read -r device; do
                if [ "${device}" != "None" ] && [ -n "${device}" ]; then
                    actual_device=$(echo "${device}" | sed 's/xvd/nvme/; s/f$/1n1/')
                    if [ -e "${actual_device}" ] && ! is_mounted "${actual_device}"; then
                        echo "${actual_device}" > /tmp/ebs_device
                        break
                    fi
                fi
            done
            
            if [ -f /tmp/ebs_device ]; then
                EBS_DEVICE=$(cat /tmp/ebs_device)
                rm -f /tmp/ebs_device
                if [ -n "${EBS_DEVICE}" ]; then
                    success_log "Found EBS volume via AWS CLI: ${EBS_DEVICE}"
                    EBS_SUCCESS=true
                    break
                fi
            fi
        fi
    fi
    
    if [ -z "${EBS_DEVICE}" ]; then
        log "⏳ No EBS volume found yet, waiting 10 seconds..."
        sleep 10
    fi
done

MOUNT_OK=false
if [ "${EBS_SUCCESS}" = "true" ] && [ -n "${EBS_DEVICE}" ]; then
    log "🔧 Setting up EBS volume: ${EBS_DEVICE}"
    mkdir -p /mnt/data
    if blkid "${EBS_DEVICE}" >/dev/null 2>&1; then
        EXISTING_FS=$(blkid -o value -s TYPE "${EBS_DEVICE}")
        log "📝 Device ${EBS_DEVICE} already has filesystem: ${EXISTING_FS}"
    else
        log "📝 Formatting ${EBS_DEVICE} with ext4..."
        if mkfs.ext4 -F "${EBS_DEVICE}"; then
            success_log "EBS volume formatted successfully"
        else
            error_log "Failed to format EBS volume"
            exit 1
        fi
    fi
    
    log "📌 Mounting ${EBS_DEVICE} to /mnt/data..."
    if mount "${EBS_DEVICE}" /mnt/data; then
        success_log "EBS volume mounted successfully"
        MOUNT_OK=true
        DEVICE_UUID=$(blkid -s UUID -o value "${EBS_DEVICE}")
        if [ -n "${DEVICE_UUID}" ]; then
            echo "UUID=${DEVICE_UUID} /mnt/data ext4 defaults,nofail 0 2" >> /etc/fstab
            log "📝 Added to fstab with UUID: ${DEVICE_UUID}"
        else
            echo "${EBS_DEVICE} /mnt/data ext4 defaults,nofail 0 2" >> /etc/fstab
            log "📝 Added to fstab with device path"
        fi
        
        chown ubuntu:ubuntu /mnt/data
        chmod 755 /mnt/data
        
        if df -h | grep -q "/mnt/data"; then
            MOUNT_SIZE=$(df -h /mnt/data | tail -1 | awk '{print $2}')
            success_log "EBS volume mount verified - Available space: ${MOUNT_SIZE}"
            
            log "🐳 Relocating Docker data directory to /mnt/data/docker..."
            systemctl stop docker 2>/dev/null || true
            mkdir -p /mnt/data/docker
            echo '{"data-root":"/mnt/data/docker","log-driver":"json-file","log-opts":{"max-size":"100m"}}' > /etc/docker/daemon.json
            systemctl daemon-reload
            
            if systemctl enable docker && systemctl start docker; then
                success_log "Docker reconfigured to use /mnt/data/docker"
                usermod -aG docker ubuntu
            else
                error_log "Failed to start Docker with new data-root"
            fi
        else
            error_log "Mount verification failed"
        fi
    else
        error_log "Failed to mount EBS volume ${EBS_DEVICE}"
        exit 1
    fi
else
    error_log "Could not find EBS volume after 60 attempts"
    exit 1
fi

if [ "${MOUNT_OK}" = true ]; then
    log "📁 Cloning repository from ${GIT_REPO} (branch: ${GIT_BRANCH})..."
    cd /mnt/data
    REPO_NAME=$(basename "${GIT_REPO}" .git)
    log "📂 Repository name: ${REPO_NAME}"
    
    if [ ! -d "${REPO_NAME}" ]; then
        if git clone -b "${GIT_BRANCH}" "${GIT_REPO}"; then
            success_log "Repository cloned successfully"
            chown -R ubuntu:ubuntu "${REPO_NAME}"
        else
            error_log "Failed to clone repository"
            exit 1
        fi
    fi
    
    cd "/mnt/data/${REPO_NAME}"
    
    # Docker 이미지 빌드 준비
    log "🐳 Preparing Docker environment..."
    
    # requirements.txt 확인 또는 생성
    if [ ! -f "requirements.txt" ]; then
        log "Creating minimal requirements.txt..."
        {
            echo "numpy>=1.24.0"
            echo "qiskit>=1.0.0"
            echo "pandas>=2.0.0"
            echo "scikit-learn>=1.0.0"
            echo "torch>=2.0.0"
            echo "matplotlib>=3.5.0"
            echo "seaborn>=0.12.0"
        } > requirements.txt
        success_log "Created requirements.txt"
    fi
    
    # Dockerfile 및 시작 스크립트 복사
    log "📝 Copying Docker configuration files..."
    mkdir -p .infra
    cp /mnt/data/${REPO_NAME}/.infra/Dockerfile .
    cp /mnt/data/${REPO_NAME}/.infra/start.sh .
    chmod +x start.sh
    
    # Docker 이미지 빌드
    log "🏗️ Building Docker image..."
    if docker build -t "${PROJECT_NAME}-dev" .; then
        success_log "Docker image built successfully"
        
        # 기존 컨테이너 정리
        if docker ps -a | grep -q "${PROJECT_NAME}-dev"; then
            log "Cleaning up existing containers..."
            docker rm -f "${PROJECT_NAME}-dev" || true
        fi
        
        # Docker 컨테이너 실행
        log "🚀 Starting Docker container..."
        if docker run -d \
            --name "${PROJECT_NAME}-dev" \
            -p 8888:8888 \
            -p 8080:8080 \
            -p 2222:22 \
            -v "/mnt/data/${REPO_NAME}:/workspace" \
            -e "SSH_PUBLIC_KEY=${SSH_PUBLIC_KEY}" \
            -e "SSH_PRIVATE_KEY=${SSH_PRIVATE_KEY}" \
            --restart unless-stopped \
            "${PROJECT_NAME}-dev"; then
            success_log "Docker container started successfully"
            
            # 서비스 접근 정보 출력
            PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "CHECK_AWS_CONSOLE")
            log "📋 Available services:"
            log "   - JupyterLab: http://${PUBLIC_IP}:8888 (token: qcbmtoken)"
            log "   - SSH 접속: ssh -p 2222 devuser@${PUBLIC_IP}"
            log "💾 Final disk space usage:"
            df -h | tee -a "${LOG_FILE}"
            success_log "Setup script completed successfully!"
        else
            error_log "Failed to start Docker container"
            exit 1
        fi
    else
        error_log "Failed to build Docker image"
        exit 1
    fi
else
    error_log "EBS volume not mounted, skipping setup."
    exit 1
fi