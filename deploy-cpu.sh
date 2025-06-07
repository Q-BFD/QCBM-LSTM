#!/bin/bash

# =============================
# 🚀 Quick Deploy - CPU Development Environment
# =============================

# Display banner
echo "🎯 Quick Deploy for Development Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .infra directory exists
if [ ! -d ".infra" ]; then
    echo "❌ Error: .infra directory not found!"
    echo "   Please run this command from the project root directory."
    exit 1
fi

# Show usage if help requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 [PROJECT_NAME] [INSTANCE_TYPE]"
    echo ""
    echo "Examples:"
    echo "   $0 qcbm                 # 기본 t3.large"
    echo "   $0 qcbm t3.xlarge       # 4 vCPU 16GB"
    echo "   $0 myproj c5.xlarge     # CPU 최적화"
    echo "   $0 myproject     # Deploy custom project"
    echo "   $0               # Deploy with default name 'qcbm'"
    echo ""
    echo "🎁 What this does:"
    echo "   ✅ Creates AWS infrastructure (EC2, EBS, Security Groups)"
    echo "   ✅ Sets up Docker development environment"
    echo "   ✅ Installs Python packages and Jupyter"
    echo "   ✅ Configures SSH access"
    echo "   ✅ Provides VSCode Web interface"
    echo ""
    echo "💰 Cost: ~$0.09/hour (t3.large + 50GB EBS)"
    echo "⏱️  Setup time: ~5 minutes"
    exit 0
fi

# Parse arguments
PROJECT_NAME="$1"
INSTANCE_TYPE="${2:-t3.large}"
if [ -z "$PROJECT_NAME" ]; then
  echo "❌ Project name required. Usage: $0 <PROJECT_NAME> [INSTANCE_TYPE]"; exit 1; fi

echo "🎯 Project: $PROJECT_NAME"
echo "📁 Infrastructure files: ./.infra/"
echo ""

# Call the actual deployment script
echo "🚀 Starting deployment..."
cd .infra && ./deploy-cpu.sh "$PROJECT_NAME" "$INSTANCE_TYPE"

# Check deployment result
if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Wait 3-5 minutes for environment setup"
    echo "   2. Setup SSH: ./setup-ssh.sh $PROJECT_NAME"
    echo "   3. Connect: ssh $PROJECT_NAME"
    echo "   4. Or use: ssh ${PROJECT_NAME}-container"
    echo ""
    echo "🌐 Access your environment:"
    echo "   📊 Get your IP: cd .infra && aws cloudformation describe-stacks --stack-name ${PROJECT_NAME}-dev-cpu --query 'Stacks[0].Outputs[?OutputKey==\"StaticIP\"].OutputValue' --output text"
    echo "   🪐 Jupyter: http://YOUR_IP:8888 (token: ${PROJECT_NAME}token)"
    echo "   💻 VSCode Web: http://YOUR_IP:8080"
    echo ""
    echo "🔍 Monitor setup: ssh $PROJECT_NAME 'tail -f /var/log/${PROJECT_NAME}-setup.log'"
else
    echo ""
    echo "❌ Deployment failed! Check the error messages above."
    exit 1
fi 