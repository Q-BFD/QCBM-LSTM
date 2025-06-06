# QCBM-LSTM

## 프로젝트 소개

이 프로젝트는 Quantum Circuit Born Machine (QCBM)과 Long Short-Term Memory (LSTM) 네트워크를 결합한 하이브리드 양자-클래식 머신러닝 모델을 구현합니다.

## 주요 기능

- QCBM을 이용한 양자 회로 기반 생성 모델
- LSTM을 이용한 시계열 데이터 처리
- 양자-클래식 하이브리드 학습 알고리즘

## 설치 방법

```bash
# 필요한 패키지 설치
pip install -r requirements.txt
```

## 프로젝트 구조

```
QCBM-LSTM/
├── data/               # 데이터 파일
├── models/            # 모델 구현
├── utils/             # 유틸리티 함수
└── notebooks/         # 주피터 노트북
```

# QCBM-LSTM AWS 개발 환경

이 프로젝트는 **QCBM (Quantum Circuit Born Machine)과 LSTM**을 활용한 양자 머신러닝 연구를 위한 **완전 자동화된 AWS 클라우드 개발 환경**을 제공합니다.

**🚀 원클릭 배포**로 CloudFormation을 사용하여 EC2 인스턴스에 Docker 기반 개발 환경을 자동으로 구축하고, VSCode Remote SSH를 통해 즉시 원격 개발이 가능합니다.

## 🏗️ 인프라 구성

- **EC2 인스턴스**: Ubuntu 22.04 기반 개발 서버
- **Docker 컨테이너**: 격리된 개발 환경 (자동 구성)
- **EBS 볼륨**: 영구 데이터 저장 (자동 감지 및 마운트)
- **Elastic IP**: 고정 IP 주소
- **Security Group**: SSH, VSCode, Docker 포트 개방

## ✨ 완전 자동화 기능

### 🎯 **원클릭 배포**

- ✅ **EBS 볼륨 자동 감지** (`/dev/nvme1n1`, `/dev/xvdf` 등 자동 처리)
- ✅ **자동 포맷 및 마운트**
- ✅ **Git 리포지토리 자동 클론**
- ✅ **Docker 이미지 자동 빌드**
- ✅ **컨테이너 자동 실행**
- ✅ **SSH 키 자동 주입**
- ✅ **Python 패키지 자동 설치**
- ✅ **VSCode Server 자동 설정**

### 📦 **사전 구성된 개발 환경**

- **양자 컴퓨팅**: Qiskit, Qiskit Aer
- **머신러닝**: PyTorch, Scikit-learn
- **데이터 분석**: NumPy, Pandas, Matplotlib
- **개발 도구**: Jupyter Notebook, VSCode Server

## 📋 사전 준비사항

### 1. AWS 설정

```bash
# AWS CLI 설치 및 설정
aws configure
```

### 2. SSH 키 생성 (없는 경우)

```bash
# ED25519 키 생성 (권장)
ssh-keygen -t ed25519 -C "your_email@example.com"

# 또는 RSA 키 생성
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 3. AWS EC2 Key Pair 생성

AWS Console에서 EC2 Key Pair를 생성하거나 기존 키를 사용하세요.

## 🔑 SSH 키 구조 및 역할

이 프로젝트는 **두 종류의 SSH 키**를 사용하여 보안성과 편의성을 모두 확보합니다.

### 📋 SSH 키 구조

```
📁 SSH Keys
├── ~/.ssh/qcbm-dev-key.pem                      # AWS EC2 Key Pair (EC2 접속용)
└── ~/.ssh/id_ed25519_github_qb_frontier.pub     # 개인 SSH Key (Docker 개발용)
```

### 🏗️ 전체 접속 아키텍처

```
로컬 개발자
    ↓ (AWS EC2 Key Pair)
EC2 인스턴스 (Ubuntu)
    ↓ (개인 SSH Key 자동 주입)
