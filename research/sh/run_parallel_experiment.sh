#!/bin/bash

# =============================================================================
# QCBM-LSTM 병렬처리 최적화 실험 실행 스크립트
# =============================================================================

set -e  # 오류 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로고 출력
print_logo() {
    echo -e "${CYAN}"
    echo "🚀 =============================================== 🚀"
    echo "    QCBM-LSTM 병렬처리 최적화 실험 런처"
    echo "🚀 =============================================== 🚀"
    echo -e "${NC}"
}

# 도움말 출력
print_help() {
    echo -e "${YELLOW}사용법:${NC}"
    echo "  $0 [옵션]"
    echo ""
    echo -e "${YELLOW}옵션:${NC}"
    echo "  -h, --help        이 도움말 표시"
    echo "  -d, --dry-run     설정만 확인 (실제 실험 실행 안함)"
    echo "  -c, --config FILE 커스텀 설정 파일 사용"
    echo "  -q, --quick       빠른 테스트 (5 epochs)"
    echo "  -m, --minimal     최소 설정 (1 epoch, 작은 배치)"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo "  $0                              # 기본 설정으로 실행"
    echo "  $0 --dry-run                    # 설정만 확인"
    echo "  $0 --quick                      # 빠른 테스트"
    echo "  $0 --config my_settings.json    # 커스텀 설정"
    echo ""
    echo -e "${YELLOW}주요 기능:${NC}"
    echo "  ✅ xx배 빠른 reward_fc 최적화"
    echo "  ✅ 병렬 처리"
    echo "  ✅ Train/Test loss 분할"
    echo "  ✅ WandB 실시간 모니터링"
    echo "  ✅ QCBM 분포 시각화"
    echo "  ✅ 자동 성능 벤치마킹"
}

# 시스템 체크
check_requirements() {
    echo -e "${BLUE}🔍 환경 확인 중...${NC}"
    
    # Python 확인
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3가 설치되지 않았습니다.${NC}"
        exit 1
    fi
    
    # 필수 패키지 확인
    python3 -c "import torch, numpy, pandas" 2>/dev/null || {
        echo -e "${RED}❌ 필수 Python 패키지가 누락되었습니다.${NC}"
        echo "필요한 패키지: torch, numpy, pandas"
        exit 1
    }
    
    # psutil 확인 (성능 모니터링용)
    python3 -c "import psutil" 2>/dev/null || {
        echo -e "${YELLOW}⚠️ psutil 패키지가 없습니다. 성능 모니터링이 제한됩니다.${NC}"
        echo "설치 권장: pip install psutil"
    }
    
    echo -e "${GREEN}✅ 환경 확인 완료${NC}"
}

# 실험 디렉토리 이동
cd_to_project_root() {
    # 스크립트 위치에서 프로젝트 루트로 이동
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    PYTHON_DIR="$PROJECT_ROOT/python"
    
    if [[ ! -d "$PYTHON_DIR" ]]; then
        echo -e "${RED}❌ Python 디렉토리를 찾을 수 없습니다: $PYTHON_DIR${NC}"
        exit 1
    fi
    
    cd "$PYTHON_DIR"
    echo -e "${GREEN}📁 작업 디렉토리: $(pwd)${NC}"
}

# 빠른 테스트 설정 생성
create_quick_config() {
    cat > "settings/quick_parallel_test.json" << EOF
{
    "experiment_name": "qcbm_lstm_quick_test",
    "experiment_root": "./outputs/quick_test",
    "prior_model": "QCBM",
    "num_qubits": 6,
    "n_qcbm_layers": 3,
    "n_qcbm_shots": 500,
    "prior_n_epochs": 5,
    "n_lstm_layers": 1,
    "hidden_dim": 128,
    "embedding_dim": 64,
    "lstm_n_epochs": 5,
    "temprature": 0.7,
    "batch_size": 64,
    "test_fraction": 0.1,
    "n_test_samples": 5000,
    "fast_reward": "fast",
    "use_parallel_reward": true,
    "parallel_n_cores": 4,
    "parallel_chunk_size": 1000,
    "use_wandb": true,
    "wandb_project": "qcbm-lstm-quick-test"
}
EOF
    echo "settings/quick_parallel_test.json"
}

