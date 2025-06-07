#!/bin/bash

# =============================
# QCBM GPU On-Demand Instance Deployment
# =============================
STACK_NAME="qcbm-dev-ondemand"
KEY_NAME="qcbm-dev-key"  # AWS EC2 Key Pair name
SSH_PUBLIC_KEY_FILE="~/.ssh/id_ed25519_github_qb_frontier.pub"  # Path to your SSH public key file
INSTANCE_TYPE="g4dn.2xlarge"  # GPU instance for quantum ML workloads
VOLUME_SIZE="100"  # Storage for GPU packages

# Git repository configuration
GIT_REPOSITORY="https://github.com/Q-BFD/QCBM-LSTM.git"
GIT_BRANCH="automation"

# =============================
# Validation
# =============================
SSH_PUBLIC_KEY_FILE_EXPANDED="${SSH_PUBLIC_KEY_FILE/#\~/$HOME}"

if [ ! -f "$SSH_PUBLIC_KEY_FILE_EXPANDED" ]; then
    echo "❌ Error: SSH public key file not found at: $SSH_PUBLIC_KEY_FILE_EXPANDED"
    echo "Please check the SSH_PUBLIC_KEY_FILE variable or generate SSH key with:"
    echo "  ssh-keygen -t rsa -b 4096 -C 'your_email@example.com'"
    exit 1
fi

# =============================
# AWS EC2 Key Pair Management
# =============================
echo "🔍 Checking AWS EC2 Key Pair: $KEY_NAME"

if aws ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
    echo "✅ Key Pair '$KEY_NAME' already exists"
else
    echo "⚠️  Key Pair '$KEY_NAME' not found. Creating new one..."
    
    KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"
    
    if aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > "$KEY_FILE"; then
        chmod 600 "$KEY_FILE"
        echo "✅ Key Pair created successfully: $KEY_FILE"
        echo "   (This file is needed for direct EC2 access)"
    else
        echo "❌ Failed to create Key Pair"
        exit 1
    fi
fi

# =============================
# Read SSH Public Key
# =============================
SSH_PUBLIC_KEY=$(cat "$SSH_PUBLIC_KEY_FILE_EXPANDED")

if [ -z "$SSH_PUBLIC_KEY" ]; then
    echo "❌ Error: SSH public key file is empty"
    exit 1
fi

echo "🔑 Using SSH public key from: $SSH_PUBLIC_KEY_FILE_EXPANDED"
echo "🚀 Deploying GPU On-Demand CloudFormation stack: $STACK_NAME"
echo "💻 Instance Type: $INSTANCE_TYPE (On-Demand)"
echo "💾 Storage: ${VOLUME_SIZE}GB EBS"
echo "📂 Git Repository: $GIT_REPOSITORY"
echo "🌿 Git Branch: $GIT_BRANCH"

# =============================
# Deploy CloudFormation Stack
# =============================
aws cloudformation deploy \
  --template-file cloudformation-ondemand.yml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    KeyName="$KEY_NAME" \
    SSHPublicKey="$SSH_PUBLIC_KEY" \
    InstanceType="$INSTANCE_TYPE" \
    VolumeSize="$VOLUME_SIZE" \
    GitRepository="$GIT_REPOSITORY" \
    GitBranch="$GIT_BRANCH" \
  --capabilities CAPABILITY_NAMED_IAM

# =============================
# Get Outputs
# =============================
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 GPU On-Demand Instance deployed successfully!"
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks \
      --stack-name "$STACK_NAME" \
      --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
      --output table
    echo ""
    echo "🔧 Next Steps:"
    echo "   1. Run: ../setup_ssh_config.sh"
    echo "   2. Connect: VSCode Remote-SSH → qcbm-container"
    echo ""
    echo "🔑 SSH Keys Info:"
    echo "   📁 EC2 Key Pair: ~/.ssh/${KEY_NAME}.pem (for EC2 direct access)"
    echo "   📁 Dev SSH Key: $SSH_PUBLIC_KEY_FILE_EXPANDED (for container access)"
    echo ""
    echo "�� Billing: On-Demand pricing (reliable, no interruptions)"
    echo "📂 Repository: $GIT_REPOSITORY (branch: $GIT_BRANCH)"
else
    echo "❌ Deployment failed!"
    exit 1
fi 