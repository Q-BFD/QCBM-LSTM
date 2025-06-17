#!/bin/bash

# =============================
# Generic CPU Instance Deployment (Testing & Development)
# =============================

# =====================================
# 사용법 표시 함수
# =====================================
show_usage() {
    echo "📋 Usage: $0 PROJECT_NAME [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -k, --ssh-key KEY_NAME    SSH 키 이름 (필수)"
    echo "  -i, --instance-type TYPE  CPU 인스턴스 타입 (기본값: t3.large)"
    echo "  -v, --volume-size SIZE    EBS 볼륨 크기 GB (기본값: 50)"
    echo "  -h, --help               도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_john-doe"
    echo "  $0 myproject -k id_rsa_company_alice-kim --instance-type t3.xlarge"
    echo "  $0 qcbm -k /custom/path/my_key -i c5.2xlarge -v 100"
    echo ""
    echo "🔑 SSH 키 네이밍 규칙:"
    echo "  패턴: id_[키타입]_[서비스]_[사용자이름]"
    echo "  ⚠️  사용자 이름 부분에 underscore(_) 사용 금지!"
    echo ""
    echo "  ✅ 올바른 예시:"
    echo "    - id_ed25519_github_john-doe"
    echo "    - id_rsa_company_alice-kim"
    echo ""
    echo "  ❌ 잘못된 예시:"
    echo "    - id_ed25519_github_john_doe  (underscore 사용)"
    exit 0
}

# =====================================
# 인자 파싱
# =====================================
PROJECT_NAME=""
SSH_KEY_NAME=""
INSTANCE_TYPE="m7i.2xlarge"
VOLUME_SIZE="100"

while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--ssh-key)
            SSH_KEY_NAME="$2"
            shift 2
            ;;
        -i|--instance-type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        -v|--volume-size)
            VOLUME_SIZE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        -*)
            echo "❌ 알 수 없는 옵션: $1"
            echo "도움말: $0 --help"
            exit 1
            ;;
        *)
            if [ -z "$PROJECT_NAME" ]; then
                PROJECT_NAME="$1"
            else
                echo "❌ 너무 많은 인자: $1"
                echo "도움말: $0 --help"
                exit 1
            fi
            shift
            ;;
    esac
done

# 필수 인자 검증
if [ -z "$PROJECT_NAME" ]; then
    echo "❌ ERROR: PROJECT_NAME이 필요합니다."
    show_usage
fi

if [ -z "$SSH_KEY_NAME" ]; then
    echo "❌ ERROR: SSH 키 이름이 필요합니다."
    echo "   예: $0 $PROJECT_NAME --ssh-key id_ed25519_github_yourname"
    show_usage
fi

# =====================================
# 자동 사용자 이름 추출 함수
# =====================================
extract_username_from_key() {
    local key_name="$1"
    
    # 키 이름에 underscore가 사용자 이름 부분에 있는지 검사
    local username_part=$(echo "$key_name" | sed 's/.*_\([^_]*\)$/\1/')
    if [[ "$username_part" == *"_"* ]]; then
        echo "❌ ERROR: 사용자 이름 부분에 underscore(_)를 사용할 수 없습니다: '$username_part'"
        echo "   키 이름을 다음 형식으로 변경하세요: id_type_provider_username"
        echo "   예: id_ed25519_github_qb-frontier (not qb_frontier)"
        exit 1
    fi
    
    # 마지막 _ 뒤의 부분을 사용자 이름으로 사용 (이미 hyphen이어야 함)
    echo "$username_part"
}

# =====================================
# SSH 키 검증 및 사용자 확인
# =====================================
echo "🔑 SSH Key Name: $SSH_KEY_NAME"

# 사용자 이름 추출 (경로에서 키 이름만 추출)
if [[ "$SSH_KEY_NAME" == *"/"* ]]; then
    # Full path인 경우 파일명만 추출
    KEY_BASENAME=$(basename "$SSH_KEY_NAME")
else
    # 키 이름만인 경우 그대로 사용
    KEY_BASENAME="$SSH_KEY_NAME"
fi

DEV_USERNAME=$(extract_username_from_key "$KEY_BASENAME")
echo "👤 Extracted Username: $DEV_USERNAME"