Docker 컨테이너 (개발환경)
```

### 🔐 두 키의 역할

#### 1️⃣ AWS EC2 Key Pair (`qcbm-dev-key`)

**목적**: EC2 인스턴스에 **최초 접속**하기 위한 키

```bash
# 직접 EC2 인스턴스 접속 (서버 관리용)
ssh -i ~/.ssh/qcbm-dev-key.pem ubuntu@[EC2-IP]

# 또는 SSH config 설정 후
ssh qcbm
```

**특징**:

- ✅ AWS에서 관리하는 공식 Key Pair
- ✅ EC2 인스턴스 생성 시 자동으로 `ubuntu` 사용자에 주입
- ✅ 서버 관리, 로그 확인, Docker 관리 등에 사용

#### 2️⃣ 개인 SSH Key (`id_ed25519_github_qb_frontier`)

**목적**: Docker 컨테이너에서 **개발 작업**을 위한 키

```bash
# Docker 컨테이너 직접 접속 (개발용)
ssh qcbm-container

# VSCode Remote SSH 연결
# VSCode → Remote-SSH → qcbm-container
```

**특징**:

- ✅ 개인이 생성한 SSH 키
- ✅ CloudFormation 배포 시 컨테이너에 **자동 주입**
- ✅ VSCode Remote SSH, 개발 작업에 최적화
- ✅ GitHub 등 다른 서비스와 동일한 키 재사용 가능

### 🔄 Key Pair 생성 시점

#### ✅ **한 번만 생성하면 됨**

```bash
# 자동 생성 (deploy.sh가 확인 후 없으면 자동 생성)
./deploy.sh

# 또는 수동 생성
aws ec2 create-key-pair --key-name qcbm-dev-key \
  --query 'KeyMaterial' --output text > ~/.ssh/qcbm-dev-key.pem
chmod 600 ~/.ssh/qcbm-dev-key.pem
```

#### 🔄 **언제 새로 만들어야 하나?**

1. **처음 AWS 사용할 때**
2. **다른 리전 사용할 때** (Key Pair는 리전별 관리)
3. **보안상 교체가 필요할 때**
4. **팀원별로 다른 키를 사용할 때**

### 🚀 자동화된 Key Pair 관리

`deploy.sh` 스크립트는 **Key Pair를 자동으로 관리**합니다:

```bash
🔍 Checking AWS EC2 Key Pair: qcbm-dev-key
✅ Key Pair 'qcbm-dev-key' already exists        # 이미 있으면 재사용
# 또는
⚠️  Key Pair 'qcbm-dev-key' not found. Creating new one...
✅ Key Pair created successfully: ~/.ssh/qcbm-dev-key.pem
```

### 🛡️ 보안 고려사항

#### AWS EC2 Key Pair

- ❗ **Private Key (`.pem`) 파일은 절대 공유하지 마세요**
- ✅ 권한을 `600`으로 설정 (소유자만 읽기/쓰기)
- ✅ 버전 관리(Git)에 포함하지 마세요

#### 개인 SSH Key

- ✅ 기존에 사용하던 안전한 키 재사용 권장
- ✅ Public Key만 AWS에 전송됨 (Private Key는 로컬에만)
- ✅ GitHub, GitLab 등과 동일한 키 사용 가능

### 📊 키별 접속 방법 비교

| 키 종류          | 접속 대상       | 주요 용도         | 접속 방법                                  |
| ---------------- | --------------- | ----------------- | ------------------------------------------ |
| **EC2 Key Pair** | EC2 인스턴스    | 서버 관리, 디버깅 | `ssh qcbm`                                 |
| **개인 SSH Key** | Docker 컨테이너 | 개발 작업         | `ssh qcbm-container`<br/>VSCode Remote SSH |

## 🚀 원클릭 배포 과정

### 1단계: 설정 수정

`deploy.sh` 파일의 설정을 수정하세요:

```bash
# deploy.sh 파일 수정
KEY_NAME="your-actual-key-pair-name"    # AWS EC2 Key Pair 이름
SSH_PUBLIC_KEY_FILE="~/.ssh/id_ed25519.pub"  # SSH public key 파일 경로
```

### 2단계: 원클릭 배포

```bash
# 실행 권한 부여
chmod +x deploy.sh

