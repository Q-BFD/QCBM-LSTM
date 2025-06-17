#!/bin/bash

# =============================
# 🚀 Quick Deploy - CPU Development Environment (Wrapper)
# =============================

# Display banner
echo "🎯 Quick Deploy for CPU Development Environment"
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
    echo "  -i, --instance-type TYPE  CPU 인스턴스 타입 (기본값: c5.xlarge)"
    echo "  -v, --volume-size SIZE    EBS 볼륨 크기 GB (기본값: 100)"
    echo "  -h, --help               도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 kyle-research --ssh-key id_ed25519_github_john-doe"
    echo "  $0 kyle-research -k id_rsa_company_alice-kim --instance-type m7i.2xlarge"
    echo "  $0 kyle-research -k /custom/path/my_key -i c5.2xlarge -v 100"
    echo "  $0 kyle-research -k id_ed25519_github_yourname -i m7i.2xlarge -v 200"
    echo "  $0 kyle-research -k id_ed25519_github_yourname -i c5.9xlarge -v 200"
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
    echo "🖥️  지원되는 CPU 인스턴스:"
    echo "  - t3.medium, t3.large, t3.xlarge, t3.2xlarge (일반 목적)"
    echo "  - c5.large, c5.xlarge, c5.2xlarge, c5.4xlarge, c5.9xlarge (컴퓨팅 최적화)"
    echo "  - m5.large, m5.xlarge, m5.2xlarge (균형잡힌 성능)"
    echo "  - m7i.2xlarge, m7i.4xlarge (최신 세대)"
    echo ""
    echo "🎁 What this does:"
    echo "   ✅ Creates AWS infrastructure (EC2, EBS, Security Groups)"
    echo "   ✅ Sets up Docker development environment"
    echo "   ✅ Installs Python packages and Jupyter"
    echo "   ✅ Configures SSH access"
    echo "   ✅ Provides VSCode Web interface"
    echo ""
    echo "💰 Cost Examples:"
    echo "   💸 t3.large: ~$0.09/hour (2 vCPU, 8GB RAM)"
    echo "   💸 t3.xlarge: ~$0.18/hour (4 vCPU, 16GB RAM)"
    echo "   💸 c5.2xlarge: ~$0.34/hour (8 vCPU, 16GB RAM, 컴퓨팅 최적화)"
    echo "   💸 c5.9xlarge: ~$0.95/hour (36 vCPU, 72GB RAM, 병렬처리 최적화)"
    echo "   💸 m7i.2xlarge: ~$0.40/hour (8 vCPU, 32GB RAM, 최신 세대)"
    echo ""
    echo "⏱️  Setup time: ~5 minutes"
    echo ""
    echo "📁 Infrastructure files: ./.infra/"
    exit 0
fi

# --- Argument parsing for user-friendly output ---
PROJECT_NAME=""
SSH_KEY_NAME=""
# Create a temporary copy of arguments to avoid modifying the original $@
TEMP_ARGS=("$@")
while [[ ${#TEMP_ARGS[@]} -gt 0 ]]; do
    case ${TEMP_ARGS[0]} in
        -k|--ssh-key)
            SSH_KEY_NAME="${TEMP_ARGS[1]}"
            # Simulate shift 2
            TEMP_ARGS=("${TEMP_ARGS[@]:2}")
            ;;
        -i|--instance-type|-v|--volume-size)
             # Simulate shift 2
             TEMP_ARGS=("${TEMP_ARGS[@]:2}")
            ;;
        -h|--help)
             # Simulate shift
             TEMP_ARGS=("${TEMP_ARGS[@]:1}")
            ;;
        -*)
            # unknown option, the inner script will handle it
            TEMP_ARGS=("${TEMP_ARGS[@]:1}")
            ;;
        *)
            if [ -z "$PROJECT_NAME" ]; then
                PROJECT_NAME="${TEMP_ARGS[0]}"
            fi
            # Simulate shift
            TEMP_ARGS=("${TEMP_ARGS[@]:1}")
            ;;
    esac
done
# --- End of parsing ---

# Validate that SSH key argument is provided (using parsed value)
if [ -z "$PROJECT_NAME" ] || [ -z "$SSH_KEY_NAME" ]; then
    echo "❌ ERROR: 프로젝트 이름과 SSH 키 이름이 모두 필요합니다."
    echo ""
    echo "사용법:"
    echo "  $0 PROJECT_NAME --ssh-key KEY_NAME"
    echo ""
    echo "예시:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_yourname"
    echo ""
    echo "도움말: $0 --help"
    exit 1
fi

echo "🚀 Starting CPU deployment..."
echo "📁 Using infrastructure scripts from: ./.infra/"
echo ""

# Call the actual deployment script with all original arguments
cd .infra && ./deploy-cpu.sh "$@"

# Check deployment result
DEPLOY_EXIT_CODE=$?
cd ..

if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Wait 3-5 minutes for environment setup"
    echo "   2. Setup SSH: ./setup-ssh.sh ${PROJECT_NAME} --ssh-key ${SSH_KEY_NAME}"
    echo "   3. Connect: ssh ${PROJECT_NAME}-container"
    echo ""
    echo "🌐 Access your environment:"
    IP_ADDRESS=$(aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-dev-cpu" --query "Stacks[0].Outputs[?OutputKey=='StaticIP'].OutputValue" --output text 2>/dev/null)
    if [ -n "$IP_ADDRESS" ] && [ "$IP_ADDRESS" != "None" ]; then
        echo "   📊 IP Address: ${IP_ADDRESS}"
        echo "   🪐 Jupyter: http://${IP_ADDRESS}:8888 (token: qcbmtoken)"
        echo "   💻 VSCode Web: http://${IP_ADDRESS}:8080"
        echo ""
        echo "🔍 Monitor setup: ssh ubuntu@${IP_ADDRESS} 'tail -f /var/log/${PROJECT_NAME}-setup.log'"
    else
        echo "   (Could not fetch IP automatically. Please check the AWS Console.)"
    fi
else
    echo ""
    echo "❌ Deployment failed! Check the error messages above."
    exit 1
fi
