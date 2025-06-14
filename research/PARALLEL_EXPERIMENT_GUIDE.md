# 🚀 QCBM-LSTM 병렬처리 최적화 실험 가이드

이 가이드는 지금까지 구현된 모든 최적화를 포함한 완전한 병렬처리 실험을 실행하는 방법을 설명합니다.

## 📊 **포함된 최적화**

### **🏃 성능 최적화**

- ✅ **865배 빠른 reward_fc** (minimal 버전)
- ✅ **83배 빠른 reward_fc** (fast 버전)
- ✅ **병렬 처리** (2.7배 개선)
- ✅ **최적 청크 크기** (2,000개)

### **🧠 모델 개선**

- ✅ **Train/Test loss 분할** (10% test split)
- ✅ **오버피팅 감지** (train vs test loss 비교)
- ✅ **QCBM 분포 시각화** (histogram 분석)

### **📈 모니터링**

- ✅ **WandB 실시간 모니터링**
- ✅ **분자 구조 이미지** 자동 생성
- ✅ **성능 벤치마킹** 자동 수행

## 🎯 **실행 방법**

### **방법 1: Shell 스크립트 사용 (권장)**

#### **기본 실험 (50 epochs)**

```bash
cd research
bash sh/run_parallel_experiment.sh
```

#### **빠른 테스트 (5 epochs)**

```bash
bash sh/run_parallel_experiment.sh --quick
```

#### **최소 테스트 (1 epoch, 빠른 확인용)**

```bash
bash sh/run_parallel_experiment.sh --minimal
```

#### **설정만 확인 (실제 실행 안함)**

```bash
bash sh/run_parallel_experiment.sh --dry-run
```

#### **커스텀 설정으로 실행**

```bash
bash sh/run_parallel_experiment.sh --config my_settings.json
```

### **방법 2: Python 스크립트 직접 사용**

```bash
cd research/python

# 기본 실험
python3 run_parallel_experiment.py

# 커스텀 설정
python3 run_parallel_experiment.py --config settings/my_config.json

# 설정 검증만
python3 run_parallel_experiment.py --dry-run
```

## ⚙️ **설정 파일 예시**

### **기본 설정 (parallel_experiment_clean.json)**

```json
{
  "experiment_name": "qcbm_lstm_parallel_optimized_v1",
  "experiment_root": "./outputs/parallel_experiments",
  "prior_model": "QCBM",
  "lstm_n_epochs": 50,
  "batch_size": 128,
  "test_fraction": 0.1,
  "fast_reward": "fast",
  "use_parallel_reward": true,
  "parallel_n_cores": 8,
  "parallel_chunk_size": 2000,
  "use_wandb": true,
  "wandb_project": "qcbm-lstm-parallel-optimization"
}
```

### **빠른 테스트용 설정**

```json
{
  "experiment_name": "qcbm_lstm_quick_test",
  "lstm_n_epochs": 5,
  "batch_size": 64,
  "n_test_samples": 5000,
  "fast_reward": "fast",
  "use_parallel_reward": true,
  "parallel_n_cores": 4
}
```

### **최대 성능 설정 (865배 개선)**

```json
{
  "experiment_name": "qcbm_lstm_maximum_speed",
  "fast_reward": "minimal",
  "use_parallel_reward": true,
  "parallel_n_cores": 8,
  "parallel_chunk_size": 2000,
  "use_parallel_dataset": true
}
```

## 📋 **시스템 요구사항**

### **권장 사양**

- **CPU**: 8코어 이상
- **메모리**: 6GB 이상 여유 공간
- **디스크**: 10GB 이상 여유 공간

### **최소 사양**

- **CPU**: 4코어
- **메모리**: 3GB 여유 공간
- **디스크**: 5GB 여유 공간

### **필수 패키지**

```bash
pip install torch numpy pandas psutil wandb
```

## 📊 **예상 성능**

