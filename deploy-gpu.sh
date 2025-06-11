#!/bin/bash

# =============================
# 🚀 Quick Deploy - GPU Development Environment (Wrapper)
# =============================

# Display banner
echo "🚀 Quick Deploy for GPU Development Environment"
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
    echo "  -k, --ssh-key KEY_NAME       SSH 키 이름 (필수)"
    echo ""
    echo "Optional:"
    echo "  -p, --pricing TYPE           가격 모델: spot|ondemand (기본값: spot)"
    echo "  -i, --instance-type TYPE     GPU 인스턴스 타입 (기본값: g4dn.2xlarge)"
    echo "  -s, --spot-price PRICE       Spot 최대 가격 (기본값: 0.50)"
    echo "  -v, --volume-size SIZE       EBS 볼륨 크기 GB (기본값: 100)"
    echo "  -h, --help                   도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_john-doe"
    echo "  $0 qcbm -k id_ed25519_github_alice-kim --pricing ondemand"
    echo "  $0 qcbm -k /custom/path/key --pricing spot --instance-type g5.xlarge"
    echo "  $0 qcbm -k mykey --pricing spot --spot-price 0.30"
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
    echo "💰 가격 모델:"
    echo "  🟢 spot:     60-90% 비용 절약, 중단 가능성 있음 (권장)"
    echo "  🔵 ondemand: 안정적, 높은 비용"
    echo ""
    echo "🖥️  지원되는 GPU 인스턴스:"
    echo "  - g4dn.xlarge, g4dn.2xlarge, g4dn.4xlarge (NVIDIA T4)"
    echo "  - g5.xlarge, g5.2xlarge, g5.4xlarge (NVIDIA A10G)"
    echo "  - p3.2xlarge (NVIDIA V100 - 고성능)"
    echo ""
    echo "🎁 What this does:"
    echo "   ✅ Creates AWS GPU infrastructure (EC2, EBS, Security Groups)"
    echo "   ✅ Sets up GPU-enabled Docker development environment"
    echo "   ✅ Installs CUDA, PyTorch, Qiskit, and Jupyter"
    echo "   ✅ Configures SSH access"
    echo "   ✅ Provides VSCode Web interface"
    echo ""
    echo "💰 Cost Examples:"
    echo "   💸 g4dn.2xlarge Spot: ~\$0.30/hour (60-90% savings)"
    echo "   💵 g4dn.2xlarge OnDemand: ~\$1.20/hour"
    echo "   💸 g5.xlarge Spot: ~\$0.40/hour"
    echo "   💵 g5.xlarge OnDemand: ~\$1.60/hour"
    echo ""
    echo "⏱️  Setup time: ~8-10 minutes (GPU drivers + packages)"
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
    echo "  $0 PROJECT_NAME --ssh-key KEY_NAME [OPTIONS]"
    echo ""
    echo "예시:"
    echo "  $0 qcbm --ssh-key id_ed25519_github_yourname"
    echo "  $0 qcbm --ssh-key id_ed25519_github_yourname --pricing spot"
    echo ""
    echo "도움말: $0 --help"
    exit 1
fi

echo "🚀 Starting GPU deployment..."
echo "📁 Using infrastructure scripts from: ./.infra/"
echo ""

# Call the actual deployment script with all arguments
cd .infra && ./deploy-gpu.sh "$@"

# Check deployment result
DEPLOY_EXIT_CODE=$?
cd ..

if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 GPU Deployment completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Wait 8-10 minutes for GPU environment setup (CUDA drivers + packages)"
    echo "   2. Setup SSH: ./setup-ssh.sh PROJECT_NAME --ssh-key KEY_NAME"
    echo "   3. Connect: ssh PROJECT_NAME-container"
    echo ""
    echo "🌐 Access your GPU environment:"
    echo "   📊 Get your IP: cd .infra && aws cloudformation describe-stacks --stack-name PROJECT_NAME-dev-gpu-PRICING --query 'Stacks[0].Outputs[?OutputKey==\"StaticIP\"].OutputValue' --output text"
    echo "   🪐 Jupyter: http://YOUR_IP:8888 (token: qcbmtoken)"
    echo "   💻 VSCode Web: http://YOUR_IP:8080"
    echo ""
    echo "🔍 Monitor GPU setup: ssh ubuntu@YOUR_IP 'tail -f /var/log/PROJECT_NAME-setup.log'"
    echo ""
    echo "🎯 GPU Ready! Test with:"
    echo "   ssh PROJECT_NAME-container 'nvidia-smi'"
else
    echo ""
    echo "❌ GPU Deployment failed! Check the error messages above."
    echo ""
    echo "🔧 Common issues:"
    echo "   1. GPU quota limit: Check AWS Service Quotas for 'Running On-Demand G instances'"
    echo "   2. SSH key validation failed: Check key file exists and follows naming convention"
    echo "   3. AWS credentials: Verify with 'aws sts get-caller-identity'"
    exit 1
fi 