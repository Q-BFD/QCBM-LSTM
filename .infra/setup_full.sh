#!/bin/bash
set -e

# -----------------------------
# 파라미터 파싱
# -----------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --project) PROJECT_NAME="$2"; shift ;;
    --instance-type) INSTANCE_TYPE="$2"; shift ;;
    --volume-size) VOLUME_SIZE="$2"; shift ;;
    --git) GIT_REPOSITORY="$2"; shift ;;
    --branch) GIT_BRANCH="$2"; shift ;;
    --ssh-key) SSHPublicKey="$2"; shift ;;
  esac
  shift
done

# 기본값
PROJECT_NAME="${PROJECT_NAME:-qcbm}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.large}"
VOLUME_SIZE="${VOLUME_SIZE:-50}"
GIT_REPOSITORY="${GIT_REPOSITORY:-https://github.com/Q-BFD/QCBM-LSTM.git}"
GIT_BRANCH="${GIT_BRANCH:-automation}"

# -----------------------------
# 이하 기존 UserData bash 코드 복붙 (로그 함수, 패키지 설치, EBS 마운트, Docker, Git, Jupyter, Docker build 등)
# -----------------------------

# ... (이전 UserData 전체 bash 코드가 여기에 들어갑니다) ...

# 예시: 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/${PROJECT_NAME}-setup.log
}

# ... 이하 전체 bash 로직 ... 