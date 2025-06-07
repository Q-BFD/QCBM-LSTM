#!/bin/bash

# =============================
# Generic SSH Config Setup Script
# =============================

# Project name from argument or default
PROJECT_NAME="${1:-qcbm}"  # First argument or default to 'qcbm'

# =============================
# Usage Information
# =============================
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 [PROJECT_NAME]"
    echo ""
    echo "Examples:"
    echo "   $0 qcbm          # Setup SSH for project 'qcbm'"
    echo "   $0 myproject     # Setup SSH for project 'myproject'"
    echo "   $0               # Setup SSH for default 'qcbm'"
    echo ""
    echo "📦 This will configure SSH access to:"
    echo "   - EC2 Instance: {PROJECT_NAME}"
    echo "   - Docker Container: {PROJECT_NAME}-container"
    exit 0
fi

echo "🎯 Project Name: $PROJECT_NAME"

# =============================
# Configuration Variables
# =============================
STACK_NAME="${PROJECT_NAME}-dev-cpu"        # CloudFormation 스택 이름 (deploy-cpu.sh와 일치)
ALIAS_NAME="$PROJECT_NAME"                   # SSH 별칭
USER_NAME="ubuntu"                           # EC2 기본 사용자 (Ubuntu 기준)
PORT=22                                      # EC2 SSH 포트
CONFIG_FILE="$HOME/.ssh/config"              # SSH 설정파일 경로

# 🔑 모든 인스턴스에 고정된 키 페어 이름을 사용
EC2_KEY_NAME="qb-frontier-global-key"
EC2_KEY_FILE="$HOME/.ssh/id_ed25519_github_qb_frontier"  # .pem 대신 실제 private key 사용

# ⭐ 개인 SSH 키 파일 우선순위 (Container 접속용)
# 첫 번째로 발견되는 키를 사용합니다
PERSONAL_SSH_KEY_FILES=(
    "$HOME/.ssh/id_ed25519_github_qb_frontier"  # 🔑 주 개발 키 (최우선)
    "$HOME/.ssh/id_ed25519"                      # 🔑 기본 ed25519 키
    "$HOME/.ssh/id_rsa"                          # 🔑 RSA 키 (백업)
    "$HOME/.ssh/id_ecdsa"                        # 🔑 ECDSA 키 (백업)
)

# =============================
# Functions
# =============================
find_personal_ssh_key() {
    for key_file in "${PERSONAL_SSH_KEY_FILES[@]}"; do
        if [ -f "$key_file" ]; then
            echo "$key_file"
            return 0
        fi
    done
    return 1
}

remove_existing_host() {
    local host_name="$1"
    local config_file="$2"
    
    if [ -f "$config_file" ] && grep -q "^Host $host_name$" "$config_file"; then
        echo "⚠️  기존 '$host_name' 설정을 제거합니다..."
        
        # Create backup
        cp "$config_file" "${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Remove existing host block
        awk -v host="$host_name" '
        BEGIN { skip = 0 }
        /^Host / { 
            if ($2 == host) {
                skip = 1
            } else {
                skip = 0
            }
        }
        /^$/ && skip { skip = 0 }
        !skip { print }
        ' "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
    fi
}

# =============================
# Validation
# =============================
echo "🔍 Finding primary SSH key for connections..."
PRIMARY_SSH_KEY=$(find_personal_ssh_key)

if [ -z "$PRIMARY_SSH_KEY" ]; then
    echo "❌ ERROR: Could not find a primary SSH private key."
    echo "   Please check if one of the following files exists:"
    for key_file in "${PERSONAL_SSH_KEY_FILES[@]}"; do
        echo "   - $key_file"
    done
    exit 1
fi
echo "✅ Using primary SSH key for all connections: $PRIMARY_SSH_KEY"

echo "🔍 Looking up Elastic IP from CloudFormation stack..."

# Get Elastic IP from CloudFormation
EIP=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='StaticIP'].OutputValue" \
  --output text 2>/dev/null)

if [ -z "$EIP" ] || [ "$EIP" = "None" ]; then
    echo "❌ ERROR: Elastic IP를 가져올 수 없습니다."
    echo "   - CloudFormation 스택 이름: $STACK_NAME"
    echo "   - 스택이 정상 배포되었는지 확인하세요."
    echo "   - AWS CLI 권한을 확인하세요."
    exit 1
fi

echo "✅ Elastic IP 발견: $EIP"

# =============================
# SSH Config Setup
# =============================
echo "📝 SSH config 설정 중..."

# Create .ssh directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"

# Remove existing host configuration if it exists
remove_existing_host "$ALIAS_NAME" "$CONFIG_FILE"
remove_existing_host "${ALIAS_NAME}-container" "$CONFIG_FILE"

# Prepare the new configuration block
NEW_CONFIG=$(cat <<EOF
# ${PROJECT_NAME} Development Environment - EC2 Instance
Host ${ALIAS_NAME}
    HostName ${EIP}
    User ${USER_NAME}
    Port ${PORT}
    IdentityFile ${PRIMARY_SSH_KEY}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

# ${PROJECT_NAME} Development Environment - Docker Container
Host ${ALIAS_NAME}-container
    HostName ${EIP}
    User devuser
    Port 2222
    IdentityFile ${PRIMARY_SSH_KEY}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

EOF
)

# Prepend the new configuration to the file
echo "${NEW_CONFIG}" | cat - "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

# Set proper permissions
chmod 600 "$CONFIG_FILE"
chmod 600 "$PRIMARY_SSH_KEY" 2>/dev/null || true

echo ""
echo "🎉 SSH config 설정 완료!"
echo ""
echo "📋 사용 가능한 연결:"
echo "   🖥️  EC2 인스턴스:     ssh ${ALIAS_NAME}"
echo "   🐳 Docker 컨테이너:   ssh ${ALIAS_NAME}-container"
echo ""
echo "🔗 추가 정보:"
echo "   📱 VSCode Web:        http://${EIP}:8080"
echo "   🔧 SSH Config:        ${CONFIG_FILE}"
echo "   🔑 Primary SSH Key:   ${PRIMARY_SSH_KEY}"

# =============================
# Connection Test
# =============================
echo ""
read -p "🔍 SSH 연결 테스트를 진행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⏳ EC2 인스턴스 연결 테스트 중..."
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$ALIAS_NAME" "echo 'SSH 연결 성공!'" 2>/dev/null; then
        echo "✅ EC2 SSH 연결 성공!"
    else
        echo "⚠️  EC2 SSH 연결 실패 (인스턴스 부팅 중일 수 있음)"
    fi
    
    echo "⏳ Docker 컨테이너 연결 테스트 중..."
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "${ALIAS_NAME}-container" "echo 'Container SSH 연결 성공!'" 2>/dev/null; then
        echo "✅ Container SSH 연결 성공!"
    else
        echo "⚠️  Container SSH 연결 실패 (컨테이너 준비 중일 수 있음)"
    fi
fi