#!/bin/bash
set -e
set -o pipefail

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

# 다중 라인 출력을 스트리밍하기 위한 로깅 함수
stream_log() {
    # 로그의 각 줄에 타임스탬프와 구분자를 추가합니다.
    while IFS= read -r line; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] | $line" | tee -a "${LOG_FILE}"
    done
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
        --ssh-key-name)
            SSH_KEY_NAME="$2"
            shift 2
            ;;
        --git-user-name)
            GIT_USER_NAME="$2"
            shift 2
            ;;
        --git-user-email)
            GIT_USER_EMAIL="$2"
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
GIT_REPO="${GIT_REPO:-git@github.com:Q-BFD/QCBM-LSTM.git}"
GIT_BRANCH="${GIT_BRANCH:-automation}"
# SSH 키 이름 설정 (CloudFormation에서 전달받거나 기본값 사용)
# 패턴: id_rsa_..._USERNAME 또는 id_ed25519_..._USERNAME (예: id_ed25519_github_username)
SSH_KEY_NAME="${SSH_KEY_NAME:-id_ed25519_github_yourname}"

# =====================================
# 자동 사용자 이름 추출 함수
# =====================================
extract_username_from_key() {
    local key_name="$1"
    
    # 키 이름에 underscore가 사용자 이름 부분에 있는지 검사
    local username_part=$(echo "$key_name" | sed 's/.*_\([^_]*\)$/\1/')
    if [[ "$username_part" == *"_"* ]]; then
        error_log "사용자 이름 부분에 underscore(_)를 사용할 수 없습니다: '$username_part'"
        error_log "키 이름을 다음 형식으로 변경하세요: id_type_provider_username"
        error_log "예: id_ed25519_github_qb-frontier (not qb_frontier)"
        exit 1
    fi
    
    # 마지막 _ 뒤의 부분을 사용자 이름으로 사용 (이미 hyphen이어야 함)
    echo "$username_part"
}

# 자동으로 사용자 이름 설정
DEV_USERNAME=$(extract_username_from_key "$SSH_KEY_NAME")
GIT_USER_NAME="${GIT_USER_NAME:-$DEV_USERNAME}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-${DEV_USERNAME}@users.noreply.github.com}"

log "🔑 SSH Key Name: $SSH_KEY_NAME"
log "👤 Extracted Username: $DEV_USERNAME"
log "📧 Git User: $GIT_USER_NAME <$GIT_USER_EMAIL>"

# --- SSH 키 로드 ---
# CloudFormation UserData에서 이미 키를 /home/ubuntu/.ssh/에 생성했습니다.
# 이 스크립트는 해당 키를 읽어와서 변수에 할당하고 사용하기만 합니다.
log "🚀 Loading SSH keys from /home/ubuntu/.ssh/..."
SSH_PRIVATE_KEY_PATH="/home/ubuntu/.ssh/${SSH_KEY_NAME}"
SSH_PUBLIC_KEY_PATH="/home/ubuntu/.ssh/${SSH_KEY_NAME}.pub"

if [ -f "$SSH_PRIVATE_KEY_PATH" ] && [ -f "$SSH_PUBLIC_KEY_PATH" ]; then
    SSH_PRIVATE_KEY=$(cat "${SSH_PRIVATE_KEY_PATH}")
    SSH_PUBLIC_KEY=$(cat "${SSH_PUBLIC_KEY_PATH}")
    success_log "SSH keys successfully loaded from host files."
else
    error_log "SSH key files not found in /home/ubuntu/.ssh/. Check CloudFormation UserData."
    exit 1
fi

