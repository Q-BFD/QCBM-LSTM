# =============================
# QCBM-LSTM Development Environment Dockerfile
# =============================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

# Install system packages
RUN apt update && apt install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-dev \
    sudo \
    unzip \
    build-essential \
    software-properties-common \
    locales \
    openssh-server \
    nodejs \
    vim \
    nano \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH server
RUN mkdir /var/run/sshd && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'AuthorizedKeysFile %h/.ssh/authorized_keys' >> /etc/ssh/sshd_config

# Create devuser with sudo privileges
RUN useradd -m -s /bin/bash devuser && \
    echo "devuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /home/devuser/.ssh && \
    chmod 700 /home/devuser/.ssh && \
    touch /home/devuser/.ssh/authorized_keys && \
    chmod 600 /home/devuser/.ssh/authorized_keys && \
    chown -R devuser:devuser /home/devuser/.ssh

# Install Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install code-server (VSCode Web)
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Switch to devuser
USER devuser
WORKDIR /home/devuser

# Configure code-server
RUN mkdir -p ~/.config/code-server && \
    echo "bind-addr: 0.0.0.0:8080" > ~/.config/code-server/config.yaml && \
    echo "auth: password" >> ~/.config/code-server/config.yaml && \
    echo "password: qcbmpassword" >> ~/.config/code-server/config.yaml && \
    echo "cert: false" >> ~/.config/code-server/config.yaml

# Create startup script
USER root
RUN echo '#!/bin/bash\n\
/usr/sbin/sshd -D &\n\
su - devuser -c "code-server --host 0.0.0.0 --port 8080" &\n\
wait\n' > /start.sh && \
    chmod +x /start.sh

# Expose ports
EXPOSE 8080 22

# Start services
CMD ["/start.sh"]
