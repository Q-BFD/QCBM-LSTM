#!/bin/bash
set -e

# 간단한 로깅 함수
log_start() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# =================
# SSH Key Setup
# =================

# 1. 컨테이너 접속을 위한 공개 키 설정
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    log_start "Setting up public key for qb-frontier..."
    mkdir -p /home/qb-frontier/.ssh
    echo "${SSH_PUBLIC_KEY}" > /home/qb-frontier/.ssh/authorized_keys
    chown -R qb-frontier:qb-frontier /home/qb-frontier/.ssh
    chmod 700 /home/qb-frontier/.ssh
    chmod 600 /home/qb-frontier/.ssh/authorized_keys
    log_start "Public key setup complete."
fi

# 2. 컨테이너 내부에서 Git 사용을 위한 개인 키 설정
if [ -n "${SSH_PRIVATE_KEY}" ]; then
    log_start "Setting up private key for qb-frontier..."
    mkdir -p /home/qb-frontier/.ssh
    echo "${SSH_PRIVATE_KEY}" > /home/qb-frontier/.ssh/id_ed25519
    chown -R qb-frontier:qb-frontier /home/qb-frontier/.ssh
    chmod 700 /home/qb-frontier/.ssh
    chmod 600 /home/qb-frontier/.ssh/id_ed25519

    # 상호작용 프롬프트를 피하기 위해 github.com을 known_hosts에 추가
    ssh-keyscan -t rsa github.com >> /home/qb-frontier/.ssh/known_hosts
    chown qb-frontier:qb-frontier /home/qb-frontier/.ssh/known_hosts
    chmod 644 /home/qb-frontier/.ssh/known_hosts

    log_start "Private key setup complete."
fi

# =================
# Git Config
# =================
if [ -n "${GIT_USER_NAME}" ] && [ -n "${GIT_USER_EMAIL}" ]; then
    log_start "Configuring Git for qb-frontier user..."
    log_start "Username: ${GIT_USER_NAME}, Email: ${GIT_USER_EMAIL}"
    su - qb-frontier -c "
        git config --global user.name '${GIT_USER_NAME}' && \
        git config --global user.email '${GIT_USER_EMAIL}' && \
        git config --global i18n.commitencoding utf-8 && \
        git config --global i18n.logoutputencoding utf-8 && \
        git config --global core.quotepath false && \
        git config --global core.editor 'nano'"
    log_start "Git configuration complete."
fi

# =================
# Start Services
# =================

# SSH 서버 시작
log_start "Starting SSH server..."
/usr/sbin/sshd

# JupyterLab 시작
log_start "Starting JupyterLab..."
NOTEBOOK_DIR="/home/qb-frontier/${REPO_NAME:-QCBM-LSTM}"
su - qb-frontier -c "JUPYTER_TOKEN=${JUPYTER_TOKEN} jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --notebook-dir=${NOTEBOOK_DIR}"