# SSH 키 파일 경로 설정 (유연한 경로 지원)
if [[ "$SSH_KEY_NAME" == *"/"* ]]; then
    # Full path가 주어진 경우
    if [[ "$SSH_KEY_NAME" == *".pub" ]]; then
        # .pub 파일 경로가 주어진 경우
        SSH_PUBLIC_KEY_FILE="$SSH_KEY_NAME"
        SSH_PRIVATE_KEY_FILE="${SSH_KEY_NAME%.pub}"
    else
        # 개인 키 경로가 주어진 경우
        SSH_PRIVATE_KEY_FILE="$SSH_KEY_NAME"
        SSH_PUBLIC_KEY_FILE="${SSH_KEY_NAME}.pub"
    fi
else
    # 키 이름만 주어진 경우 (기본 ~/.ssh/ 경로 사용)
    SSH_PUBLIC_KEY_FILE="~/.ssh/${SSH_KEY_NAME}.pub"
    SSH_PRIVATE_KEY_FILE="~/.ssh/${SSH_KEY_NAME}"
fi

# 키 파일 존재 여부 확인
EXPANDED_PUBLIC_KEY=$(eval echo "$SSH_PUBLIC_KEY_FILE")
EXPANDED_PRIVATE_KEY=$(eval echo "$SSH_PRIVATE_KEY_FILE")

if [ ! -f "$EXPANDED_PUBLIC_KEY" ]; then
    echo "❌ ERROR: SSH 공개 키 파일을 찾을 수 없습니다: $EXPANDED_PUBLIC_KEY"
    echo "   키를 생성하거나 경로를 확인하세요."
    echo ""
    echo "💡 사용법:"
    echo "   키 이름만: --ssh-key id_ed25519_github_yourname"
    echo "   Full path: --ssh-key /path/to/your/key"
    exit 1
fi

if [ ! -f "$EXPANDED_PRIVATE_KEY" ]; then
    echo "❌ ERROR: SSH 개인 키 파일을 찾을 수 없습니다: $EXPANDED_PRIVATE_KEY"
    echo "   키를 생성하거나 경로를 확인하세요."
    exit 1
fi

echo "✅ SSH 키 파일 확인 완료"
echo "📁 SSH Public Key File: $SSH_PUBLIC_KEY_FILE"
echo "📁 SSH Private Key File: $SSH_PRIVATE_KEY_FILE"

# =====================================
# 사용자 확인 프롬프트
# =====================================
echo ""
echo "🎯 배포 정보 확인:"
echo "   📦 프로젝트 이름: $PROJECT_NAME"
echo "   🔑 SSH 키: $SSH_KEY_NAME"
echo "   👤 컨테이너 사용자: $DEV_USERNAME"
echo "   🖥️  인스턴스 타입: $INSTANCE_TYPE"
echo "   💾 볼륨 크기: ${VOLUME_SIZE}GB"
echo "   🏷️  스택 이름: ${PROJECT_NAME}-dev-cpu"
echo ""
read -p "🚀 위 설정으로 배포를 진행하시겠습니까? (y/N): " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 배포가 취소되었습니다."
    exit 0
fi

# 자동으로 AWS 키 이름과 Git 정보 설정
AWS_KEY_NAME="${DEV_USERNAME}-global-key"
DEV_USERNAME=$(extract_username_from_key "$SSH_KEY_NAME")
GIT_USER_NAME="${DEV_USERNAME}"
GIT_USER_EMAIL="${DEV_USERNAME}@users.noreply.github.com"

