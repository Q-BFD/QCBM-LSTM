#!/bin/bash

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