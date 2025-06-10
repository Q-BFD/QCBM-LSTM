# 실험 설정 및 실행 가이드

## 📁 Settings 구조

```
research/
├── python/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── training_para.py              # TrainingArgs 클래스 정의
│   │   └── benchmark_models_settings_qcbm.json  # 기본 설정 파일
│   └── main.py
└── sh/
    ├── run.sh                            # 메인 실행 스크립트
    ├── run_temperature_experiment.sh     # Temperature 실험
    └── run_batch_size_experiment.sh      # Batch size 실험
```

## 🎯 부분 설정 파일 사용법

**핵심**: 20개가 넘는 파라미터 중에서 **바뀌는 값만 JSON에 넣으면 됩니다!**

### 예시 1: Temperature만 변경
```json
{
    "prior_model": "QCBM",
    "temprature": 0.3
}
```
→ 나머지 19개 파라미터는 모두 기본값 사용

### 예시 2: 여러 파라미터 변경
```json
{
    "prior_model": "QCBM",
    "temprature": 0.2,
    "batch_size": 64,
    "lstm_n_epochs": 50,
    "experiment_root": "./results/my_experiment"
}
```

## 🚀 실험 실행 방법

### 1. 기본 실험 실행
```bash
bash sh/run.sh                    # 기본 설정으로 실행
bash sh/run.sh qcbm              # QCBM 실험 실행
bash sh/run.sh default --help    # 도움말 보기
```

### 2. Temperature 실험 (0.1 ~ 0.5, 0.1 단위)
```bash
bash sh/run_temperature_experiment.sh
```
- 자동으로 5개의 설정 파일 생성
- 각각 다른 디렉토리에 결과 저장
- 임시 설정 파일은 자동으로 정리

### 3. Batch Size 실험 (32, 64, 128, 256, 512)
```bash
bash sh/run_batch_size_experiment.sh
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
    "experiment_root": "./results/${PARAMETER_NAME}_${value}"
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
    "experiment_root": "./results/combo_temp03_batch64_epoch150"
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

## ✅ 검증된 동작 확인

- ✅ 부분 설정 파일 로드 (일부 값만 오버라이드)
- ✅ 기본값 자동 적용
- ✅ JSON 형식 유효성 검사
- ✅ 실험별 결과 디렉토리 자동 생성
- ✅ 임시 파일 자동 정리

---

**💡 Tip**: 실험 전에 항상 `--help` 옵션으로 확인하고, 작은 데이터셋으로 먼저 테스트해보세요! 