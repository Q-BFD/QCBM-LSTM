#!/bin/bash

# =============================
# Generic CPU Instance Deployment (Testing & Development)
# =============================

# Project name from argument or default
PROJECT_NAME="$1"
INSTANCE_TYPE="${2:-t3.large}"
[ -z "$PROJECT_NAME" ] && { echo "Usage: $0 <PROJECT_NAME> [INSTANCE_TYPE]"; exit 1; }

STACK_NAME="${PROJECT_NAME}-dev-cpu"
# 🔑 모든 인스턴스에 사용할 고정된 키 페어 이름과 파일 경로
KEY_NAME="qb-frontier-global-key"
SSH_PUBLIC_KEY_FILE="~/.ssh/id_ed25519_github_qb_frontier.pub"
VOLUME_SIZE="50"  # Smaller storage for testing

# Git repository configuration
GIT_REPOSITORY="https://github.com/Q-BFD/QCBM-LSTM.git"
GIT_BRANCH="automation"

# Parse setup script information from Git repository
SETUP_SCRIPT_PATH=".infra/setup_full.sh"

# Parse organization and repository from Git URL
if [[ $GIT_REPOSITORY =~ github\.com[/:]([^/]+)/([^/]+)\.git ]]; then
    SETUP_SCRIPT_ORG="${BASH_REMATCH[1]}"
    SETUP_SCRIPT_REPO="${BASH_REMATCH[2]}"
    SETUP_SCRIPT_BRANCH="$GIT_BRANCH"
    echo "📦 Parsed Git info:"
    echo "   - Organization: $SETUP_SCRIPT_ORG"
    echo "   - Repository: $SETUP_SCRIPT_REPO"
    echo "   - Branch: $SETUP_SCRIPT_BRANCH"
else
    echo "❌ Error: Could not parse GitHub organization and repository from URL: $GIT_REPOSITORY"
    exit 1
fi

# =============================
# Usage Information
# =============================
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 [PROJECT_NAME] [INSTANCE_TYPE]"
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
echo "🔍 Using global key '$KEY_NAME' for all instances."
SSH_PUBLIC_KEY_FILE_EXPANDED="${SSH_PUBLIC_KEY_FILE/#\~/$HOME}"

if [ ! -f "$SSH_PUBLIC_KEY_FILE_EXPANDED" ]; then
    echo "❌ Error: SSH public key file not found at: $SSH_PUBLIC_KEY_FILE_EXPANDED"
    exit 1
fi

# AWS에 최신 로컬 공개 키를 등록합니다.
echo "   Ensuring AWS Key Pair '$KEY_NAME' is up-to-date with local key..."
if aws ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
    aws ec2 delete-key-pair --key-name "$KEY_NAME"
fi

# 공개 키에서 주석을 제거하고 AWS로 가져옵니다.
KEY_MATERIAL=$(awk '{print $1" "$2}' "$SSH_PUBLIC_KEY_FILE_EXPANDED")
aws ec2 import-key-pair --key-name "$KEY_NAME" --public-key-material "$KEY_MATERIAL"
if [ $? -ne 0 ]; then
    echo "❌ Failed to import SSH public key to AWS EC2."
    echo "   Please check the key format and AWS permissions."
    exit 1
fi
echo "✅ Successfully imported public key to AWS EC2 as '$KEY_NAME'."

# =============================
# Read SSH Public and Private Keys
# =============================
SSH_PUBLIC_KEY=$(cat "$SSH_PUBLIC_KEY_FILE_EXPANDED")
SSH_PRIVATE_KEY_FILE="${SSH_PUBLIC_KEY_FILE_EXPANDED%.pub}"

if [ ! -f "$SSH_PRIVATE_KEY_FILE" ]; then
    echo "❌ Error: Corresponding private key not found at: $SSH_PRIVATE_KEY_FILE"
    exit 1
fi
SSH_PRIVATE_KEY=$(cat "$SSH_PRIVATE_KEY_FILE")

if [ -z "$SSH_PUBLIC_KEY" ] || [ -z "$SSH_PRIVATE_KEY" ]; then
    echo "❌ Error: SSH public or private key file is empty"
    exit 1
fi

echo "🔑 Using SSH public key from: $SSH_PUBLIC_KEY_FILE_EXPANDED"
echo "🔐 Using corresponding private key for Git operations in container"
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
    SSHPrivateKey="$SSH_PRIVATE_KEY" \
    InstanceType="$INSTANCE_TYPE" \
    VolumeSize="$VOLUME_SIZE" \
    GitRepository="$GIT_REPOSITORY" \
    GitBranch="$GIT_BRANCH" \
    SetupScriptOrg="$SETUP_SCRIPT_ORG" \
    SetupScriptRepo="$SETUP_SCRIPT_REPO" \
    SetupScriptBranch="$SETUP_SCRIPT_BRANCH" \
    SetupScriptPath="$SETUP_SCRIPT_PATH" \
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