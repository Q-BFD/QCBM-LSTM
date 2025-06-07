# 🚀 Infrastructure Automation (Hidden Directory)

이 숨김 폴더(`.infra/`)는 AWS 인프라 자동화를 담당합니다.
일반 사용자는 이 폴더를 직접 사용할 필요가 없습니다.

## 📦 지원 프로젝트

- **QCBM**: `./deploy-cpu.sh qcbm`
- **기타 프로젝트**: `./deploy-cpu.sh myproject`

## 🛠️ 사용법 (고급 사용자)

### 1. CPU 테스트 인스턴스 배포

```bash
cd .infra/

# 특정 프로젝트로 배포
./deploy-cpu.sh qcbm        # QCBM 프로젝트
./deploy-cpu.sh myproject   # 다른 프로젝트

# 기본값으로 배포 (qcbm)
./deploy-cpu.sh
```

### 2. SSH 설정

```bash
# 동일한 프로젝트명으로 SSH 설정
./setup_ssh_config.sh qcbm
./setup_ssh_config.sh myproject

# 기본값으로 설정
./setup_ssh_config.sh
```

### 3. 접속

```bash
# EC2 인스턴스
ssh qcbm
ssh myproject

# Docker 컨테이너
ssh qcbm-container
ssh myproject-container
```

## 📋 생성되는 리소스

각 프로젝트별로 다음 리소스가 생성됩니다:

- **CloudFormation Stack**: `{PROJECT_NAME}-dev-cpu`
- **EC2 Instance**: `{PROJECT_NAME}-DevInstance-CPU`
- **Security Group**: `{PROJECT_NAME}-SecurityGroup`
- **EBS Volume**: `{PROJECT_NAME}-DataVolume-CPU`
- **Elastic IP**: `{PROJECT_NAME}-ElasticIP`
- **SSH Key Pair**: `{PROJECT_NAME}-dev-key`

## 🌐 서비스 접속

### Jupyter Notebook

```
http://YOUR_ELASTIC_IP:8888
Token: {PROJECT_NAME}token
```

### VSCode Web (Docker 컨테이너)

```
http://YOUR_ELASTIC_IP:8080
```

## 🔧 파일 구조

```
.infra/                      # 숨김 폴더 (사용자는 무시)
├── cloudformation-cpu.yml    # CPU 인스턴스 템플릿
├── deploy-cpu.sh            # 배포 스크립트
├── setup_ssh_config.sh      # SSH 설정 스크립트
├── Dockerfile              # Docker 빌드 파일
└── README.md               # 이 파일
```

## 📊 비용 정보

- **t3.large**: ~$0.09/hour (~$65/month)
- **50GB EBS**: ~$5/month
- **Elastic IP**: $0 (인스턴스 연결 시)

## 🚀 GPU 업그레이드 경로

1. CPU 환경에서 테스트 완료
2. AWS 콘솔 → Service Quotas → EC2
3. "Running On-Demand G instances" → 8 vCPU 요청
4. 승인 후 GPU 인스턴스 배포

## ⚡ 일반 사용자용 (권장)

프로젝트 루트에서 간단하게 실행:

```bash
# 1. 배포 (프로젝트 루트에서)
./deploy-cpu.sh myproject

# 2. SSH 설정 (프로젝트 루트에서)
./setup-ssh.sh myproject

# 3. 접속 테스트
ssh myproject

# 4. Jupyter 접속
# http://YOUR_ELASTIC_IP:8888 (token: myprojecttoken)
```

## ⚡ 고급 사용자용 (직접 실행)

```bash
# 1. 배포
cd .infra && ./deploy-cpu.sh myproject

# 2. SSH 설정 (3-5분 후)
./setup_ssh_config.sh myproject

# 3. 접속 테스트
ssh myproject

# 4. Jupyter 접속
# http://YOUR_ELASTIC_IP:8888 (token: myprojecttoken)
```

## 🔍 문제 해결

### 로그 확인

```bash
ssh myproject 'tail -f /var/log/myproject-setup.log'
```

### EBS 볼륨 확인

```bash
ssh myproject 'df -h /mnt/data'
```

### Docker 컨테이너 상태

```bash
ssh myproject 'docker ps'
```

## 📝 커스터마이징

각 프로젝트의 요구사항에 맞게 다음을 수정할 수 있습니다:

- **cloudformation-cpu.yml**: 인스턴스 타입, 볼륨 크기
- **deploy-cpu.sh**: Git 리포지토리, 브랜치
- **requirements.txt**: Python 패키지 (각 프로젝트 저장소에서)
