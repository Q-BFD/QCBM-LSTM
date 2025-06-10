#!/bin/bash

# =============================
# Generic CPU Instance Deployment (Testing & Development)
# =============================

# =====================================
# 🔑 SSH Key Configuration (사용자가 수정할 주요 설정)
# =====================================
# 패턴: id_rsa_..._USERNAME 또는 id_ed25519_..._USERNAME
# 예: id_ed25519_github_yourname, id_rsa_company_yourname
SSH_KEY_NAME="id_ed25519_github_yourname"  # 🔑 여기에 실제 키 이름을 입력하세요!

# =====================================
# 자동 사용자 이름 추출 함수
# =====================================
extract_username_from_key() {
    local key_name="$1"
    # 마지막 _ 뒤의 부분을 추출하고, _를 -로 변환
    local username=$(echo "$key_name" | sed 's/.*_\([^_]*\)$/\1/' | tr '_' '-')
    echo "$username"
}

# 자동으로 사용자 이름과 키 경로 설정
DEV_USERNAME=$(extract_username_from_key "$SSH_KEY_NAME")
SSH_PUBLIC_KEY_FILE="~/.ssh/${SSH_KEY_NAME}.pub"
AWS_KEY_NAME="${DEV_USERNAME}-global-key"

echo "🔑 SSH Key Name: $SSH_KEY_NAME"
echo "👤 Extracted Username: $DEV_USERNAME" 
echo "📁 SSH Public Key File: $SSH_PUBLIC_KEY_FILE"
echo "🔐 AWS Key Name: $AWS_KEY_NAME"

# --- Argument Parsing ---
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 <PROJECT_NAME> [INSTANCE_TYPE]"
    echo ""
    echo "Examples:"
    echo "   $0 qcbm          # Deploy 'qcbm' with default instance type (t3.large)"
    echo "   $0 myproject t3.medium  # Deploy 'myproject' with t3.medium"
    echo ""
    echo "📦 This will create:"
    echo "   - Stack: {PROJECT_NAME}-dev-cpu"
    echo "   - Key Pair: {PROJECT_NAME}-dev-key"
    echo "   - Resources tagged with project name"
    exit 0
fi

if [ -z "$1" ]; then
    echo "❌ Error: Project name is required."
    echo "Usage: $0 <PROJECT_NAME> [INSTANCE_TYPE]"
    exit 1
fi

PROJECT_NAME="$1"
# Set INSTANCE_TYPE from the second argument, or default to t3.large
INSTANCE_TYPE_PARAM="${2:-t3.large}"

STACK_NAME="${PROJECT_NAME}-dev-cpu"
# 🔑 자동으로 설정된 키 정보 사용
KEY_NAME="$AWS_KEY_NAME"
# SSH_PUBLIC_KEY_FILE은 이미 위에서 설정됨
VOLUME_SIZE="50"  # Smaller storage for testing

# --- Git Repository Configuration ---
# Try to dynamically detect the Git repository URL and branch from the current directory
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    # Detect remote URL
    GIT_REMOTE_URL=$(git config --get remote.origin.url)
    
    # If the URL is HTTPS, convert it to SSH format for consistency
    if [[ "${GIT_REMOTE_URL}" == https://* ]]; then
        echo "🔄 Converting detected HTTPS remote to SSH format..."
        GIT_REMOTE_URL=$(echo "${GIT_REMOTE_URL}" | sed -E 's|https://([^/]+)/|git@\1:|')
    fi

    if [ -n "$GIT_REMOTE_URL" ]; then
        echo "✅ Dynamically detected Git repository: $GIT_REMOTE_URL"
        GIT_REPOSITORY="$GIT_REMOTE_URL"
    else
        echo "⚠️  Could not detect git remote 'origin'. Using default repository."
        GIT_REPOSITORY="git@github.com:Q-BFD/QCBM-LSTM.git"
    fi

    # Detect current branch and set it as default
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ -n "$CURRENT_BRANCH" ]; then
        echo "✅ Dynamically detected Git branch: $CURRENT_BRANCH"
        GIT_BRANCH="$CURRENT_BRANCH"
    else
        echo "⚠️  Could not detect current branch. Using default 'automation'."
        GIT_BRANCH="automation"
    fi
else
    echo "⚠️  Not inside a Git repository. Using default repository and branch."
    GIT_REPOSITORY="git@github.com:Q-BFD/QCBM-LSTM.git"
    GIT_BRANCH="automation"
fi

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

echo "🎯 Project Name: $PROJECT_NAME"
echo "📚 Stack Name: $STACK_NAME"

# =============================
# Validation
# =============================
SSH_PUBLIC_KEY_FILE_EXPANDED="${SSH_PUBLIC_KEY_FILE/#\~/$HOME}"
if [ ! -f "$SSH_PUBLIC_KEY_FILE_EXPANDED" ]; then
    echo "❌ Error: SSH public key file not found at: $SSH_PUBLIC_KEY_FILE_EXPANDED"
    exit 1
fi

# =============================
# Read SSH Public and Private Keys
# =============================
# 공개 키에서 주석을 제거하여 전달합니다.
SSH_PUBLIC_KEY=$(awk '{print $1" "$2}' "$SSH_PUBLIC_KEY_FILE_EXPANDED")
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
echo "🧪 Instance Type: $INSTANCE_TYPE_PARAM (CPU Testing - No GPU quota needed)"
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
    SSHPublicKey="$SSH_PUBLIC_KEY" \
    SSHPrivateKey="$SSH_PRIVATE_KEY" \
    InstanceType="$INSTANCE_TYPE_PARAM" \
    VolumeSize="$VOLUME_SIZE" \
    GitRepository="$GIT_REPOSITORY" \
    GitBranch="$GIT_BRANCH" \
    GitUserName="$DEV_USERNAME" \
    GitUserEmail="${DEV_USERNAME}@users.noreply.github.com" \
    SSHKeyName="$SSH_KEY_NAME" \
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
    echo "   💻 Instance: $INSTANCE_TYPE_PARAM (2 vCPU, 8GB RAM)"
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