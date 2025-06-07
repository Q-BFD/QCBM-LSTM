# =============================
# QCBM-LSTM Development Environment Dockerfile
# =============================
FROM python:3.9-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    nodejs \
    npm \
    openssh-server \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# SSH 서버 설정
RUN mkdir /var/run/sshd && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config

# 개발자 사용자 생성
RUN useradd -m -s /bin/bash devuser && \
    echo "devuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /home/devuser/.ssh && \
    chmod 700 /home/devuser/.ssh && \
    chown -R devuser:devuser /home/devuser/.ssh

# 작업 디렉토리 설정
WORKDIR /workspace

# Python 패키지 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir \
    jupyterlab>=4.0.0 \
    notebook>=7.0.0 \
    ipywidgets>=8.0.0

# JupyterLab 설정
EXPOSE 8888 8080 22
ENV JUPYTER_ENABLE_LAB=yes
ENV JUPYTER_TOKEN=qcbmtoken

# 시작 스크립트
COPY start.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