# 원클릭 배포 (모든 것이 자동화됨!)
./deploy.sh
```

**🎉 자동으로 완료되는 작업들:**

- ✅ EC2 인스턴스 생성 (t3.medium)
- ✅ EBS 볼륨 생성 및 자동 마운트 (50GB)
- ✅ Elastic IP 할당
- ✅ Security Group 설정
- ✅ Git 리포지토리 클론
- ✅ Docker 이미지 빌드
- ✅ Docker 컨테이너 실행
- ✅ SSH 키 자동 주입
- ✅ Python 패키지 설치
- ✅ VSCode Server 설정
- ✅ **개발 환경 완료!**

### 3단계: SSH 설정

```bash
# 실행 권한 부여
chmod +x setup_ssh_config.sh

# SSH 설정 실행
./setup_ssh_config.sh
```

**생성되는 SSH 설정:**

```
Host qcbm                    # EC2 인스턴스 접속
Host qcbm-container         # Docker 컨테이너 접속
```

## 💻 개발 환경 접속

### 방법 1: VSCode Remote SSH (권장)

1. **VSCode에서 Remote-SSH 확장 설치**
2. **Command Palette** (`Cmd+Shift+P`)
3. **"Remote-SSH: Connect to Host..."** 선택
4. **`qcbm-container`** 선택
5. 🎉 **Docker 컨테이너에 직접 연결!**

### 방법 2: 터미널 SSH

```bash
# EC2 인스턴스 접속 (서버 관리)
ssh qcbm

# Docker 컨테이너 접속 (개발 작업)
ssh qcbm-container
```

### 방법 3: VSCode Web (브라우저)

```
http://[ELASTIC_IP]:8080
# 비밀번호: qcbmpassword
```

## 📁 프로젝트 구조

```
QCBM-LSTM/
├── cloudformation.yml          # AWS 인프라 정의 (완전 자동화)
├── deploy.sh                   # 원클릭 배포 스크립트
├── setup_ssh_config.sh         # SSH 설정 스크립트
├── Dockerfile                  # Docker 이미지 정의 (자동 SSH 설정)
├── requirements.txt            # Python 의존성 (양자 ML 패키지)
├── README.md                   # 이 파일
└── [연구 코드들...]            # 자동으로 /home/devuser/workspace에 마운트
```

## 🔧 주요 기능

### 🎯 완전 자동화된 배포

- ✅ **원클릭 배포**: `./deploy.sh` 한 번으로 전체 환경 구축
- ✅ **스마트 EBS 마운트**: 디바이스 이름 자동 감지 (`/dev/nvme1n1`, `/dev/xvdf` 등)
- ✅ **SSH 키 자동 주입**: 로컬 SSH 키를 자동으로 컨테이너에 주입
- ✅ **영구 스토리지**: EBS 볼륨으로 데이터 영구 보존
- ✅ **자동 복구**: 컨테이너 재시작 정책 (`--restart unless-stopped`)

### 🐳 사전 구성된 개발 환경

- ✅ **양자 컴퓨팅**: Qiskit 2023 최신 버전
- ✅ **머신러닝**: PyTorch, Scikit-learn
- ✅ **데이터 분석**: NumPy, Pandas, Matplotlib, Plotly
- ✅ **개발 도구**: Jupyter Notebook, VSCode Server
- ✅ **시스템 도구**: Git, Vim, Nano, Htop

### 🛡️ 보안 및 편의성

- ✅ **SSH 키 인증**: 비밀번호 없는 안전한 인증
- ✅ **Security Group**: 필요한 포트만 개방
- ✅ **Elastic IP**: 고정 IP로 안정적 접속
- ✅ **자동 로깅**: 모든 설정 과정이 `/var/log/qcbm-setup.log`에 기록

## 🛠️ 사용 가능한 서비스

| 서비스            | 접속 방법                   | 포트 | 용도         | 인증 방식           | 비밀번호          |
| ----------------- | --------------------------- | ---- | ------------ | ------------------- | ----------------- |
| **EC2 SSH**       | `ssh qcbm`                  | 22   | 서버 관리    | SSH Key (자동 설정) | ❌ 없음           |
| **Container SSH** | `ssh qcbm-container`        | 2222 | 개발 작업    | SSH Key (자동 설정) | ❌ 없음           |
| **VSCode Web**    | `http://[IP]:8080`          | 8080 | 웹 IDE       | 비밀번호 인증       | ✅ `qcbmpassword` |
| **VSCode Remote** | Remote-SSH → qcbm-container | 2222 | 데스크톱 IDE | SSH Key (권장 방법) | ❌ 없음           |

