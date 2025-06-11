# 실험 설정 및 실행 가이드

## ⚡ **빠른 시작 체크리스트**

### **🎯 최소 5분 설정**
```bash
# 1. 데이터 폴더 확인
ls data/KRAS_G12D/ && ls data/valid_filter/
# ✅ 파일들이 보이면 OK, 없으면 관리자에게 요청

# 2. 기본 실행 테스트
bash sh/run.sh --help
# ✅ 도움말이 나오면 설정 완료

# 3. 빠른 테스트 (선택사항)
bash sh/run.sh fast_test
# ✅ 3 에폭 빠른 실험으로 동작 확인

# 4. WandB 설정 (선택사항)
wandb login
# ✅ API Key 입력하면 실시간 모니터링 가능

# 5. 장시간 실험 (백그라운드 실행)
screen -S my_experiment
bash sh/run.sh default
# Ctrl+A, D (detach) → IDE 닫아도 실험 계속 진행!
```

### **❗ 문제 해결**
```bash
# 데이터 파일 없음 → 관리자에게 data 폴더 요청
# Import 오류 → 위 체크리스트로 확인
# WandB 오류 → 오프라인 모드: WANDB_MODE=offline bash sh/run.sh
# Jupyter Notebook Kernel 오류 → Container에 Jupyter 확장 프로그램 설치 필요
```

#### **📓 Jupyter Notebook 사용 시 주의사항**
- **Container 환경에서 Jupyter Notebook을 사용하려면 Jupyter 확장 프로그램이 설치되어 있어야 합니다**
- VS Code에서 `.ipynb` 파일 실행 시 kernel을 찾을 수 없다는 오류가 발생하면:
  ```bash
  # Container 내부에서 Jupyter 관련 패키지 설치
  pip install jupyter ipykernel
  
  # 또는 requirements.txt에 추가하여 환경 구성
  echo "jupyter" >> requirements.txt
  echo "ipykernel" >> requirements.txt
  ```

---

## 🚀 **시작하기 전 필수 설정**

### **📁 데이터셋 설정 (중요!)**

**⚠️ data 폴더는 Git에서 관리되지 않으므로 별도로 설정해야 합니다!**

#### **1단계: 데이터 폴더 구조 확인**
```bash
# 필요한 데이터 폴더 구조:
research/
└── data/
    ├── KRAS_G12D/
    │   └── 1Mstoned_vsc_initial_dataset_insilico_chemistry42_filtered.csv
    └── valid_filter/
        ├── mcf.csv
        ├── pains.txt
        └── wehi_pains.txt
```

#### **2단계: 데이터 파일 확보**
```bash
# 관리자에게 다음 파일들을 요청하세요:

# 🧬 메인 데이터셋 (필수)
data/KRAS_G12D/1Mstoned_vsc_initial_dataset_insilico_chemistry42_filtered.csv

# 🔬 필터링 데이터 (필수)
data/valid_filter/mcf.csv           # MCF 필터 데이터
data/valid_filter/pains.txt         # PAINS 필터 패턴
data/valid_filter/wehi_pains.txt    # WEHI PAINS 필터 패턴
```

#### **3단계: 데이터 설치 확인**
```bash
# 데이터 파일 존재 확인
ls -la data/KRAS_G12D/
ls -la data/valid_filter/

# 파일 크기 확인 (대략적인 기준)
# 1Mstoned_vsc_initial_dataset... : ~50MB
# mcf.csv : ~1KB
# pains.txt : ~50KB  
# wehi_pains.txt : ~200KB
```

#### **4단계: 데이터 없을 시 발생하는 오류**
```bash
# 이런 오류가 나면 데이터 파일이 없는 것입니다:
FileNotFoundError: [Errno 2] No such file or directory: '.../data/valid_filter/mcf.csv'
FileNotFoundError: [Errno 2] No such file or directory: '.../data/KRAS_G12D/...'
```

---

