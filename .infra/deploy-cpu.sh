#!/bin/bash

# =============================
# Generic CPU Instance Deployment (Testing & Development)
# =============================

# Project name from argument or default
PROJECT_NAME="${1:-qcbm}"  # First argument or default to 'qcbm'
STACK_NAME="${PROJECT_NAME}-dev-cpu"
KEY_NAME="${PROJECT_NAME}-dev-key"  # AWS EC2 Key Pair name
SSH_PUBLIC_KEY_FILE="~/.ssh/id_ed25519_github_qb_frontier.pub"  # Path to your SSH public key file
INSTANCE_TYPE="t3.large"  # CPU instance for testing (no GPU quota needed)
VOLUME_SIZE="50"  # Smaller storage for testing

# Git repository configuration
GIT_REPOSITORY="https://github.com/Q-BFD/QCBM-LSTM.git"
GIT_BRANCH="automation"

# =============================
# Usage Information
# =============================
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 [PROJECT_NAME]"
    echo ""
    echo "Examples:"
    echo "   $0 qcbm          # Deploy with project name 'qcbm'"
    echo "   $0 myproject     # Deploy with project name 'myproject'"
    echo "   $0               # Deploy with default name 'qcbm'"
    echo ""
    echo "📦 This will create:"
    echo "   - Stack: {PROJECT_NAME}-dev-cpu"
    echo "   - Key Pair: {PROJECT_NAME}-dev-key"
    echo "   - Resources tagged with project name"
    exit 0
fi

echo "🎯 Project Name: $PROJECT_NAME"
echo "📚 Stack Name: $STACK_NAME"

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
echo "🚀 Deploying $PROJECT_NAME CPU Test Instance CloudFormation stack: $STACK_NAME"
echo "🧪 Instance Type: $INSTANCE_TYPE (CPU Testing - No GPU quota needed)"
echo "💾 Storage: ${VOLUME_SIZE}GB EBS"
echo "📂 Git Repository: $GIT_REPOSITORY"
echo "🌿 Git Branch: $GIT_BRANCH"
echo ""
echo "🎯 Purpose: Test Docker environment and SSH setup before GPU upgrade"
echo "💰 Cost: ~\$0.09/hour (very affordable for testing)"

# =============================
# Deploy CloudFormation Stack
# =============================
aws cloudformation deploy \
  --template-file cloudformation-cpu.yml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    ProjectName="$PROJECT_NAME" \
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
    echo "🎉 $PROJECT_NAME CPU Test Instance deployed successfully!"
    echo "🧪 This validates your Docker and SSH setup"
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks \
      --stack-name "$STACK_NAME" \
      --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
      --output table
    echo ""
    echo "🔧 Next Steps:"
    echo "   1. Wait 3-5 minutes for environment setup to complete"
    echo "   2. Setup SSH: ./setup_ssh_config.sh $PROJECT_NAME"
    echo "   3. Test with Jupyter: http://YOUR_ELASTIC_IP:8888 (token: ${PROJECT_NAME}token)"
    echo "   4. Connect: VSCode Remote-SSH → ${PROJECT_NAME}-container"
    echo "   5. Request GPU quota increase (see below)"
    echo ""
    echo "🔑 SSH Keys Info:"
    echo "   📁 EC2 Key Pair: ~/.ssh/${KEY_NAME}.pem (for EC2 direct access)"
    echo "   📁 Dev SSH Key: $SSH_PUBLIC_KEY_FILE_EXPANDED (for container access)"
    echo ""
    echo "🧪 Testing Environment:"
    echo "   💻 Instance: $INSTANCE_TYPE (2 vCPU, 8GB RAM)"
    echo "   💾 Storage: ${VOLUME_SIZE}GB EBS"
    echo "   🐍 Python: CPU-only PyTorch, Qiskit, Jupyter"
    echo "   📂 Repository: $GIT_REPOSITORY (branch: $GIT_BRANCH)"
    echo ""
    echo "🚀 GPU Upgrade Path:"
    echo "   1. Test current environment thoroughly"
    echo "   2. AWS Console → Service Quotas → EC2"
    echo "   3. Request 'Running On-Demand G instances' → 8 vCPU"
    echo "   4. Wait for approval (usually 1-24 hours)"
    echo "   5. Deploy GPU instance: ./deploy-ondemand.sh or ./deploy-spot.sh"
    echo ""
    echo "📊 Environment Status:"
    echo "   ⏳ Setting up... (check logs: ssh ubuntu@YOUR_IP 'tail -f /var/log/${PROJECT_NAME}-setup.log')"
else
    echo "❌ Deployment failed!"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check AWS CLI configuration: aws sts get-caller-identity"
    echo "   2. Verify SSH key file exists: ls -la $SSH_PUBLIC_KEY_FILE_EXPANDED"
    echo "   3. Check CloudFormation events:"
    echo "      aws cloudformation describe-stack-events --stack-name $STACK_NAME"
    exit 1
fi 