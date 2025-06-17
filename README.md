# research-template

## Quantum Circuit Born Machine for Drug Discovery

> Quantum Circuit Born Machine(QCBM)-과 Long Short-Term Memory(LSTM) 를 결합한 **하이브리드 양자-클래식** 모델 연구 프로젝트입니다.

---

## 🔑 SSH 키 및 사용자 계정 정책

### 📋 SSH 키 네이밍 규칙

이 프로젝트는 **SSH 키 이름에서 사용자 이름을 자동으로 추출**하는 시스템을 사용합니다.

#### 키 이름 패턴

```
id_[키타입]_[서비스]_[사용자이름]

⚠️ 중요: 사용자 이름 부분에는 underscore(_) 사용 금지!

✅ 올바른 예시:
- id_ed25519_github_john-doe    → 사용자: john-doe
- id_rsa_company_alice-kim      → 사용자: alice-kim
- id_ed25519_personal_bobsmith  → 사용자: bobsmith

❌ 잘못된 예시:
- id_ed25519_github_john_doe    → ERROR (underscore 사용)
- id_rsa_company_alice_kim      → ERROR (underscore 사용)
```

#### 지원되는 키 타입

- `id_ed25519_*` (권장)
- `id_rsa_*`
- `id_ecdsa_*`

### 🛠️ SSH 키 설정 방법

1. **SSH 키 생성** (없는 경우):

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_github_yourname -C "your.email@example.com"
   ```

2. **키 권한 설정**:

   ```bash
   chmod 600 ~/.ssh/id_ed25519_github_yourname
   chmod 644 ~/.ssh/id_ed25519_github_yourname.pub
   ```

3. **GitHub에 공개 키 등록**:

   - GitHub Settings > SSH Keys에서 `.pub` 파일 내용 등록

4. **배포 스크립트에서 키 이름 설정**:
   ```bash
   # .infra/deploy-cpu.sh에서 수정
   SSH_KEY_NAME="id_ed25519_github_yourname"  # 여기에 실제 키 이름 입력
   ```

### 🔒 보안 가이드라인

- **절대 개인 키를 공유하지 마세요** (`.pub`가 없는 파일)
- **각자의 고유한 키를 사용하세요** (공유 키 사용 금지)
- **키 파일 권한을 올바르게 설정하세요** (600/644)
- **사용하지 않는 키는 정기적으로 삭제하세요**

### 🚀 자동 사용자 설정

키 이름을 올바르게 설정하면 다음이 자동으로 구성됩니다:

- **Docker 컨테이너 사용자 이름**: 키에서 추출
- **Git 사용자 설정**: `yourname@users.noreply.github.com`
- **SSH 접속 계정**: 추출된 사용자 이름
- **JupyterLab 작업 디렉토리**: `/home/yourname/projectname`

> 💡 **참고**: 키 이름의 사용자 부분은 이미 hyphen(`-`)을 사용해야 합니다. Underscore(`_`) 사용 시 오류가 발생합니다.

---

## 🔬 연구자(Regular User) 빠른 시작

### 전제 조건: SSH 키 설정 완료

위의 "SSH 키 및 사용자 계정 정책"을 먼저 확인하고 키 설정을 완료하세요.

1️⃣ **EC2 개발 환경 자동 배포**

```bash
# 기본 설정 (t3.large, 50GB)
./deploy-cpu.sh projectname --ssh-key id_ed25519_github_yourname

# 커스텀 설정 예시
./deploy-cpu.sh projectname --ssh-key id_ed25519_github_yourname \
  --instance-type t3.xlarge --volume-size 100
```

**지원되는 CPU 인스턴스 타입:**

- `t3.medium`, `t3.large`, `t3.xlarge`, `t3.2xlarge` (일반 목적)
- `c5.large`, `c5.xlarge`, `c5.2xlarge` (컴퓨팅 최적화)
- `m5.large`, `m5.xlarge`, `m5.2xlarge` (균형잡힌 성능)
- `m7i.2xlarge`, `m7i.4xlarge` (최신 세대)

2️⃣ **SSH 설정** (선택사항)

```bash
./setup-ssh.sh projectname --ssh-key id_ed25519_github_yourname
```

3️⃣ **접속 & 개발**

```bash
ssh projectname-container     # Docker 컨테이너 내부 셸
```

| 서비스       | 주소 / 명령                          | 용도           |
| ------------ | ------------------------------------ | -------------- |
| Jupyter      | http://<EIP>:8888 (token: qcbmtoken) | 노트북 실행    |
| VSCode Web   | http://<EIP>:8080                    | 브라우저 IDE   |
| EC2 SSH      | `ssh ubuntu@<EIP>`                   | 서버 관리      |
| 컨테이너 SSH | `ssh -p 2222 yourname@<EIP>`         | 코드 작성·실험 |

> ⏱ 설치 5-8분 소요  
> 🔑 `yourname`은 SSH 키에서 자동 추출된 사용자 이름입니다

**💰 비용 예시** (US East 기준):

- `t3.large`: ~$0.09/시간 (2 vCPU, 8GB RAM)
- `t3.xlarge`: ~$0.18/시간 (4 vCPU, 16GB RAM)
- `c5.2xlarge`: ~$0.34/시간 (8 vCPU, 16GB RAM, 컴퓨팅 최적화)
- `m7i.2xlarge`: ~$0.40/시간 (8 vCPU, 32GB RAM, 최신 세대)
- EBS 스토리지: ~$0.10/월 per GB

### 🚀 GPU 개발 환경 (고급 사용자)

양자 머신 러닝 모델 학습을 위한 GPU 인스턴스가 필요한 경우:

```bash
# SPOT 인스턴스 (60-90% 할인, 권장)
./deploy-gpu.sh projectname --ssh-key id_ed25519_github_yourname --pricing spot

