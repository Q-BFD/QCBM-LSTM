#!/bin/bash
set -e

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

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "/var/log/${PROJECT_NAME}-setup.log"
}

error_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "/var/log/${PROJECT_NAME}-setup.log"
}

success_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "/var/log/${PROJECT_NAME}-setup.log"
}

log "==== setup_full.sh 시작 ===="
log "🚀 Starting ${PROJECT_NAME} development environment setup..."
log "🧪 Instance Type: ${INSTANCE_TYPE} (CPU Testing)"
log "📂 Git Repository: ${GIT_REPO}"
log "🌿 Git Branch: ${GIT_BRANCH}"
log "💾 Checking initial disk space..."
df -h | tee -a "/var/log/${PROJECT_NAME}-setup.log"

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
df -h | tee -a "/var/log/${PROJECT_NAME}-setup.log"

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
    lsblk | tee -a "/var/log/${PROJECT_NAME}-setup.log"
    
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
        fi
    fi
    
    log "📋 Using requirements.txt from repository..."
    cd "/mnt/data/${REPO_NAME}"
    if [ -f "requirements.txt" ]; then
        log "Requirements file found in repository:"
        head -10 requirements.txt | tee -a "/var/log/${PROJECT_NAME}-setup.log"
        success_log "Using repository requirements.txt"
    else
        error_log "No requirements.txt found in repository"
        log "Creating minimal requirements.txt as fallback..."
        {
            echo "numpy>=1.24.0"
            echo "jupyter>=1.0.0"
            echo "qiskit>=1.0.0"
        } > requirements.txt
    fi
    
    log "🧹 Cleaning system before package installation..."
    apt autoremove -y 2>/dev/null || true
    apt autoclean 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    
    AVAILABLE_SPACE_BEFORE=$(df / | awk 'NR==2 {print $4}')
    log "Available disk space before Python packages: ${AVAILABLE_SPACE_BEFORE} KB"
    
    log "🐍 Installing Python packages in stages..."
    log "Stage 1: Installing core packages..."
    pip3 install --no-cache-dir --upgrade pip
    pip3 install --no-cache-dir "numpy>=1.24.0" && success_log "numpy installed" || error_log "numpy failed"
    
    SPACE_CHECK=$(df / | awk 'NR==2 {print $4}')
    if [ "${SPACE_CHECK}" -lt 1000000 ]; then
        log "Low disk space detected, cleaning up..."
        apt autoremove -y && apt autoclean
        pip3 cache purge 2>/dev/null || true
    fi
    
    log "Stage 2: Installing Jupyter..."
    pip3 install --no-cache-dir "jupyter>=1.0.0" "notebook>=7.0.0" && success_log "Jupyter installed" || error_log "Jupyter failed"
    
    log "Stage 3: Installing utilities..."
    pip3 install --no-cache-dir "tqdm>=4.65.0" && success_log "tqdm installed" || error_log "tqdm failed"
    
    log "Stage 4: Installing Qiskit (latest version)..."
    if pip3 install --no-cache-dir "qiskit>=1.0.0"; then
        success_log "Qiskit latest version installed successfully"
    else
        log "Attempting Qiskit with specific compatible version..."
        pip3 install --no-cache-dir "qiskit==1.0.2" && success_log "Qiskit 1.0.2 installed" || error_log "Qiskit installation failed"
    fi
    
    log "🔑 Setting up SSH keys..."
    mkdir -p /home/ubuntu/.ssh
    echo "${SSHPublicKey}" >> /home/ubuntu/.ssh/authorized_keys
    chmod 600 /home/ubuntu/.ssh/authorized_keys
    chown -R ubuntu:ubuntu /home/ubuntu/.ssh
    success_log "SSH keys configured"
    
    log "🪐 Starting Jupyter Notebook server on host..."
    cd "/mnt/data/${REPO_NAME}" || cd /mnt/data || cd /home/ubuntu
    if which jupyter >/dev/null 2>&1; then
        nohup sudo -u ubuntu jupyter notebook \
            --ip=0.0.0.0 \
            --port=8888 \
            --no-browser \
            --notebook-dir="/mnt/data/${REPO_NAME}" \
            --NotebookApp.token="${PROJECT_NAME}token" \
            --NotebookApp.password='' \
            --allow-root > /var/log/jupyter.log 2>&1 &
        success_log "Jupyter Notebook started successfully"
    else
        error_log "Jupyter not available, skipping..."
    fi
    
    log "🐳 Docker installed but will be configured after EBS mount"
    echo "${PROJECT_NAME} development environment setup completed at $(date)" > "/mnt/data/${REPO_NAME}/setup-complete.txt" 2>/dev/null || echo "Setup completed" > /tmp/setup-complete.txt
    
    log "🎉 ${PROJECT_NAME} development environment setup completed!"
    log "🧪 CPU Test Instance setup finished"
    log "📋 Available services:"
    
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "CHECK_AWS_CONSOLE")
    log "   - Jupyter Notebook: http://${PUBLIC_IP}:8888 (token: ${PROJECT_NAME}token)"
    
    if docker ps | grep -q "${PROJECT_NAME}-dev"; then
        log "   - VSCode Web: http://${PUBLIC_IP}:8080"
        log "   - SSH to container: ssh devuser@${PUBLIC_IP} -p 2222"
    fi
    
    log "   - SSH to EC2: ssh ubuntu@${PUBLIC_IP}"
    log "🚀 Next: Test environment, then request GPU quota for g4dn.2xlarge"
    log "💾 Final disk space usage:"
    df -h | tee -a "/var/log/${PROJECT_NAME}-setup.log"
    success_log "Setup script completed successfully!"
else
    error_log "EBS volume not mounted, skipping repository clone and setup."
    exit 1
fi