# Git 정보 자동 감지
if git remote get-url origin >/dev/null 2>&1; then
    GIT_REPOSITORY=$(git remote get-url origin)
    if [[ "$GIT_REPOSITORY" == https://* ]]; then
        # HTTPS URL을 SSH 형식으로 변환
        GIT_REPOSITORY=$(echo "$GIT_REPOSITORY" | sed -E 's|https://([^/]+)/|git@\1:|')
    fi
    echo "✅ Dynamically detected Git repository: $GIT_REPOSITORY"
else
    GIT_REPOSITORY="git@github.com:Q-BFD/QCBM-LSTM.git"
    echo "⚠️  Could not detect Git repository, using default: $GIT_REPOSITORY"
fi

if git branch --show-current >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current)
    echo "✅ Dynamically detected Git branch: $GIT_BRANCH"
else
    GIT_BRANCH="automation"
    echo "⚠️  Could not detect Git branch, using default: $GIT_BRANCH"
fi

# Git 저장소 정보 파싱
if [[ "$GIT_REPOSITORY" =~ git@([^:]+):([^/]+)/([^.]+)\.git ]]; then
    GIT_HOST="${BASH_REMATCH[1]}"
    SETUP_SCRIPT_ORG="${BASH_REMATCH[2]}"
    SETUP_SCRIPT_REPO="${BASH_REMATCH[3]}"
    
    echo "📦 Parsed Git info:"
    echo "   - Organization: $SETUP_SCRIPT_ORG"
    echo "   - Repository: $SETUP_SCRIPT_REPO"
    echo "   - Branch: $GIT_BRANCH"
else
    echo "⚠️  Could not parse Git repository URL, using defaults"
    SETUP_SCRIPT_ORG="Q-BFD"
    SETUP_SCRIPT_REPO="QCBM-LSTM"
fi

SETUP_SCRIPT_BRANCH="$GIT_BRANCH"
SETUP_SCRIPT_PATH=".infra/setup_full.sh"

# =====================================
# 배포 설정
# =====================================
echo "🎯 Project Name: $PROJECT_NAME"
echo "📚 Stack Name: ${PROJECT_NAME}-dev-cpu"
echo "🔐 AWS Key Name: $AWS_KEY_NAME"

# SSH 키 로드
SSH_PUBLIC_KEY=$(cat "$EXPANDED_PUBLIC_KEY")
SSH_PRIVATE_KEY=$(cat "$EXPANDED_PRIVATE_KEY")

if [ -z "$SSH_PUBLIC_KEY" ] || [ -z "$SSH_PRIVATE_KEY" ]; then
    echo "❌ ERROR: SSH 키를 읽을 수 없습니다."
    exit 1
fi

echo "🔐 Using corresponding private key for Git operations in container"

# =====================================
# CloudFormation 배포
# =====================================
STACK_NAME="${PROJECT_NAME}-dev-cpu"
KEY_NAME="$AWS_KEY_NAME"
# Volume size and instance type are now from command line arguments

echo "🚀 Deploying $PROJECT_NAME CPU Test Instance CloudFormation stack: $STACK_NAME"
echo "🧪 Instance Type: $INSTANCE_TYPE (CPU Testing - No GPU quota needed)"
echo "💾 Storage: ${VOLUME_SIZE}GB EBS"
echo "📂 Git Repository: $GIT_REPOSITORY"
echo "🌿 Git Branch: $GIT_BRANCH"
echo ""
echo "🎯 Purpose: Test Docker environment and SSH setup before GPU upgrade"
echo "💰 Cost: ~$0.09/hour (very affordable for testing)"
echo ""

aws cloudformation deploy \
  --template-file cloudformation-cpu.yml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    ProjectName="$PROJECT_NAME" \
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
    SSHKeyName="$SSH_KEY_NAME" \
    GitUserName="$GIT_USER_NAME" \
    GitUserEmail="$GIT_USER_EMAIL" \
  --capabilities CAPABILITY_NAMED_IAM

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 $PROJECT_NAME CPU Test Instance deployed successfully!"
    echo "🧪 This validates your Docker and SSH setup"
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs" --output table 2>/dev/null | head -20 | cat
    echo ""
    echo "🔧 Next Steps:"
    echo "   1. Wait 3-5 minutes for environment setup to complete"
    echo "   2. Setup SSH: ./setup_ssh_config.sh $PROJECT_NAME --ssh-key $SSH_KEY_NAME"
    echo "   3. Test with Jupyter: http://YOUR_ELASTIC_IP:8888 (token: qcbmtoken)"
    echo "   4. Connect: VSCode Remote-SSH → ${PROJECT_NAME}-container"
    echo "   5. Request GPU quota increase (see below)"
    echo ""
    echo "🔑 SSH Keys Info:"
    echo "   📁 EC2 Key Pair: ~/.ssh/${KEY_NAME}.pem (for EC2 direct access)"
    echo "   📁 Dev SSH Key: $SSH_PUBLIC_KEY_FILE (for container access)"
else
    echo "❌ Deployment failed!"
    exit 1
fi

# =====================================
# 추가 정보 표시
# =====================================
echo ""
echo "🧪 Testing Environment:"
echo "   💻 Instance: $INSTANCE_TYPE"
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