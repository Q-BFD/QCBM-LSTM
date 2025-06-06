# 🏗️ QCBM Infrastructure

AWS 기반 QCBM 양자 머신러닝 개발환경 자동 배포

## 📁 파일 구조

```
infrastructure/
├── deploy-ondemand.sh          # 온디맨드 GPU 인스턴스 배포
├── deploy-spot.sh              # Spot GPU 인스턴스 배포 (60-90% 절약)
├── cloudformation-ondemand.yml # 온디맨드 CloudFormation 템플릿
├── cloudformation-spot.yml     # Spot CloudFormation 템플릿
└── README.md                   # 이 파일
```

## 🚀 빠른 시작

### **1️⃣ GPU 할당량 확인**

먼저 AWS에서 GPU 인스턴스 할당량을 확인하세요:

- AWS Console → Service Quotas → EC2 → "Running On-Demand G instances"
- 현재 제한: 0 vCPU (신규 계정)
- 필요한 양: 8 vCPU (g4dn.2xlarge)

### **2️⃣ 배포 선택**

#### **💰 비용 절약 우선 (개발용 추천)**

```bash
cd infrastructure
./deploy-spot.sh
```

- **60-90% 비용 절약** 💰
- 중단 가능성 있음 ⚡
- 데이터는 EBS에 보존 📦

#### **⚡ 안정성 우선 (프로덕션용)**

```bash
cd infrastructure
./deploy-ondemand.sh
```

- **안정적, 중단 없음** 🔒
- 온디맨드 가격 💳
- 24/7 가용성 🕒

## ⚙️ 설정 변경

### **Git 리포지토리 변경**

배포 스크립트에서 다음 변수들을 수정하세요:

```bash
# Git repository configuration
GIT_REPOSITORY="https://github.com/YOUR_ORG/YOUR_REPO.git"
GIT_BRANCH="your-branch"
```

### **인스턴스 타입 변경**

배포 스크립트에서 인스턴스 타입을 변경할 수 있습니다:

```bash
INSTANCE_TYPE="g4dn.xlarge"    # 4 vCPU, 16GB RAM, T4 GPU (더 저렴)
INSTANCE_TYPE="g4dn.2xlarge"   # 8 vCPU, 32GB RAM, T4 GPU (기본값)
INSTANCE_TYPE="g5.2xlarge"     # 8 vCPU, 32GB RAM, A10G GPU (최신)
```

### **SSH 키 경로 변경**

```bash
SSH_PUBLIC_KEY_FILE="~/.ssh/your_key.pub"
```

## 🔑 SSH 설정

배포 완료 후:

```bash
cd ..
./setup_ssh_config.sh
```

## 🌐 접속 방법

### **VSCode Web**

```
http://YOUR_ELASTIC_IP:8080
Password: qcbmpassword
```

### **SSH 접속**

```bash
# 컨테이너 접속 (개발용)
ssh qcbm-container

# EC2 직접 접속 (관리용)
ssh qcbm
```

## 💰 비용 비교

| 인스턴스 타입 | 온디맨드   | Spot (평균) | 월 비용 (24/7) |
| ------------- | ---------- | ----------- | -------------- |
| g4dn.xlarge   | $0.42/시간 | $0.13/시간  | $95 → $28      |
| g4dn.2xlarge  | $0.75/시간 | $0.22/시간  | $547 → $160    |
| g5.2xlarge    | $1.21/시간 | $0.36/시간  | $884 → $263    |

## 🔧 문제 해결

### **GPU 할당량 부족**

```
ERROR: You have requested more vCPU capacity than your current vCPU limit of 0
```

**해결방법:**

1. AWS Console → Service Quotas
2. Amazon EC2 → "Running On-Demand G instances"
3. Request quota increase → 8 vCPU
4. 이유: "양자 머신러닝 연구개발용"

### **스택 ROLLBACK_COMPLETE 오류**

```bash
aws cloudformation delete-stack --stack-name qcbm-dev-ondemand
# 또는
aws cloudformation delete-stack --stack-name qcbm-dev-spot
```

## 📋 포함된 기능

- ✅ **GPU 인스턴스** (NVIDIA T4/A10G)
- ✅ **Docker 개발환경**
- ✅ **VSCode Web 서버**
- ✅ **SSH 컨테이너 접근**
- ✅ **EBS 영구 스토리지**
- ✅ **Elastic IP (고정 IP)**
- ✅ **자동 환경 설정**
- ✅ **Python 패키지 설치**
- ✅ **Git 리포지토리 클론**

## 🎯 다음 단계

1. **환경 테스트**: Jupyter Notebook 실행
2. **GPU 확인**: `nvidia-smi` 명령어 실행
3. **QCBM 코드 실행**: 양자 회로 테스트
4. **모델 훈련**: 대용량 데이터셋으로 실험