# 최소 설정 생성
create_minimal_config() {
    cat > "settings/minimal_parallel_test.json" << EOF
{
    "experiment_name": "qcbm_lstm_minimal_test",
    "experiment_root": "./outputs/minimal_test",
    "prior_model": "QCBM",
    "num_qubits": 4,
    "n_qcbm_layers": 2,
    "n_qcbm_shots": 100,
    "prior_n_epochs": 3,
    "n_lstm_layers": 1,
    "hidden_dim": 64,
    "embedding_dim": 32,
    "lstm_n_epochs": 1,
    "temprature": 0.7,
    "batch_size": 32,
    "test_fraction": 0.1,
    "n_test_samples": 1000,
    "fast_reward": "minimal",
    "use_parallel_reward": true,
    "parallel_n_cores": 2,
    "parallel_chunk_size": 500,
    "use_wandb": false
}
EOF
    echo "settings/minimal_parallel_test.json"
}

# 메인 실행 함수
run_experiment() {
    local config_file="$1"
    local dry_run="$2"
    
    echo -e "${PURPLE}🚀 실험 실행 시작...${NC}"
    echo -e "${BLUE}📄 설정 파일: $config_file${NC}"
    
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}🔍 DRY RUN 모드${NC}"
        python3 run_parallel_experiment.py --config "$config_file" --dry-run
    else
        echo -e "${GREEN}⚡ 실제 실험 실행${NC}"
        python3 run_parallel_experiment.py --config "$config_file"
    fi
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}🎉 실험이 성공적으로 완료되었습니다!${NC}"
    else
        echo -e "${RED}💥 실험 실행에 실패했습니다. (Exit code: $exit_code)${NC}"
        exit $exit_code
    fi
}

# 메인 로직
main() {
    local config_file="settings/parallel_experiment.json"
    local dry_run="false"
    local mode="default"
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_help
                exit 0
                ;;
            -d|--dry-run)
                dry_run="true"
                shift
                ;;
            -c|--config)
                config_file="$2"
                shift 2
                ;;
            -q|--quick)
                mode="quick"
                shift
                ;;
            -m|--minimal)
                mode="minimal"
                shift
                ;;
            *)
                echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}"
                echo "도움말: $0 --help"
                exit 1
                ;;
        esac
    done
    
    # 로고 출력
    print_logo
    
    # 시스템 체크
    check_requirements
    
    # 프로젝트 루트로 이동
    cd_to_project_root
    
    # 모드별 설정 파일 생성
    case $mode in
        "quick")
            echo -e "${YELLOW}🏃 빠른 테스트 모드${NC}"
            config_file=$(create_quick_config)
            ;;
        "minimal")
            echo -e "${YELLOW}⚡ 최소 테스트 모드${NC}"
            config_file=$(create_minimal_config)
            ;;
        "default")
            echo -e "${BLUE}📊 기본 설정 모드${NC}"
            ;;
    esac
    
    # 설정 파일 존재 확인
    if [[ ! -f "$config_file" ]]; then
        echo -e "${RED}❌ 설정 파일을 찾을 수 없습니다: $config_file${NC}"
        exit 1
    fi
    
    # 실험 실행
    run_experiment "$config_file" "$dry_run"
    
    # 완료 메시지
    echo ""
    echo -e "${CYAN}🎊 모든 작업이 완료되었습니다!${NC}"
    
    if [[ "$dry_run" == "false" ]]; then
        echo -e "${GREEN}📁 결과 확인: outputs/ 디렉토리${NC}"
        echo -e "${GREEN}📊 WandB 대시보드에서 실시간 결과 확인${NC}"
    fi
}

# 인터럽트 핸들러
trap 'echo -e "\n${YELLOW}⚠️ 사용자에 의해 중단되었습니다.${NC}"; exit 130' INT

# 메인 함수 실행
main "$@" 