### 🔐 **인증 방식 상세**

#### 🔑 **SSH Key 기반 접속** (비밀번호 불필요)

- **EC2 SSH**: AWS EC2 Key Pair 자동 사용
- **Container SSH**: 개인 SSH Key 자동 주입
- **VSCode Remote SSH**: 개인 SSH Key 사용
- **장점**: 비밀번호 입력 없이 안전한 키 기반 인증

#### 🌐 **VSCode Web 접속** (비밀번호 필요)

```
🔗 주소: http://[ELASTIC_IP]:8080
🔑 비밀번호: qcbmpassword
```

- **장점**: 브라우저만으로 즉시 접속 가능
- **용도**: 빠른 코드 확인, 웹 기반 개발

## 🔄 간소화된 워크플로우

### 🚀 초기 설정 (5분 완료!)

```bash
1. git clone https://github.com/Q-BFD/QCBM-LSTM.git
2. cd QCBM-LSTM
3. vi deploy.sh          # KEY_NAME 수정
4. ./deploy.sh           # 원클릭 배포 (자동화!)
5. ./setup_ssh_config.sh # SSH 설정
6. VSCode Remote-SSH 연결 # 즉시 개발 시작!
```

### 💼 일상적인 개발

```bash
1. VSCode에서 Remote-SSH → qcbm-container 연결
2. /home/devuser/workspace에서 코드 편집
3. Jupyter Notebook 또는 터미널에서 실행
4. 모든 작업이 EBS에 영구 저장
```

### 📊 개발 환경 정보 확인

```bash
# 컨테이너에서 실행
ssh qcbm-container
python3 -c "import qiskit; print(f'Qiskit: {qiskit.__version__}')"
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
jupyter --version
```

## 🚨 문제 해결

### 🔍 배포 상태 확인

```bash
# CloudFormation 스택 상태 확인
aws cloudformation describe-stacks --stack-name qcbm-dev-stack

# 상세 로그 확인 (EC2에서)
ssh qcbm "tail -f /var/log/qcbm-setup.log"

# Docker 컨테이너 상태 확인
ssh qcbm "docker ps -a"
ssh qcbm "docker logs qcbm-dev"
```

### 🔧 자동 복구 기능

시스템이 자동으로 처리하는 문제들:

- ✅ **EBS 볼륨 디바이스 이름 변경** → 자동 감지
- ✅ **Docker 컨테이너 중지** → 자동 재시작
- ✅ **SSH 키 권한 문제** → 자동 설정
- ✅ **Python 패키지 누락** → 자동 설치

### 🆘 수동 문제 해결

#### SSH 연결 실패

```bash
# SSH 키 권한 확인
chmod 600 ~/.ssh/id_*

# SSH 연결 테스트
ssh -v qcbm-container
```

#### 컨테이너 재시작

```bash
# 컨테이너 재시작
ssh qcbm "docker restart qcbm-dev"

# 완전 재구축
ssh qcbm "cd /mnt/data/QCBM-LSTM && docker build -t qcbm-dev . && docker restart qcbm-dev"
```

#### 환경 초기화

```bash
# CloudFormation 스택 삭제 후 재배포
aws cloudformation delete-stack --stack-name qcbm-dev-stack
# 스택 삭제 완료 후
./deploy.sh
```

## 🎯 성능 최적화

### 💰 비용 관리

#### 리소스 정리

```bash
# CloudFormation 스택 삭제 (모든 리소스 정리)
aws cloudformation delete-stack --stack-name qcbm-dev-stack
```

#### 비용 최적화 팁

