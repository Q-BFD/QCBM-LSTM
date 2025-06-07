#!/bin/bash

# =============================
# 🔑 Quick SSH Setup
# =============================

# Display banner
echo "🔑 Quick SSH Configuration Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .infra directory exists
if [ ! -d ".infra" ]; then
    echo "❌ Error: .infra directory not found!"
    echo "   Please run this command from the project root directory."
    exit 1
fi

# Show usage if help requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "📋 Usage: $0 [PROJECT_NAME]"
    echo ""
    echo "Examples:"
    echo "   $0 qcbm          # Setup SSH for QCBM project"
    echo "   $0 myproject     # Setup SSH for custom project"
    echo "   $0               # Setup SSH for default 'qcbm'"
    echo ""
    echo "🔑 What this does:"
    echo "   ✅ Configures SSH access to EC2 instance"
    echo "   ✅ Configures SSH access to Docker container"
    echo "   ✅ Updates ~/.ssh/config automatically"
    echo "   ✅ Tests connections"
    exit 0
fi

PROJECT_NAME="${1:-qcbm}"
echo "🎯 Project: $PROJECT_NAME"
echo "📁 Infrastructure files: ./.infra/"
echo ""

# Call the actual SSH setup script
echo "🔑 Setting up SSH configuration..."
cd .infra && ./setup_ssh_config.sh "$PROJECT_NAME"

# Check setup result
if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 SSH setup completed successfully!"
    echo ""
    echo "🚀 Ready to connect:"
    echo "   🖥️  EC2 instance:     ssh $PROJECT_NAME"
    echo "   🐳 Docker container:  ssh ${PROJECT_NAME}-container"
    echo ""
    echo "💡 Quick test:"
    echo "   ssh $PROJECT_NAME 'echo \"Hello from EC2!\"'"
    echo "   ssh ${PROJECT_NAME}-container 'echo \"Hello from container!\"'"
else
    echo ""
    echo "❌ SSH setup failed! Check the error messages above."
    exit 1
fi 