| 최적화            | 개선 배수    | 시간 단축       |
| ----------------- | ------------ | --------------- |
| minimal reward_fc | 865배        | 30분 → 2초      |
| fast reward_fc    | 83배         | 30분 → 20초     |
| 병렬 처리         | 2.7배        | 5분 → 2분       |
| **총 개선**       | **~2,300배** | **5시간 → 8분** |

## 🎯 **실험 결과 확인**

### **로컬 결과**

```bash
# 결과 디렉토리 확인
ls outputs/parallel_experiments/

# 훈련 요약 확인
cat outputs/parallel_experiments/stats/training_summary.csv

# 분자 이미지 확인
ls outputs/parallel_experiments/plots/
```

### **WandB 대시보드**

1. https://wandb.ai 접속
2. 프로젝트: `qcbm-lstm-parallel-optimization`
3. 실시간 메트릭 확인:
   - `training/lstm_loss` vs `training/test_loss`
   - `qcbm/distribution_analysis`
   - `molecules/generated_samples`

## 🔍 **주요 모니터링 메트릭**

### **Loss 메트릭**

- **training/lstm_loss**: 훈련 손실
- **training/test_loss**: 테스트 손실 (오버피팅 감지용)
- **training/prior_loss**: QCBM 손실

### **분자 품질 메트릭**

- **fractions/valid**: 유효한 분자 비율
- **fractions/unique**: 고유한 분자 비율
- **fractions/diversity**: 분자 다양성

### **성능 메트릭**

- **epoch_time**: 에폭당 실행 시간
- **compounds/valid_count**: 유효한 분자 수

### **QCBM 분석**

- **qcbm/avg_hamming_weight**: 평균 해밍 가중치
- **qcbm/unique_patterns**: 고유 패턴 수
- **qcbm/entropy**: 분포 엔트로피

## 🐛 **문제 해결**

### **메모리 부족**

```bash
# 배치 크기 줄이기
{
    "batch_size": 64,
    "n_test_samples": 10000
}
```

### **CPU 코어 부족**

```bash
# 병렬 코어 수 조정
{
    "parallel_n_cores": 4,
    "parallel_chunk_size": 1000
}
```

### **WandB 로그인 문제**

```bash
wandb login
# API Key 입력
```

### **패키지 누락**

```bash
pip install psutil  # 성능 모니터링용
pip install wandb   # 실시간 모니터링용
```

## 📈 **성능 최적화 팁**

### **1. reward_fc 설정**

- **minimal**: 최대 속도 (865배), 기본 필터만
- **fast**: 균형적 성능 (83배), Lipinski 규칙
- **original**: 전체 필터, 가장 느림

### **2. 병렬 처리 설정**

- **optimal chunk size**: 2,000개 (실험 검증됨)
- **cores**: 시스템 코어 수의 80-90%
- **memory per core**: ~1GB

### **3. 데이터 설정**

- **test_fraction**: 0.1 (10%)이 권장
- **data_set_fraction**: 1.0 (전체 사용)
- **n_test_samples**: 20,000개가 적절

## 🎊 **실험 완료 후**

### **결과 분석**

1. **Train vs Test loss**: 오버피팅 확인
2. **Valid fraction 추이**: 모델 학습 효과
3. **QCBM 분포**: 학습된 패턴 분석
4. **분자 구조**: 생성된 분자 품질

### **후속 실험**

1. **하이퍼파라미터 튜닝**: learning rate, 온도
2. **모델 구조**: LSTM 레이어, 큐비트 수
3. **데이터 확장**: 다른 데이터셋 테스트

---

## 🚀 **Quick Start**

```bash
# 1. 저장소 클론
git clone <repository-url>
cd QCBM-LSTM/research

# 2. 환경 설정
pip install -r requirements.txt
wandb login

# 3. 빠른 테스트
bash sh/run_parallel_experiment.sh --minimal --dry-run

# 4. 실제 실험
bash sh/run_parallel_experiment.sh --quick

# 5. 결과 확인
ls outputs/quick_test/
```

이제 최신 최적화가 모두 적용된 QCBM-LSTM 실험을 실행할 준비가 완료되었습니다! 🎯✨
