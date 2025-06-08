#!/bin/bash
set -e

# =================
# SSH Key Setup
# =================

# 1. Setup qb-frontier's public key for SSH access into the container
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    echo "Setting up public key for qb-frontier..."
    mkdir -p /home/qb-frontier/.ssh
    echo "${SSH_PUBLIC_KEY}" > /home/qb-frontier/.ssh/authorized_keys
    chown -R qb-frontier:qb-frontier /home/qb-frontier/.ssh
    chmod 700 /home/qb-frontier/.ssh
    chmod 600 /home/qb-frontier/.ssh/authorized_keys
    echo "Public key setup complete."
fi

# 2. Setup qb-frontier's private key for SSH access from the container (e.g., git push)
if [ -n "${SSH_PRIVATE_KEY}" ]; then
    echo "Setting up private key for qb-frontier..."
    mkdir -p /home/qb-frontier/.ssh
    echo "${SSH_PRIVATE_KEY}" > /home/qb-frontier/.ssh/id_ed25519
    chown -R qb-frontier:qb-frontier /home/qb-frontier/.ssh
    chmod 700 /home/qb-frontier/.ssh
    chmod 600 /home/qb-frontier/.ssh/id_ed25519

    # Add github.com to known_hosts to avoid interactive prompts
    ssh-keyscan -t rsa github.com >> /home/qb-frontier/.ssh/known_hosts
    chown qb-frontier:qb-frontier /home/qb-frontier/.ssh/known_hosts
    chmod 644 /home/qb-frontier/.ssh/known_hosts

    echo "Private key setup complete."
fi

# =================
# Start Services
# =================

# Start SSH server
echo "Starting SSH server..."
/usr/sbin/sshd

# Start JupyterLab as qb-frontier
echo "Starting JupyterLab..."
sudo -E -u qb-frontier jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --notebook-dir=/workspace 