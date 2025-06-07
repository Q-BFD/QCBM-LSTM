#!/bin/bash

# SSH 키 설정
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    echo "${SSH_PUBLIC_KEY}" > /home/devuser/.ssh/authorized_keys
    chmod 600 /home/devuser/.ssh/authorized_keys
    chown devuser:devuser /home/devuser/.ssh/authorized_keys
fi

# SSH 서버 시작
/usr/sbin/sshd

# JupyterLab 시작
jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --NotebookApp.token="${JUPYTER_TOKEN}" \
    --NotebookApp.password='' \
    --notebook-dir=/workspace 