# ON-DEMAND 인스턴스 (안정성 우선)
./deploy-gpu.sh projectname --ssh-key id_ed25519_github_yourname --pricing ondemand
```

**지원되는 GPU 인스턴스:**

- `g4dn.xlarge`, `g4dn.2xlarge` (NVIDIA T4, 비용 효율적)
- `g5.xlarge`, `g5.2xlarge` (NVIDIA A10G, 최신 세대)
- `p3.2xlarge` (NVIDIA V100, 고성능 ML)

> ⚠️ **주의**: GPU 인스턴스는 AWS 할당량 요청이 필요할 수 있습니다.

### 💻 로컬 실행 (선택 사항)

```bash
pip install -r requirements.txt
jupyter notebook               # 로컬 노트북
```

### 📁 프로젝트 구조

```
research-template/
├── research/                  # 연구 작업 디렉토리
│   ├── notebooks/            # Jupyter 노트북
│   ├── python/               # Python 스크립트
│   ├── data/                 # 데이터 파일
│   └── model/                # 학습된 모델
├── .infra/                   # 인프라 자동화 스크립트
│   ├── deploy-cpu.sh         # CPU 인스턴스 배포
│   ├── setup_ssh_config.sh   # SSH 설정 자동화
│   └── ...                   # 기타 인프라 파일들
└── README.md                 # 이 파일
```

> 💡 **Tip** : 사용하지 않을 때 EC2 인스턴스를 중지하면 비용을 절감할 수 있습니다.

---

## 🛠 개발자 문서

인프라를 수정해야 할 경우 **`.infra/README.md`** 를 참고하세요.

---

## 라이선스

MIT

# 연구 프로젝트 가이드라인

## 📁 프로젝트 구조

모든 연구 관련 작업은 **`research/`** 폴더 안에서 진행해주세요.

### 필수 폴더 구조

```
research/
├── notebooks/    # Jupyter 노트북 파일들
├── python/       # Python 스크립트 파일들
├── sh/           # Shell 스크립트 파일들
├── data/         # 데이터 파일들 (원본, 전처리된 데이터 등)
└── model/        # 학습된 모델 파일들
```

## 📋 작업 가이드라인

### 1. notebooks/ 폴더

- 모든 Jupyter 노트북 파일은 이 폴더에 저장
- 탐색적 데이터 분석(EDA), 실험, 프로토타이핑 작업
- 파일명은 목적을 명확히 하는 이름으로 지정 (예: `01_data_exploration.ipynb`)

### 2. python/ 폴더

- 재사용 가능한 Python 모듈과 스크립트
- 데이터 처리, 모델 학습, 평가 스크립트
- 유틸리티 함수들

### 3. sh/ 폴더

- 배치 처리를 위한 Shell 스크립트
- 자동화 스크립트
- 환경 설정 스크립트

### 4. data/ 폴더

- 원본 데이터
- 전처리된 데이터
- 중간 결과물
- 하위 폴더로 구조화 권장 (예: `raw/`, `processed/`, `interim/`)

### 5. model/ 폴더

- 학습된 모델 파일 (.pkl, .h5, .pth 등)
- 모델 체크포인트
- 모델 메타데이터

## 🚀 시작하기

1. 새로운 연구 작업을 시작할 때는 `research/` 폴더로 이동하세요
2. 적절한 하위 폴더에 파일을 생성하고 작업하세요
3. 파일명과 폴더명은 명확하고 일관성 있게 작성하세요

## 💡 팁

- 각 폴더에 `.gitkeep` 파일을 추가하여 빈 폴더도 Git에서 추적되도록 하세요
- 큰 데이터 파일은 `.gitignore`에 추가하여 버전 관리에서 제외하세요
- 실험 결과는 노트북과 함께 문서화하세요

This folder contains scripts for deploying the environment on AWS. It allows you to quickly set up a development environment on EC2 with all necessary dependencies installed inside a Docker container. For more details, see the deployment guide in `research-template/infra/README.md`.

### `research/`
