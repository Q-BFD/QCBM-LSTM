# 🔬 QCBM-LSTM 실험 가이드 (v2.0)

이 문서는 새롭게 리팩토링된 QCBM-LSTM 프로젝트의 실험 설정 및 실행 방법을 안내합니다.

## 🚀 새로운 아키텍처의 핵심 철학

> "연구자는 **무엇(What)**을 실험할지에만 집중하고, **어떻게(How)** 환경을 구성할지는 시스템이 알아서 처리한다."

- **`settings/*.json`**: 연구자는 오직 이 JSON 파일에 실험 파라미터만 수정하면 됩니다.
- **`ExperimentManager`**: 폴더 생성, 이름 규칙, 정보 파일 기록 등 모든 관리 작업을 자동으로 처리합니다.
- **`main.py`**: 전체 실험 흐름을 지휘하는 역할만 담당합니다.

---

## ⚡ 5분 빠른 시작

### 1. `settings` 폴더에 나만의 설정 파일 만들기

`settings/final_test_settings.json` 파일을 복사하여 `settings/my_first_experiment.json` 파일을 만듭니다.

```json
{
    "_comment": "나의 첫 실험: 빠른 테스트",
    "prior_model": "QCBM",
    "experiment_name": "my-first-experiment", 
    "lstm_n_epochs": 2,
    "data_set_fraction": 0.01,
    "reward_strategy": "fast",
    "parallel_n_cores": 4
}
```
- **`experiment_name`**: 실험 결과를 저장할 폴더 이름이 됩니다. **직접 지정하는 것을 강력히 권장합니다.**
- **`reward_strategy`**: 보상 계산 방식을 `'original'`, `'fast'`, `'minimal'` 중에서 선택합니다.
- 나머지 파라미터는 `settings/training_para.py`의 기본값이 자동으로 적용됩니다.

### 2. 실험 실행

터미널에서 다음 명령을 실행합니다.

```bash
# research/python 디렉토리로 이동
cd QCBM-LSTM/research/python

# 설정 파일을 지정하여 main.py 실행
python main.py --config_file settings/my_first_experiment.json
```
- 또는, 프로젝트 루트에서 `sh` 스크립트를 사용할 수도 있습니다.
```bash
bash QCBM-LSTM/research/sh/run_final_test.sh # 예시 스크립트
```

### 3. 결과 확인

실행이 완료되면 `research/outputs/` 폴더 아래에 결과가 저장됩니다.

```
outputs/
└── my-first-experiment/
    ├── experiment_info.txt  # 👈 **실험의 모든 설정이 기록된 가장 중요한 파일**
    ├── checkpoints/
    ├── logs/
    ├── plots/
    └── samples/
```

---

## ⚙️ 주요 설정 가이드

### 1. 실험 이름 (`experiment_name`)

- **직접 지정 (권장)**: JSON 파일에 `"experiment_name": "내-실험-이름"`과 같이 명시적으로 지정하세요. 가장 관리하기 좋습니다.
- **자동 생성**: `experiment_name`을 지정하지 않거나 `null`로 두면, 시스템이 자동으로 복잡한 이름을 생성합니다.
  - **형식**: `{username}-{ip}_{model}_l{layers}_d{dim}_t{temp}_r{reward}_{hash}`
  - **예시**: `qb-frontier-172-17-0-2_QCBM_l2_d128_t0.5_r-original_a1b2c3`

### 2. 보상 계산 전략 (`reward_strategy`)

어떤 기준으로 분자에게 보상을 줄지 결정하는 핵심 파라미터입니다.

| `reward_strategy` | 목적 | 속도 | 설명 |
| :--- | :--- | :--- | :--- |
| **`'original'`** | **정밀성** | 🐢 (느림) | 모든 약물성 필터(PAINS, MCF, SA_Score 등)를 사용하여 가장 정확한 보상을 계산합니다. (기본값) |
| **`'fast'`** | **속도** | 🚀🚀 | LogP, 회전 결합 등 간단한 물리화학적 특성만으로 빠르게 보상을 계산합니다. |
| **`'minimal'`** | **초고속** | 🚀🚀🚀 | 분자량, 원자 수 등 최소한의 정보만으로 보상을 계산합니다. 빠른 프로토타이핑에 유용합니다. |

### 3. 병렬 처리 (`parallel_n_cores`)

보상 계산 시 사용할 CPU 코어 수를 지정합니다.
```json
{
    "parallel_n_cores": 8,
    "parallel_chunk_size": 2500 
}
```
- **`parallel_n_cores`**: 코어 수 (많을수록 빠름, 최대 8-16 권장)
- **`parallel_chunk_size`**: 한 번에 처리할 작업량 (보통 1000~5000 사이)

---

## 📁 결과물 분석

- **`outputs/[실험이름]/experiment_info.txt`**: **가장 먼저 확인해야 할 파일.** 해당 실험에 사용된 모든 파라미터와 설명이 기록되어 있어, 이 파일만 있으면 실험을 완벽하게 재현할 수 있습니다.
- **`outputs/[실험이름]/plots/`**: 에폭별로 생성된 분자 구조 이미지가 저장됩니다.
- **`wandb`**: `use_wandb: true`로 설정하면, 웹 대시보드에서 실시간으로 학습 과정을 모니터링할 수 있습니다.

## 🆘 문제 해결

- **`FileNotFoundError: .../data/...`**: `data` 폴더가 없습니다. 관리자에게 데이터셋을 요청하여 `research/data` 경로에配置하세요.
- **`ModuleNotFoundError`**: 필요한 라이브러리가 설치되지 않았습니다. `requirements.txt`를 확인하여 설치하세요. (`pip install -r requirements.txt`)
- **기타**: 오류 메시지를 확인하고, `experiment_info.txt`에 기록된 설정이 의도한 대로인지 확인하세요.