- **인스턴스 중지**: 사용하지 않을 때 EC2 인스턴스 중지
- **스케줄링**: CloudWatch Events로 자동 시작/중지 설정
- **볼륨 관리**: 불필요한 EBS 스냅샷 정리
- **스팟 인스턴스**: 비용 절약을 위해 스팟 인스턴스 고려

### ⚡ 성능 튜닝

#### 인스턴스 타입 변경

```bash
# deploy.sh에서 수정
INSTANCE_TYPE="t3.large"  # 또는 "c5.xlarge" (CPU 집약적 작업용)
```

#### GPU 지원 (선택사항)

```bash
# GPU 인스턴스 사용시 (p3.2xlarge 등)
# requirements.txt에 추가:
# torch-torchvision-cpu → torch-torchvision-cuda
```

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

문제가 있거나 질문이 있으시면 GitHub Issues를 통해 문의해주세요.

---

**🎯 Happy Quantum Computing with Automated Cloud Development!** 🚀✨

---

## 🛠️ 개발자 참고: 유용한 명령어 모음

> 자동화 개발 과정에서 사용된 핵심 명령어들을 역할별로 정리했습니다. 문제 해결이나 커스터마이징 시 참고하세요.

### 🔐 **AWS 환경 확인 및 인증**

#### 현재 AWS 사용자 및 권한 확인

```bash
# AWS 계정 정보 확인
aws sts get-caller-identity

# AWS CLI 설정 확인
aws configure list
```

### 🔑 **EC2 Key Pair 관리**

#### Key Pair 확인 및 생성

```bash
# 특정 Key Pair 존재 확인
aws ec2 describe-key-pairs --key-names [KEY_NAME]

# 모든 Key Pair 목록 조회
aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName' --output table

# 새 Key Pair 생성 및 저장
aws ec2 create-key-pair --key-name [KEY_NAME] \
  --query 'KeyMaterial' --output text > ~/.ssh/[KEY_NAME].pem
chmod 600 ~/.ssh/[KEY_NAME].pem
```

### ☁️ **CloudFormation 스택 관리**

#### 스택 상태 확인 및 관리

```bash
# 스택 상태 확인
aws cloudformation describe-stacks --stack-name [STACK_NAME] \
  --query 'Stacks[0].StackStatus' --output text

# 스택 삭제
aws cloudformation delete-stack --stack-name [STACK_NAME]

# 실패한 리소스 확인
aws cloudformation describe-stack-events --stack-name [STACK_NAME] \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
  --output table
```

### 🖼️ **AMI 이미지 관리**

#### 최신 Ubuntu AMI 검색

```bash
# 최신 Ubuntu 22.04 AMI 찾기
aws ec2 describe-images --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
            "Name=state,Values=available" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table | head -10

# 특정 AMI 존재 확인
aws ec2 describe-images --image-ids [AMI_ID]
```

### 🔗 **SSH 연결 및 원격 관리**

#### 기본 SSH 연결

```bash
# EC2 인스턴스 접속
ssh qcbm

# Docker 컨테이너 접속
ssh qcbm-container

# SSH 연결 테스트
ssh qcbm "whoami && pwd"
```

#### 시스템 정보 확인

```bash
# 블록 디바이스 확인
ssh qcbm "lsblk"

# 인스턴스 공개 IP 확인
ssh qcbm "curl -s http://169.254.169.254/latest/meta-data/public-ipv4"

# SSH 키 확인
ssh qcbm "cat ~/.ssh/authorized_keys"
```

### 💾 **EBS 볼륨 관리**

#### EBS 볼륨 수동 마운트

```bash
# EBS 볼륨 포맷 및 마운트
ssh qcbm "sudo mkfs.ext4 /dev/nvme1n1 && \
          sudo mkdir -p /mnt/data && \
          sudo mount /dev/nvme1n1 /mnt/data"

# 영구 마운트 설정
ssh qcbm "echo '/dev/nvme1n1 /mnt/data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab"
```

### 📁 **Git 및 파일 관리**

#### 리포지토리 관리

