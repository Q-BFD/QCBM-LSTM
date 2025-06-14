#!/bin/bash

# 스크립트의 절대 경로를 기준으로 `research` 디렉토리를 찾습니다.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
RESEARCH_DIR="$( dirname "$SCRIPT_DIR" )"
PYTHON_DIR="$RESEARCH_DIR/python"

# 설정 파일 경로
CONFIG_FILE="settings/full_settings.json"
FULL_CONFIG_PATH="$PYTHON_DIR/$CONFIG_FILE"

# 최종 테스트를 위한 안내 메시지
echo "=================================================="
echo "🚀 최종 통합 테스트 스크립트 실행"
echo "=================================================="
echo "  - Python 실행 경로: $PYTHON_DIR"
echo "  - 사용할 설정 파일: $CONFIG_FILE"
echo ""

# 설정 파일 존재 여부 확인
if [ ! -f "$FULL_CONFIG_PATH" ]; then
    echo "❌ 에러: 설정 파일을 찾을 수 없습니다!"
    echo "   경로: $FULL_CONFIG_PATH"
    exit 1
fi

# 파이썬 스크립트 실행
# python 디렉토리로 이동하여 실행해야 상대 경로 import 문제를 피할 수 있습니다.
cd "$PYTHON_DIR" && python main.py --config_file "$CONFIG_FILE"

# 실행 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 최종 테스트가 성공적으로 완료되었습니다."
else
    echo ""
    echo "❌ 최종 테스트 실행 중 오류가 발생했습니다."
fi 