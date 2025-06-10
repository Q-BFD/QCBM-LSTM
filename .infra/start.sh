#!/bin/bash
set -e

# 간단한 로깅 함수
log_start() {
    echo "[CONTAINER START] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# =====================================
# 동적 사용자 이름 추출
# =====================================
# 환경 변수에서 사용자 이름 가져오기
DEV_USERNAME="${DEV_USERNAME:-username}"  # 키 이름에서 자동 추출된 기본값

log_start "🔑 Development user: $DEV_USERNAME"

# =================
# SSH Key Setup
# =================

# 1. 컨테이너 접속을 위한 공개 키 설정
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    log_start "Setting up public key for $DEV_USERNAME..."
    mkdir -p /home/$DEV_USERNAME/.ssh
    echo "${SSH_PUBLIC_KEY}" > /home/$DEV_USERNAME/.ssh/authorized_keys
    chown -R $DEV_USERNAME:$DEV_USERNAME /home/$DEV_USERNAME/.ssh
    chmod 700 /home/$DEV_USERNAME/.ssh
    chmod 600 /home/$DEV_USERNAME/.ssh/authorized_keys
    log_start "Public key configured successfully"
fi

# 2. 컨테이너 내부에서 Git 사용을 위한 개인 키 설정
if [ -n "${SSH_PRIVATE_KEY}" ]; then
    log_start "Setting up private key for $DEV_USERNAME..."
    mkdir -p /home/$DEV_USERNAME/.ssh
    echo "${SSH_PRIVATE_KEY}" > /home/$DEV_USERNAME/.ssh/id_ed25519
    chown -R $DEV_USERNAME:$DEV_USERNAME /home/$DEV_USERNAME/.ssh
    chmod 700 /home/$DEV_USERNAME/.ssh
    chmod 600 /home/$DEV_USERNAME/.ssh/id_ed25519

    # 상호작용 프롬프트를 피하기 위해 github.com을 known_hosts에 추가
    ssh-keyscan -t rsa github.com >> /home/$DEV_USERNAME/.ssh/known_hosts
    chown $DEV_USERNAME:$DEV_USERNAME /home/$DEV_USERNAME/.ssh/known_hosts
    chmod 644 /home/$DEV_USERNAME/.ssh/known_hosts

    log_start "Private key configured successfully"
fi

# =================
# Git Config
# =================
if [ -n "${GIT_USER_NAME}" ] && [ -n "${GIT_USER_EMAIL}" ]; then
    log_start "Configuring Git for $DEV_USERNAME user..."
    log_start "Username: ${GIT_USER_NAME}, Email: ${GIT_USER_EMAIL}"
    su - $DEV_USERNAME -c "
        git config --global user.name '${GIT_USER_NAME}' && \
        git config --global user.email '${GIT_USER_EMAIL}' && \
        git config --global i18n.commitencoding utf-8 && \
        git config --global i18n.logoutputencoding utf-8 && \
        git config --global core.quotepath false && \
        git config --global core.editor 'nano' && \
        git config --global init.defaultBranch main && \
        git config --global pull.rebase false && \
        git config --global color.ui auto"
    log_start "Git configuration completed"
fi

# =================
# 한글 로케일 환경 설정
# =================
log_start "Setting up Korean locale environment for $DEV_USERNAME user..."
# $DEV_USERNAME 사용자의 .bashrc에 한글 로케일 설정 추가
cat >> /home/$DEV_USERNAME/.bashrc << 'EOF'

# 한글 로케일 설정
export LANG=ko_KR.utf8
export LC_ALL=ko_KR.utf8
export LANGUAGE=ko_KR:ko
EOF

chown $DEV_USERNAME:$DEV_USERNAME /home/$DEV_USERNAME/.bashrc

# .profile에도 동일한 설정 추가 (SSH 로그인 시 더 안정적)
cat >> /home/$DEV_USERNAME/.profile << 'EOF'

# 한글 로케일 설정
export LANG=ko_KR.utf8
export LC_ALL=ko_KR.utf8
export LANGUAGE=ko_KR:ko
EOF

chown $DEV_USERNAME:$DEV_USERNAME /home/$DEV_USERNAME/.profile
log_start "Korean locale environment configured"

# =================
# Start Services
# =================

# SSH 서버 시작
log_start "Starting SSH server..."
/usr/sbin/sshd

# JupyterLab 시작
log_start "Starting JupyterLab..."
NOTEBOOK_DIR="/home/$DEV_USERNAME/${REPO_NAME:-QCBM-LSTM}"
su - $DEV_USERNAME -c "JUPYTER_TOKEN=${JUPYTER_TOKEN} jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --notebook-dir='$NOTEBOOK_DIR' \
    --LabApp.token='${JUPYTER_TOKEN}' &"

log_start "All services started successfully!"

# 컨테이너 유지를 위해 무한 대기
tail -f /dev/null