## 📁 프로젝트 구조

```
research/
├── data/                                 # 🚨 Git 미관리 - 별도 설정 필요!
│   ├── KRAS_G12D/                        # 메인 데이터셋
│   └── valid_filter/                     # 필터링 데이터
├── python/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── training_para.py              # TrainingArgs 클래스 정의
│   │   └── benchmark_models_settings_qcbm.json  # 기본 설정 파일
│   ├── utils/                            # 유틸리티 함수들
│   └── main.py
├── sh/
│   ├── run.sh                            # 메인 실행 스크립트
│   ├── run_temperature_experiment.sh     # Temperature 실험
│   └── run_batch_size_experiment.sh      # Batch size 실험
└── outputs/                              # 🎯 모든 실험 결과 저장
    └── [experiment_name]/
        ├── experiment_info.txt           # 실험 메타데이터 (항상 생성)
        ├── plots/                        # 분자 이미지, 그래프 (필요시 생성)
        ├── samples/                      # 생성된 분자 데이터 (필요시 생성)
        ├── checkpoints/                  # 모델 체크포인트 (필요시 생성)
        ├── stats/                        # 통계 데이터 (필요시 생성)
        └── logs/                         # 실험 로그 (필요시 생성)
```

## 🎯 **새로운 간단한 설정 방식** ⭐️

### **기본값 자동 사용 (JSON 파일 불필요!)**
```bash
bash sh/run.sh                 # 모든 기본값 사용
bash sh/run.sh default         # 모든 기본값 사용  
```
→ **`training_para.py`의 기본값이 자동으로 사용됩니다!**

### **부분 설정 파일 (바뀌는 값만!)**

**핵심**: 20개가 넘는 파라미터 중에서 **바뀌는 값만 JSON에 넣으면 됩니다!**

#### 예시 1: Temperature만 변경
```json
{
    "prior_model": "QCBM",
    "temprature": 0.2,
    "experiment_name": "temp_test"
}
```
→ **나머지 19개 파라미터는 모두 기본값 자동 사용!**

#### 예시 2: 빠른 테스트용
```json
{
    "prior_model": "QCBM",
    "lstm_n_epochs": 3,
    "batch_size": 32,
    "data_set_fraction": 0.001,
    "experiment_name": "quick_test"
}
```
→ **훨씬 간단하고 깔끔!**

## 🚀 실험 실행 방법

### 1. **기본값으로 실행 (NEW!)**
```bash
bash sh/run.sh                    # 완전 기본값 (JSON 불필요!)
bash sh/run.sh default           # 완전 기본값 (JSON 불필요!)
bash sh/run.sh --help            # 도움말 보기
```

### 2. **커스텀 설정으로 실행**  
```bash
# 설정 파일 사용
bash sh/run.sh --config_file python/settings/temp_experiment.json
cd python && python main.py --config_file settings/fast_test.json
```

### 3. **자동 실험 스크립트**
```bash
# Temperature 실험 (0.1 ~ 0.5, 0.1 단위)
bash sh/run_temperature_experiment.sh

# Batch Size 실험 (32, 64, 128, 256, 512)  
bash sh/run_batch_size_experiment.sh
```
- ✅ **최소한의 오버라이드만 포함한 설정 파일 자동 생성**
- ✅ **각각 다른 디렉토리에 결과 저장**
- ✅ **임시 설정 파일은 자동으로 정리**
- ✅ **WandB에서 실험별 자동 추적**

### 4. **🔥 백그라운드 실행 (장시간 실험용)** ⭐️ **추천!**

**💡 IDE나 터미널을 닫아도 실험이 계속 진행됩니다!**

#### **🖥️ Screen 사용법 (강력 추천!)**

**기본 사용법:**
```bash
# 1. 새로운 screen 세션 생성
screen -S my_experiment

# 2. 실험 실행
bash sh/run.sh default

# 3. 세션에서 나오기 (실험은 계속 진행)
# Ctrl+A, 그다음 D 키 누르기

# 4. 나중에 다시 접속
screen -r my_experiment

# 5. 실행 중인 세션 목록 확인
screen -ls
```

