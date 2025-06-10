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
    locales \
    htop \
    vim \
    nano \
    tmux \
    screen \
    tree \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 한글(ko_KR.UTF-8) 로케일 설정
RUN sed -i -e 's/# ko_KR.UTF-8 UTF-8/ko_KR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG ko_KR.UTF-8
ENV LANGUAGE ko_KR.UTF-8
ENV LC_ALL ko_KR.UTF-8

# SSH 서버 설정
RUN mkdir /var/run/sshd && \
    sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -ri 's/^#?PasswordAuthentication\s+.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -ri 's/^#?PubkeyAuthentication\s+.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -ri 's,^#?AuthorizedKeysFile.*,AuthorizedKeysFile /home/qb-frontier/.ssh/authorized_keys,' /etc/ssh/sshd_config

# 개발자 사용자 생성
RUN useradd -m -s /bin/bash qb-frontier && \
    echo "qb-frontier ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /home/qb-frontier/.ssh && \
    chmod 700 /home/qb-frontier/.ssh && \
    chown -R qb-frontier:qb-frontier /home/qb-frontier/.ssh

# 작업 디렉토리 설정
WORKDIR /home/qb-frontier

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

# SSH 키 환경 변수
ENV SSH_PUBLIC_KEY=""
ENV SSH_PRIVATE_KEY=""

# 시작 스크립트
COPY start.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
