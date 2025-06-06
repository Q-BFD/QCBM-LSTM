#!/bin/bash

# =============================
# Configuration Variables
# =============================
STACK_NAME="qcbm-dev-cpu"              # CloudFormation 스택 이름 (deploy.sh와 일치)
ALIAS_NAME="qcbm"                        # SSH 별칭
USER_NAME="ubuntu"                       # EC2 기본 사용자 (Ubuntu 기준)
PORT=22                                  # EC2 SSH 포트
CONFIG_FILE="$HOME/.ssh/config"          # SSH 설정파일 경로

# SSH 키 파일 설정
EC2_KEY_NAME="qcbm-dev-key"              # EC2 Key Pair 이름
EC2_KEY_FILE="$HOME/.ssh/${EC2_KEY_NAME}.pem"  # EC2 접속용 키

# 개인 SSH 키 파일 자동 감지 (우선순위: ed25519 > rsa > ecdsa)
PERSONAL_SSH_KEY_FILES=(
    "$HOME/.ssh/id_ed25519"
    "$HOME/.ssh/id_ed25519_github_qb_frontier"
    "$HOME/.ssh/id_rsa"
    "$HOME/.ssh/id_ecdsa"
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
echo "🔍 CloudFormation 스택에서 Elastic IP 조회 중..."

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

# Find EC2 Key Pair
echo "🔍 EC2 Key Pair 파일 확인 중..."
if [ ! -f "$EC2_KEY_FILE" ]; then
    echo "❌ ERROR: EC2 Key Pair 파일을 찾을 수 없습니다: $EC2_KEY_FILE"
    echo "   다음 명령으로 Key Pair를 생성하세요:"
    echo "   aws ec2 create-key-pair --key-name $EC2_KEY_NAME --query 'KeyMaterial' --output text > $EC2_KEY_FILE"
    echo "   chmod 600 $EC2_KEY_FILE"
    exit 1
fi
echo "✅ EC2 Key Pair 발견: $EC2_KEY_FILE"

# Find personal SSH private key for Docker container
echo "🔍 개인 SSH 키 파일 검색 중..."
PERSONAL_SSH_KEY=$(find_personal_ssh_key)

if [ -z "$PERSONAL_SSH_KEY" ]; then
    echo "❌ ERROR: 개인 SSH 키 파일을 찾을 수 없습니다."
    echo "   다음 위치를 확인하세요:"
    for key_file in "${PERSONAL_SSH_KEY_FILES[@]}"; do
        echo "   - $key_file"
    done
    echo ""
    echo "   SSH 키가 없다면 다음 명령으로 생성하세요:"
    echo "   ssh-keygen -t ed25519 -C 'your_email@example.com'"
    exit 1
fi

echo "✅ 개인 SSH 키 발견: $PERSONAL_SSH_KEY"

# =============================
# SSH Config Setup
# =============================
echo "📝 SSH config 설정 중..."

# Create .ssh directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"

# Remove existing host configuration if it exists
remove_existing_host "$ALIAS_NAME" "$CONFIG_FILE"
remove_existing_host "${ALIAS_NAME}-container" "$CONFIG_FILE"

# Add new SSH config entry
cat <<EOF >> "$CONFIG_FILE"

# QCBM Development Environment - EC2 Instance
Host ${ALIAS_NAME}
    HostName ${EIP}
    User ${USER_NAME}
    Port ${PORT}
    IdentityFile ${EC2_KEY_FILE}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

# QCBM Development Environment - Docker Container
Host ${ALIAS_NAME}-container
    HostName ${EIP}
    User devuser
    Port 2222
    IdentityFile ${PERSONAL_SSH_KEY}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
EOF

# Set proper permissions
chmod 600 "$CONFIG_FILE"
chmod 600 "$EC2_KEY_FILE" 2>/dev/null || true
chmod 600 "$PERSONAL_SSH_KEY" 2>/dev/null || true

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
echo "   🔑 EC2 Key:           ${EC2_KEY_FILE}"
echo "   🔑 Personal Key:      ${PERSONAL_SSH_KEY}"

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