**실전 예시:**
```bash
# Temperature 실험을 백그라운드에서 실행
screen -S temp_experiment
bash sh/run_temperature_experiment.sh
# Ctrl+A, D (detach)

# 다른 실험도 동시에 실행 가능
screen -S batch_experiment  
bash sh/run_batch_size_experiment.sh
# Ctrl+A, D (detach)

# 실행 중인 실험들 확인
screen -ls
# 0.temp_experiment (Detached)
# 1.batch_experiment (Detached)

# 특정 실험 상태 확인
screen -r temp_experiment
```

**Screen 고급 명령어:**
```bash
# 세션 강제 종료
screen -S my_experiment -X quit

# 새 창 만들기 (세션 내에서): Ctrl+A, C
# 창 전환: Ctrl+A, N (다음), Ctrl+A, P (이전)
# 창 목록: Ctrl+A, W
# 세션 이름 변경: Ctrl+A, :sessionname new_name
```

#### **🌟 nohup 사용법 (간단한 대안)**

```bash
# 기본 사용법
nohup bash sh/run.sh default > experiment.log 2>&1 &

# 로그 실시간 확인
tail -f experiment.log

# 실행 중인 프로세스 확인
ps aux | grep python

# 프로세스 종료 (PID 필요)
kill [PID]
```

#### **📊 백그라운드 실험 모니터링**

**WandB로 실시간 모니터링:**
```bash
# Screen에서 실험 실행
screen -S wandb_experiment
bash sh/run.sh default  # WandB 자동 연결
# Ctrl+A, D

# 웹에서 https://wandb.ai/[your-entity]/kras-drug-discovery 확인
# 실험이 진행 중인지 실시간으로 확인 가능!
```

**로그 파일 모니터링:**
```bash
# outputs 폴더에서 실험 진행 상황 확인
watch -n 30 "ls -la outputs/*/experiment_info.txt"

# 특정 실험의 로그 실시간 확인
tail -f outputs/[experiment_name]/logs/*.log
```

#### **💡 백그라운드 실험 Best Practices**

**실험 시작 전:**
```bash
# 1. 빠른 테스트로 문제없는지 확인
bash sh/run.sh fast_test

# 2. WandB 연결 확인
wandb status

# 3. 디스크 공간 확인
df -h

# 4. Screen 세션 생성 후 본격 실험
screen -S production_experiment
bash sh/run.sh default
```

**실험 중 체크포인트:**
```bash
# 정기적으로 세션 상태 확인
screen -ls

# 실험 진행 상황 확인
screen -r production_experiment
# Ctrl+A, D (다시 detach)

# WandB 대시보드에서 메트릭 확인
# https://wandb.ai/[your-entity]/kras-drug-discovery
```

**실험 완료 후:**
```bash
# 세션 정리
screen -S production_experiment -X quit

# 결과 확인
ls -la outputs/[experiment_name]/
```

## 🛠️ 나만의 실험 스크립트 만들기

### Template:
```bash
#!/bin/bash

# 실험할 값들 정의
VALUES=(value1 value2 value3)
PARAMETER_NAME="your_parameter"

# 각 값에 대해 설정 파일 생성
for value in "${VALUES[@]}"; do
    cat > "python/settings/exp_${value}.json" << EOF
{
    "prior_model": "QCBM",
    "${PARAMETER_NAME}": ${value},
    "experiment_root": "./outputs/${PARAMETER_NAME}_${value}"
}
EOF
    
    # 실험 실행
    cd python
    python main.py --config_file "../settings/exp_${value}.json"
    cd ..
done
```

## 📊 자주 실험하는 파라미터들

