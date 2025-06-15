#!/bin/bash
# ==================================================================================
#                                 run_debug_molecule_screen.sh
# ==================================================================================
#  이 스크립트는 디버깅 세션을 터미널에서 직접 실행합니다.
#  어느 위치에서 실행하든 안정적으로 동작하도록 설계되었습니다.
# ==================================================================================

# --- 경로 설정 ---
# 스크립트 파일이 있는 디렉토리의 절대 경로를 찾습니다.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# 프로젝트 루트는 sh 디렉토리의 부모 디렉토리입니다.
PROJECT_ROOT=$( dirname -- "$SCRIPT_DIR" )

# 스크립트 실행 위치를 프로젝트 루트로 변경합니다.
# 이렇게 하면 모든 상대 경로가 올바르게 작동합니다.
cd "$PROJECT_ROOT" || exit

# --- 변수 설정 ---
PYTHON_SCRIPT="python/main.py"
CONFIG_FILE="python/settings/debug_molecule_screen_settings.json"

# --- 스크립트 실행 ---
echo "================================================================================"
echo "Starting Molecule Generation Debug Session (Foreground)"
echo "  - Project Root: $(pwd)"
echo "  - Python script: ${PYTHON_SCRIPT}"
echo "  - Config file: ${CONFIG_FILE}"
echo "================================================================================"
echo ""

# 파이썬 스크립트를 직접 실행하여 모든 출력을 터미널에 표시
# -u 옵션은 출력이 버퍼링되지 않도록 하여 즉시 표시되게 함
python -u ${PYTHON_SCRIPT} --config_file ${CONFIG_FILE}

echo ""
echo "================================================================================"
echo "Script execution finished."
echo "================================================================================"