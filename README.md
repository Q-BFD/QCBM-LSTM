# QCBM-LSTM

> Quantum Circuit Born Machine(QCBM)-과 Long Short-Term Memory(LSTM) 를 결합한 **하이브리드 양자-클래식** 모델 연구 프로젝트입니다.

---

## 🔬 연구자(Regular User) 빠른 시작

1️⃣ **EC2 개발 환경 자동 배포**

```bash
./deploy-cpu.sh qcbm          # 프로젝트 이름은 자유롭게 지정 가능
```

2️⃣ **SSH 설정**

```bash
./setup-ssh.sh qcbm           # 30초 이내
```

3️⃣ **접속 & 개발**

```bash
ssh qcbm-container            # Docker 컨테이너 내부 셸
```

| 서비스       | 주소 / 명령                          | 용도           |
| ------------ | ------------------------------------ | -------------- |
| Jupyter      | http://<EIP>:8888 (token :qcbmtoken) | 노트북 실행    |
| VSCode Web   | http://<EIP>:8080                    | 브라우저 IDE   |
| EC2 SSH      | `ssh qcbm`                           | 서버 관리      |
| 컨테이너 SSH | `ssh qcbm-container`                 | 코드 작성·실험 |

> ⏱ 설치 5-8분 소요, 비용 ≈ $0.09/시간 (t3.large + 50 GB EBS)

### 💻 로컬 실행 (선택 사항)

```bash
pip install -r requirements.txt
jupyter notebook               # 로컬 노트북
```

### 📁 프로젝트 구조

```
QCBM-LSTM/
├── src/ , notebooks/          # 연구 코드·노트북
├── data/ , results/           # 데이터셋·출력
├── deploy-cpu.sh              # 원클릭 배포 래퍼
├── setup-ssh.sh               # SSH 설정 래퍼
└── .infra/                    # 인프라 자동화 (무시해도 됨)
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
