# KRAS Drug Discovery with QCBM and LSTM

이 프로젝트는 QCBM(Quantum Circuit Born Machine)과 LSTM을 사용하여 KRAS 단백질 억제제를 발견하는 연구입니다.

## 📁 프로젝트 구조

```
research/
├── python/                    # 모든 Python 코드
│   ├── main.py               # 메인 실행 파일
│   └── utils/                # 유틸리티 모듈들
│       ├── training_utils.py # 학습 관련 유틸리티
│       ├── filters.py        # 분자 필터링
│       ├── compound_stat.py  # 화합물 통계
│       ├── dataloader.py     # 데이터 로딩
│       └── selfies_encoding.py # SELFIES 인코딩
├── data/                     # 데이터셋과 필터 파일들
├── model/                    # 모델 정의 (LSTM, QCBM)
├── settings/                 # 설정 파일들
├── results/                  # 실험 결과 (자동 생성됨)
│   ├── checkpoints/         # 모델 체크포인트
│   ├── generated_samples/   # 생성된 분자 샘플
│   ├── plots/              # 분자 구조 이미지
│   ├── logs/               # 실험 로그
│   └── statistics/         # 통계 요약
├── sh/
│   └── run.sh               # 실험 실행 스크립트
└── requirements.txt         # Python 의존성
```

## 🚀 사용법

### 방법 1: Shell 스크립트 사용 (권장)

```bash
cd research

# 기본 실험 실행
bash sh/run.sh

# 특정 실험 실행
bash sh/run.sh qcbm

# 도움말 확인
bash sh/run.sh --help

# 추가 argument와 함께 실행
bash sh/run.sh default --help
```

### 방법 2: Python에서 직접 실행

```bash
cd research/python
python main.py --config_file ../settings/benchmark_models_settings_qcbm.json
```

### 새로운 실험 설정 추가

`sh/run.sh` 파일의 `EXPERIMENTS` 배열에 새 설정을 추가:

```bash
EXPERIMENTS[my_experiment]="./settings/my_custom_settings.json"
```

## ⚙️ 설정

설정은 `settings/benchmark_models_settings_qcbm.json` 파일에서 수정할 수 있습니다:

```json
{
    "lstm_n_epochs": 5,          # LSTM 학습 에폭 수
    "prior_n_epochs": 40,        # Prior 모델 학습 에폭 수
    "prior_model": "QCBM",       # Prior 모델 종류 (QCBM/classical)
    "n_lstm_layers": 5,          # LSTM 레이어 수
    "batch_size": 128,           # 배치 크기
    "experiment_root": "./results" # 결과 저장 경로
}
```

## 📊 결과 확인

실행 후 `results/` 폴더에서 다음 결과들을 확인할 수 있습니다:

- **checkpoints/**: 각 에폭별 모델 상태
- **generated_samples/**: 생성된 분자 데이터 (CSV, PKL)
- **plots/**: 분자 구조 이미지들
- **statistics/**: 학습 통계 요약
- **logs/**: 실험 설정과 로그

## 🔧 개발

새로운 기능 추가 시:

- 유틸리티 함수: `python/utils/` 폴더에 추가
- 모델 코드: `model/` 폴더에 추가
- 설정: `settings/` 폴더에서 관리
- 실험 스크립트: `sh/` 폴더에서 관리

### 실험 매개변수 조정 예시

```bash
# 다양한 설정으로 실험 실행
bash sh/run.sh qcbm        # QCBM 모델로 실행
bash sh/run.sh classical   # Classical 모델로 실행 (설정 파일 필요)

# 명령줄에서 직접 매개변수 전달도 가능
cd python
python main.py --config_file ../settings/custom_settings.json
```

## 📝 로그 예시

실행 시 다음과 같은 구조화된 로그를 확인할 수 있습니다:

```
========== EPOCH 1/5 ==========
[Step 1/6] Training LSTM model...
[Step 2/6] Generating compounds with LSTM...
[Step 3/6] Calculating compound statistics...
[Step 4/6] Training prior model...
[Step 5/6] Generating compounds after prior training...
[Step 6/6] Saving epoch results...

============================================================
EPOCH 1 SUMMARY
============================================================
Execution time: 45.67 seconds
Unique compounds: 3,245
Valid compounds: 2,891
Unseen compounds: 1,456
Unique fraction: 0.8123
Valid fraction: 0.7234
Diversity fraction: 0.6789
============================================================
```

## 🏆 최종 결과

학습 완료 후 최고 성능 요약이 출력됩니다:

```
Best Performance (Epoch 3):
  Valid fraction: 0.8456
  Diversity: 0.7234
  Unique fraction: 0.9123
  Total valid compounds: 4,234
```