```bash
# Git 리포지토리 클론
ssh qcbm "cd /mnt/data && sudo git clone https://github.com/Q-BFD/QCBM-LSTM.git"

# 디렉토리 내용 확인
ssh qcbm "ls -la /mnt/data/QCBM-LSTM/"

# 특정 파일 찾기
ssh qcbm "find /mnt/data/QCBM-LSTM -name 'requirements.txt' -o -name 'Dockerfile'"
```

### 🐳 **Docker 관리**

#### Docker 상태 확인

```bash
# Docker 컨테이너 상태 확인
ssh qcbm "sudo docker ps -a"

# Docker 컨테이너 로그 확인
ssh qcbm "sudo docker logs [CONTAINER_NAME]"

# Docker 사용자 권한 추가
ssh qcbm "sudo usermod -aG docker ubuntu"
```

#### Docker 컨테이너 관리

```bash
# 컨테이너 재시작
ssh qcbm "docker restart [CONTAINER_NAME]"

# 컨테이너 내부 명령 실행
ssh qcbm "docker exec [CONTAINER_NAME] /bin/bash -c '[COMMAND]'"

# Docker 이미지 빌드
ssh qcbm "cd /mnt/data/QCBM-LSTM && docker build -t [IMAGE_NAME] ."
```

### 🚨 **문제 해결 및 디버깅**

#### 로그 확인

```bash
# Cloud-init 로그 확인
ssh qcbm "sudo tail -30 /var/log/cloud-init-output.log"

# 사용자 정의 설정 로그 확인
ssh qcbm "tail -20 /var/log/qcbm-setup.log"

# 시스템 상태 확인
ssh qcbm "systemctl status docker"
```

#### SSH 설정 확인

```bash
# 로컬 SSH 공개키 확인
cat ~/.ssh/id_ed25519.pub

# SSH config 설정 확인
cat ~/.ssh/config | grep -A10 "qcbm-container"

# SSH 연결 상세 디버깅
ssh -v qcbm-container
```

### 🔧 **환경 초기화 및 재설정**

#### 완전 재배포

```bash
# 스택 삭제 후 재배포
aws cloudformation delete-stack --stack-name qcbm-dev-stack
# 삭제 완료 대기 후
./deploy.sh
```

#### 컨테이너 재구축

```bash
# 컨테이너 중지 및 제거
ssh qcbm "docker stop qcbm-dev && docker rm qcbm-dev"

# 이미지 재빌드 및 실행
ssh qcbm "cd /mnt/data/QCBM-LSTM && \
          docker build -t qcbm-dev . && \
          docker run -d --name qcbm-dev \
            -p 8080:8080 -p 2222:22 \
            -v /mnt/data:/mnt/data \
            qcbm-dev"
```

### 📊 **성능 모니터링**

#### 시스템 리소스 확인

```bash
# 디스크 사용량 확인
ssh qcbm "df -h"

# 메모리 사용량 확인
ssh qcbm "free -h"

# CPU 사용률 확인
ssh qcbm "top -bn1 | head -20"

# Docker 리소스 사용량
ssh qcbm "docker stats --no-stream"
```

### 🎯 **주요 사용 시나리오**

#### 🚨 **문제 발생 시 체크리스트**

1. **CloudFormation 스택 상태 확인**
2. **EC2 인스턴스 SSH 연결 확인**
3. **Docker 컨테이너 상태 확인**
4. **EBS 볼륨 마운트 상태 확인**
5. **로그 파일 확인**

#### 🔄 **정기 유지보수**

1. **Docker 컨테이너 재시작**
2. **시스템 업데이트**
3. **디스크 공간 정리**
4. **백업 확인**

#### ⚡ **빠른 문제 해결**

```bash
# 원스톱 상태 확인 스크립트
ssh qcbm "echo '=== System Info ===' && \
          uname -a && \
          echo '=== Disk Usage ===' && \
          df -h && \
          echo '=== Docker Status ===' && \
          docker ps -a && \
          echo '=== Mount Points ===' && \
          mount | grep /mnt/data"
```

---

> 💡 **팁**: 이 명령어들은 자동화 스크립트 개발 과정에서 실제 사용된 것들입니다. 문제 해결이나 커스터마이징 시 참고하여 사용하세요.
