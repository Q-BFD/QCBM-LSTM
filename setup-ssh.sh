#!/bin/bash

# =============================
# 🔧 SSH Setup - Development Environment (Wrapper)
# =============================

# Display banner
echo "🔧 SSH Setup for Development Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .infra directory exists
if [ ! -d ".infra" ]; then
    echo "❌ Error: .infra directory not found!"
    echo "   Please run this command from the project root directory."
    exit 1
fi

# Show usage if help requested or if run without arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ $# -eq 0 ]; then
    echo "📋 Usage: $0 PROJECT_NAME [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -k, --ssh-key KEY_NAME    SSH 키 이름 (필수)"
    echo ""
    echo "Optional:"
    echo "  -h, --help               도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_john-doe"
    echo "  $0 myproject -k id_rsa_company_alice-kim"
    echo "  $0 qcbm -k /custom/path/my_key"
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
    echo "📦 This will configure SSH access to:"
    echo "   - EC2 Instance: PROJECT_NAME"
    echo "   - Docker Container: PROJECT_NAME-container"
    echo ""
    echo "💡 Note: Run this after successful deployment with deploy-cpu.sh"
    echo "📁 Infrastructure files: ./.infra/"
    exit 0
fi

# Validate that SSH key argument is provided
SSH_KEY_PROVIDED=false
for arg in "$@"; do
    if [[ "$arg" == "--ssh-key" ]] || [[ "$arg" == "-k" ]]; then
        SSH_KEY_PROVIDED=true
        break
    fi
done

if [ "$SSH_KEY_PROVIDED" = false ]; then
    echo "❌ ERROR: SSH 키 이름이 필요합니다."
    echo ""
    echo "사용법:"
    echo "  $0 PROJECT_NAME --ssh-key KEY_NAME"
    echo ""
    echo "예시:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_yourname"
    echo ""
    echo "💡 deploy-cpu.sh에서 사용한 것과 동일한 키 이름을 사용하세요!"
    echo ""
    echo "도움말: $0 --help"
    exit 1
fi

# --- Argument parsing for user-friendly output ---
PROJECT_NAME_FOR_OUTPUT=""
for arg in "$@"; do
    if [[ "$arg" != -* ]]; then
        PROJECT_NAME_FOR_OUTPUT="$arg"
        break
    fi
done
# --- End of parsing ---

echo "🚀 Starting SSH configuration..."
echo "📁 Using infrastructure scripts from: ./.infra/"
echo ""

# Call the actual SSH setup script with all arguments
cd .infra && ./setup_ssh_config.sh "$@"

# Check setup result
SETUP_EXIT_CODE=$?
cd ..

if [ $SETUP_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 SSH configuration for EC2 instance completed successfully!"
    echo ""
    echo "🚀 You can now connect to the EC2 instance using:"
    echo "   ssh ${PROJECT_NAME_FOR_OUTPUT}"
    echo ""
    echo "💡 The Docker container is still setting up in the background."
    echo "   After a few minutes, connect to the container using:"
    echo "   ssh ${PROJECT_NAME_FOR_OUTPUT}-container"
else
    echo ""
    echo "❌ SSH setup failed! Check the error messages above."
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Make sure the EC2 instance is deployed first: ./deploy-cpu.sh"
    echo "   2. Check that the same SSH key name is used in both scripts"
    echo "   3. Verify AWS CLI is configured: aws sts get-caller-identity"
    exit 1
fi 