# --- SSH URL 변환: HTTPS 주소를 SSH 주소로 변경 ---
if [[ "${GIT_REPO}" == https://* ]]; then
    log "HTTPS Git URL을 SSH 형식으로 변환합니다: ${GIT_REPO}"
    GIT_REPO_SSH=$(echo "${GIT_REPO}" | sed -E 's|https://([^/]+)/|git@\1:|')
    log "변환된 SSH URL: ${GIT_REPO_SSH}"
    GIT_REPO="${GIT_REPO_SSH}"
fi

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

# 볼륨 크기 허용 범위 설정 (CloudFormation에서 설정한 크기 ±10GB)
expected_min=$((VOLUME_SIZE - 10))
expected_max=$((VOLUME_SIZE + 10))

# 최소값이 음수가 되지 않도록 보정
if [ "${expected_min}" -lt 1 ]; then
    expected_min=1
fi

log "🔍 Enhanced EBS volume detection with 5 strategies..."
log "📏 Expected volume size: ${VOLUME_SIZE}GB (accepting range: ${expected_min}-${expected_max}GB)"

for attempt in {1..30}; do
    log "⏳ Attempt ${attempt}/30: Scanning for EBS volume..."
    log "📊 Current block devices:"
    lsblk | tee -a "${LOG_FILE}"
    
    log "🔍 Strategy 1: Scanning NVMe devices..."
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
                
                if [ "${device_size_gb}" -ge "${expected_min}" ] && [ "${device_size_gb}" -le "${expected_max}" ] && ! is_mounted "${target}"; then
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
                # 장치 크기를 숫자로 변환 (예: "50G" -> 50)
                device_size_num=$(echo "${device_size}" | sed 's/[^0-9]//g')
                if [ -n "${device_size_num}" ] && [ "${device_size_num}" -ge "${expected_min}" ] && [ "${device_size_num}" -le "${expected_max}" ]; then
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
        log "🔍 Strategy 3: Using AWS CLI to find attached volumes (with timeout)..."
        INSTANCE_ID=$(timeout 10 curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
        if [ -n "${INSTANCE_ID}" ]; then
            log "⏳ Querying AWS API for attached volumes (timeout: 30s)..."
            AWS_OUTPUT=$(timeout 30 aws ec2 describe-volumes \
                --filters "Name=attachment.instance-id,Values=${INSTANCE_ID}" \
                --query 'Volumes[?Size==`'"${VOLUME_SIZE}"'`].Attachments[0].Device' \
                --output text 2>/dev/null || echo "")
            
            if [ -n "${AWS_OUTPUT}" ] && [ "${AWS_OUTPUT}" != "None" ]; then
                for device in ${AWS_OUTPUT}; do
                    if [ "${device}" != "None" ] && [ -n "${device}" ]; then
                        # Convert xvdf to nvme1n1 for NVMe instances
                        actual_device=$(echo "${device}" | sed 's/xvd/nvme/; s/f$/1n1/')
                        log "🔍 AWS reported device: ${device} -> checking: ${actual_device}"
                        if [ -e "${actual_device}" ] && ! is_mounted "${actual_device}"; then
                            EBS_DEVICE="${actual_device}"
                            success_log "Found EBS volume via AWS CLI: ${EBS_DEVICE}"
                            EBS_SUCCESS=true
                            break 2
                        fi
                    fi
                done
            else
                log "⚠️  AWS CLI query completed but no suitable volumes found or timed out"
            fi
                 else
             log "⚠️  Could not get instance ID from metadata service"
         fi
     fi
     
     if [ -z "${EBS_DEVICE}" ]; then
         log "🔍 Strategy 4: Checking common EBS device paths..."
         # 일반적인 EBS 장치 경로들을 직접 체크
         for common_device in "/dev/nvme1n1" "/dev/nvme2n1" "/dev/xvdf" "/dev/xvdg"; do
             if [ -e "${common_device}" ] && ! is_mounted "${common_device}"; then
                 # 크기 확인
                 if command -v lsblk >/dev/null 2>&1; then
                     device_size_bytes=$(lsblk -b -n -o SIZE "${common_device}" 2>/dev/null | head -1)
                     if [ -n "${device_size_bytes}" ]; then
                         device_size_gb=$((device_size_bytes / 1024 / 1024 / 1024))
                         log "🔍 Found common device ${common_device} with size: ${device_size_gb} GB"
                         if [ "${device_size_gb}" -ge "${expected_min}" ] && [ "${device_size_gb}" -le "${expected_max}" ]; then
                             EBS_DEVICE="${common_device}"
                             success_log "Found EBS volume via strategy 4: ${EBS_DEVICE} (${device_size_gb} GB)"
                             EBS_SUCCESS=true
                             break 2
                         fi
                     fi
                 fi
             fi
         done
     fi
     
     if [ -z "${EBS_DEVICE}" ]; then
         log "🔍 Strategy 5: Finding largest unmounted disk..."
         # 마지막 수단: 가장 큰 unmounted 디스크 찾기
         largest_device=""
         largest_size=0
         
         while IFS= read -r line; do
             device_name=$(echo "${line}" | awk '{print $1}')
             device_size=$(echo "${line}" | awk '{print $2}')
             mount_point=$(echo "${line}" | awk '{print $3}')
             device_type=$(echo "${line}" | awk '{print $4}')
             
             if [ "${device_type}" = "disk" ] && [ "${mount_point}" = "none" ]; then
                 device_size_num=$(echo "${device_size}" | sed 's/[^0-9]//g')
                 if [ -n "${device_size_num}" ] && [ "${device_size_num}" -gt "${largest_size}" ] && [ "${device_size_num}" -ge 10 ]; then
                     full_device="/dev/${device_name}"
                     if [ -e "${full_device}" ]; then
                         largest_device="${full_device}"
                         largest_size="${device_size_num}"
                     fi
                 fi
             fi
         done < <(get_block_devices)
         
         if [ -n "${largest_device}" ] && [ "${largest_size}" -ge 10 ]; then
             log "🔍 Found largest unmounted disk: ${largest_device} (${largest_size} GB)"
             EBS_DEVICE="${largest_device}"
             success_log "Found EBS volume via strategy 5: ${EBS_DEVICE} (${largest_size} GB)"
             EBS_SUCCESS=true
             break
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
    error_log "Could not find EBS volume after 30 attempts (tried 5 different strategies)"
    log "🔍 Debug info - final attempt:"
    log "  - Volume size expected: ${VOLUME_SIZE}GB (range: ${expected_min}-${expected_max}GB)"
    log "  - Current block devices:"
    lsblk | tee -a "${LOG_FILE}"
    exit 1
fi

if [ "${MOUNT_OK}" = true ]; then
    log "📁 Cloning repository from ${GIT_REPO} (branch: ${GIT_BRANCH})..."
    cd /mnt/data
    REPO_NAME=$(basename "${GIT_REPO}" .git)
    log "📂 Repository name: ${REPO_NAME}"
    
    if [ ! -d "${REPO_NAME}" ]; then
        # Use the key stored on the host for the clone operation.
        export GIT_SSH_COMMAND="ssh -i ${SSH_PRIVATE_KEY_PATH} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"
        
        log "⏳ Attempting to clone with host key: ${SSH_PRIVATE_KEY_PATH}"
        if git clone -b "${GIT_BRANCH}" "${GIT_REPO}"; then
            success_log "Repository cloned successfully"
            chown -R ubuntu:ubuntu "${REPO_NAME}"
        else
            error_log "Failed to clone repository"
            unset GIT_SSH_COMMAND
            exit 1
        fi
        
        # Unset the command after use
        unset GIT_SSH_COMMAND
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
    
    # Docker 이미지 빌드 (.infra 디렉토리에서 실행, 상위 디렉토리를 빌드 컨텍스트로 사용)
    log "🏗️ Building Docker image from .infra directory..."
    cd .infra
    if docker build -f Dockerfile --build-arg DEV_USERNAME="${DEV_USERNAME}" -t "${PROJECT_NAME}-dev" .. 2>&1 | stream_log; then
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
            -v "/mnt/data/${REPO_NAME}:/home/${DEV_USERNAME}/${REPO_NAME}" \
            -e "SSH_PUBLIC_KEY=${SSH_PUBLIC_KEY}" \
            -e "SSH_PRIVATE_KEY=${SSH_PRIVATE_KEY}" \
            -e "JUPYTER_TOKEN=qcbmtoken" \
            -e "GIT_USER_NAME=${GIT_USER_NAME}" \
            -e "GIT_USER_EMAIL=${GIT_USER_EMAIL}" \
            -e "DEV_USERNAME=${DEV_USERNAME}" \
            -e "REPO_NAME=${REPO_NAME}" \
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
        error_log "Failed to build Docker image. Check the log above for details."
        exit 1
    fi
else
    error_log "EBS volume not mounted, skipping setup."
    exit 1
fi