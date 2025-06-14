#!/bin/bash

# =============================
# Generic SSH Config Setup Script
# =============================

# =====================================
# 사용법 표시 함수
# =====================================
show_usage() {
    echo "📋 Usage: $0 PROJECT_NAME [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -k, --ssh-key KEY_NAME    SSH 키 이름 (필수)"
    echo "  -h, --help               도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_john-doe"
    echo "  $0 myproject -k id_rsa_company_alice-kim"
    echo "  $0 qcbm -k /custom/path/my_key_ed25519_github_alice-kim"
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
    echo ""
    echo "📦 이 스크립트는 다음을 설정합니다:"
    echo "  - EC2 Instance: {PROJECT_NAME}"
    echo "  - Docker Container: {PROJECT_NAME}-container"
    exit 0
}

# =====================================
# 인자 파싱
# =====================================
PROJECT_NAME=""
SSH_KEY_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--ssh-key)
            SSH_KEY_NAME="$2"
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
    echo "   💡 deploy-cpu.sh에서 사용한 것과 동일한 키 이름을 사용하세요!"
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

# 사용자 이름 추출 (경로에서 키 이름만 추출)
if [[ "$SSH_KEY_NAME" == *"/"* ]]; then
    # Full path인 경우 파일명만 추출
    KEY_BASENAME=$(basename "$SSH_KEY_NAME")
else
    # 키 이름만인 경우 그대로 사용
    KEY_BASENAME="$SSH_KEY_NAME"
fi

DEV_USERNAME=$(extract_username_from_key "$KEY_BASENAME")

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
    SSH_PRIVATE_KEY_FILE="$HOME/.ssh/$SSH_KEY_NAME"
    SSH_PUBLIC_KEY_FILE="$HOME/.ssh/$SSH_KEY_NAME.pub"
fi

echo "🎯 Project Name: $PROJECT_NAME"
echo "🔑 SSH Key: $SSH_KEY_NAME"
echo "👤 Dev User: $DEV_USERNAME"
echo "📁 SSH Private Key: $SSH_PRIVATE_KEY_FILE"

# =============================
# Configuration Variables
# =============================
STACK_NAME="${PROJECT_NAME}-dev-cpu"        # CloudFormation 스택 이름 (deploy-cpu.sh와 일치)
ALIAS_NAME="$PROJECT_NAME"                   # SSH 별칭
USER_NAME="ubuntu"                           # EC2 기본 사용자 (Ubuntu 기준)
PORT=22                                      # EC2 SSH 포트
CONFIG_FILE="$HOME/.ssh/config"              # SSH 설정파일 경로

# ⭐ 사용할 개인 SSH 키 파일 우선순위 (동적으로 생성)
PERSONAL_SSH_KEY_FILES=(
    "$SSH_PRIVATE_KEY_FILE"                  # 🔑 주 개발 키 (최우선)
    "$HOME/.ssh/id_ed25519"                  # 🔑 기본 ed25519 키
    "$HOME/.ssh/id_rsa"                      # 🔑 RSA 키 (백업)
    "$HOME/.ssh/id_ecdsa"                    # 🔑 ECDSA 키 (백업)
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
    echo ""
    echo "💡 If you need to update the SSH key name, use:"
    echo "   $0 $PROJECT_NAME --ssh-key YOUR_KEY_NAME"
    echo "   This should match the key name used in deploy-cpu.sh"
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
    echo ""
    echo "💡 스택을 먼저 배포해야 합니다:"
    echo "   ./deploy-cpu.sh $PROJECT_NAME --ssh-key $SSH_KEY_NAME"
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
    User ${DEV_USERNAME}
    Port 2222
    IdentityFile ${PRIMARY_SSH_KEY}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    SendEnv LANG LC_*

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
echo "   🐳 Docker 컨테이너:   ssh ${ALIAS_NAME}-container (User: ${DEV_USERNAME})"
echo ""
echo "🔗 추가 정보:"
echo "   📱 VSCode Web:        http://${EIP}:8080"
echo "   📱 JupyterLab:        http://${EIP}:8888 (token: qcbmtoken)"
echo "   🔧 SSH Config:        ${CONFIG_FILE}"
echo "   🔑 Primary SSH Key:   ${PRIMARY_SSH_KEY}"

# =============================
# Connection Test
# =============================
echo ""
read -p "🔍 EC2 인스턴스 연결 테스트를 진행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⏳ EC2 인스턴스 연결 테스트 중 (최대 10초 대기)..."
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$ALIAS_NAME" "echo '✅ EC2 SSH 연결 성공!'" 2>/dev/null; then
        echo "🎉 EC2 인스턴스 접속이 확인되었습니다."
        echo "   (Docker 컨테이너는 백그라운드에서 준비 중입니다. 몇 분 정도 소요될 수 있습니다.)"
    else
        echo "❌ EC2 SSH 연결에 실패했습니다!"
        echo "   인스턴스가 아직 부팅 중이거나 네트워크(보안 그룹) 문제가 있을 수 있습니다."
        echo ""
        echo "   [문제 해결 가이드]"
        echo "   1. AWS 콘솔에서 '${ALIAS_NAME}' 인스턴스 상태가 'running'이고 '2/2 상태 검사 통과'인지 확인하세요."
        echo "   2. 보안 그룹에서 포트 22가 열려 있는지 확인하세요."
        echo "   3. 잠시 후 EC2 연결을 먼저 수동으로 테스트해보세요: ssh ${ALIAS_NAME}"
        exit 1
    fi
fi

echo ""
echo "🎯 요약:"
echo "   📦 프로젝트: $PROJECT_NAME"
echo "   🔑 SSH 키: $SSH_KEY_NAME"
echo "   👤 사용자: $DEV_USERNAME"
echo "   🌐 IP: $EIP"
echo ""
echo "🚀 이제 다음 명령으로 접속할 수 있습니다:"
echo "   ssh ${ALIAS_NAME}-container"