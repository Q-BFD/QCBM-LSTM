#!/bin/bash
set -e

# =================
# SSH Key Setup
# =================

# 1. Setup devuser's public key for SSH access into the container
if [ -n "${SSH_PUBLIC_KEY}" ]; then
    echo "Setting up public key for devuser..."
    mkdir -p /home/devuser/.ssh
    echo "${SSH_PUBLIC_KEY}" > /home/devuser/.ssh/authorized_keys
    chown -R devuser:devuser /home/devuser/.ssh
    chmod 700 /home/devuser/.ssh
    chmod 600 /home/devuser/.ssh/authorized_keys
    echo "Public key setup complete."
fi

# 2. Setup devuser's private key for SSH access from the container (e.g., git push)
if [ -n "${SSH_PRIVATE_KEY}" ]; then
    echo "Setting up private key for devuser..."
    mkdir -p /home/devuser/.ssh
    echo "${SSH_PRIVATE_KEY}" > /home/devuser/.ssh/id_ed25519
    chown -R devuser:devuser /home/devuser/.ssh
    chmod 700 /home/devuser/.ssh
    chmod 600 /home/devuser/.ssh/id_ed25519

    # Add github.com to known_hosts to avoid interactive prompts
    ssh-keyscan -t rsa github.com >> /home/devuser/.ssh/known_hosts
    chown devuser:devuser /home/devuser/.ssh/known_hosts
    chmod 644 /home/devuser/.ssh/known_hosts

    echo "Private key setup complete."
fi

# =================
# Start Services
# =================

# Start SSH server
echo "Starting SSH server..."
/usr/sbin/sshd

# Start JupyterLab as devuser
echo "Starting JupyterLab..."
su - devuser -c "jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --notebook-dir=/workspace" 