| 파라미터 | 기본값 | 실험 추천값 | 설명 |
|---------|--------|-------------|------|
| `temprature` | 0.5 | 0.1~1.0 | 샘플링 온도 |
| `batch_size` | 128 | 32,64,128,256,512 | 배치 크기 |
| `lstm_n_epochs` | 100 | 50,100,200 | LSTM 학습 에폭 |
| `learning_rate` | - | 0.001,0.01,0.1 | 학습률 (추가 필요) |
| `n_lstm_layers` | 2 | 1,2,3,4 | LSTM 레이어 수 |
| `hidden_dim` | 128 | 64,128,256,512 | 은닉층 차원 |

## 🎨 고급 사용법

### 1. 여러 파라미터 조합 실험
```json
{
    "prior_model": "QCBM",
    "temprature": 0.3,
    "batch_size": 64,
    "lstm_n_epochs": 150,
    "experiment_root": "./outputs/combo_temp03_batch64_epoch150"
}
```

### 2. 조건부 설정
```bash
# GPU가 있을 때와 없을 때 다른 설정
if nvidia-smi &> /dev/null; then
    DEVICE="cuda"
    BATCH_SIZE=256
else
    DEVICE="cpu"  
    BATCH_SIZE=32
fi

cat > "settings/adaptive_config.json" << EOF
{
    "prior_model": "QCBM",
    "device": "${DEVICE}",
    "batch_size": ${BATCH_SIZE}
}
EOF
```

## 📊 Outputs 폴더에 생성되는 실제 파일들

### 🗂️ 항상 생성:
- **experiment_info.txt**: 실험 설정 및 시작 시간

