#!/bin/bash

echo "[DEBUG] Checking SSH key setup..."
echo "[DEBUG] SSH_PUBLIC_KEY value length: ${#SSH_PUBLIC_KEY}"

# SSH 키 설정
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    echo "[DEBUG] Setting up SSH key for devuser..."
    echo "${SSH_PUBLIC_KEY}" > /home/devuser/.ssh/authorized_keys
    chmod 600 /home/devuser/.ssh/authorized_keys
    chown devuser:devuser /home/devuser/.ssh/authorized_keys
    echo "[DEBUG] SSH key setup completed. Key content:"
    ls -la /home/devuser/.ssh/
    head -n 1 /home/devuser/.ssh/authorized_keys
else
    echo "[DEBUG] No SSH_PUBLIC_KEY provided!"
fi

# SSH 서버 시작
echo "[DEBUG] Starting SSH server..."
/usr/sbin/sshd
echo "[DEBUG] SSH server started"

# JupyterLab 시작
echo "[DEBUG] Starting JupyterLab..."
jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --NotebookApp.token="${JUPYTER_TOKEN}" \
    --NotebookApp.password='' \
    --notebook-dir=/workspace 