### 📁 실제 사용될 때만 생성:
- **plots/**: 
  - `epoch_X_molecules.png` - 에폭별 생성된 분자 구조 이미지
- **samples/**: 
  - `generated_epoch_XXX.csv` - 생성된 분자 SMILES (CSV)
  - `samples_epoch_XXX.pkl` - 상세한 샘플 데이터 (PKL)
- **checkpoints/**: 
  - `checkpoint_epoch_XXX.pkl` - 모델 체크포인트
- **stats/**: 
  - `training_summary.csv` - 전체 훈련 통계 요약
  - `detailed_compound_stats.pkl` - 상세 통계 데이터
- **logs/**: 
  - `experiment_log.pkl` - 실험 설정 및 최종 결과 로그

## 📊 **WandB 실시간 모니터링** ⭐️ **NEW!**

### 🚀 **자동으로 추적되는 메트릭:**
- **Compounds**: unique_count, valid_count, unseen_count
- **Fractions**: unique, valid, diversity
- **Performance**: epoch_time
- **분자 이미지**: 에폭별 생성된 분자 구조
- **하이퍼파라미터**: 모든 실험 설정 자동 저장

### 🎛️ **WandB 설정 옵션:**
```json
{
    "use_wandb": true,                    // WandB 사용 여부
    "wandb_project": "kras-drug-discovery", // 프로젝트 이름
    "wandb_entity": null,                 // 팀명 (선택사항)
    "experiment_name": null               // 실험명 (자동 생성)
}
```

### 🌐 **사용법:**

#### **🔐 초기 설정 (최초 1회만)**

**1단계: WandB API Key 획득**
```bash
# 관리자에게 WandB API Key 요청
# 팀 계정이 있는 경우: 관리자가 API Key 제공
# 개인 사용시: https://wandb.ai/signup 가입 후 https://wandb.ai/settings에서 API Key 확인
```

**2단계: 로그인**
```bash
# 터미널에서 로그인
wandb login

# 프롬프트가 나오면 API Key 입력
# Enter your API key: [여기에 Key 붙여넣기]
```

**3단계: 로그인 확인**
```bash
wandb status
# 로그인 성공시 entity 정보가 표시됩니다
```

**4단계: 연결 테스트 (선택사항)**
```bash
# 간단한 테스트 실행
cd python && python -c "
import wandb
run = wandb.init(project='test-connection', name='login-test')
wandb.log({'test_metric': 1.0})
wandb.finish()
print('✅ WandB 연결 테스트 성공!')
"

# 테스트 결과 확인: https://wandb.ai/[your-entity]/test-connection
```

#### **🚀 실험 실행**
```bash
# 로그인 후에는 WandB 자동 활성화
bash sh/run.sh

# 실험 진행 중 콘솔에 다음과 같이 표시:
# 🚀 WandB initialized: QCBM_temp0.5_batch128_20231210_143022
# 📊 Dashboard: https://wandb.ai/[your-entity]/kras-drug-discovery/runs/xxx
```

#### **📱 결과 확인**
```bash
# 브라우저에서 표시된 URL 접속
# 또는 https://wandb.ai/[your-entity]/kras-drug-discovery 직접 방문
```

#### **🔧 고급 옵션**
```bash
# 오프라인 모드 (인터넷 연결 없을 때)
WANDB_MODE=offline bash sh/run.sh

# WandB 완전 비활성화
# settings에서 "use_wandb": false로 설정

# 특정 프로젝트명 사용
# settings에서 "wandb_project": "custom-project-name"
```

#### **🚨 문제 해결**

**로그인 문제:**
```bash
# API Key 오류시
wandb login --relogin

# 로그인 상태 재확인
wandb status

# 캐시 초기화
rm -rf ~/.netrc ~/.config/wandb/
wandb login
```

**권한 문제:**
```bash
# 관리자에게 다음 정보 제공 요청:
# 1. 팀 WandB entity name
# 2. 프로젝트 접근 권한
# 3. API Key (읽기/쓰기 권한 포함)
```

**네트워크 문제:**
```bash
# 프록시 환경에서는 관리자에게 문의
# 방화벽 이슈: wandb.ai 도메인 허용 필요

# 임시 해결: 오프라인 모드 사용
WANDB_MODE=offline bash sh/run.sh
# 나중에 wandb sync로 동기화 가능
```

## ✅ 검증된 동작 확인

### **🔧 시스템 요구사항**
- ✅ **데이터셋 설정**: data 폴더 및 필수 파일들 존재
- ✅ **경로 문제 해결**: valid_filter 디렉토리 경로 수정
- ✅ **파일명 오타 수정**: compound_stat.py 이름 수정

### **⚙️ 설정 시스템**
- ✅ **부분 설정 파일 로드** (일부 값만 오버라이드)
- ✅ **기본값 자동 적용** (JSON 파일 없어도 실행 가능)
- ✅ **JSON 형식 유효성 검사**
- ✅ **단순화된 설정 구조** (중복 제거)

### **📁 실험 관리**
- ✅ **실험별 결과 디렉토리 자동 생성**
- ✅ **단순화된 폴더 구조** (필요할 때만 생성)
- ✅ **임시 파일 자동 정리**

### **📊 모니터링 시스템**
- ✅ **WandB 실시간 모니터링** (온라인/오프라인 지원)
- ✅ **자동 실험 추적** (메트릭, 이미지, 하이퍼파라미터)

### **🧪 실험 스크립트**
- ✅ **기본값 실행**: `bash sh/run.sh`
- ✅ **커스텀 설정**: `bash sh/run.sh temp_test`
- ✅ **자동 실험**: `bash sh/run_temperature_experiment.sh`
- ✅ **백그라운드 실행**: `screen -S exp && bash sh/run.sh`

### **🔄 장시간 실험 지원**
- ✅ **Screen 세션 관리** (IDE 종료 후에도 실험 계속)
- ✅ **다중 실험 동시 실행** (여러 screen 세션)
- ✅ **실시간 모니터링** (WandB + 로그 파일)
- ✅ **안전한 실험 관리** (detach/attach 지원)

---

**💡 Tip**: 실험 전에 항상 `--help` 옵션으로 확인하고, 작은 데이터셋으로 먼저 테스트해보세요! 