from typing import Literal
import os
import json
from pydantic import BaseModel, Field


class TrainingArgs(BaseModel):
    """
    모델 학습에 필요한 모든 하이퍼파라미터와 설정값을 관리하는 클래스
    튜플 형식으로 데이터 저장
    """
    
    # Prior 모델 종류 (기본값이 없는 필드를 먼저 선언)
    prior_model: Literal[
        "QCBM", "mQCBM", "mrQCBM", "RBM", "classical", "ibm_hub_simulator"
    ]

    prior_size: int = Field(default=100, description="Prior 모델 샘플 수")
    num_qubits: int = Field(default=8, description="QCBM에서 사용할 큐비트 수 (4-20 권장)")
    prior_n_epochs: int = Field(default=30, description="사전 모델(QCBM/RBM) 학습 에폭 수")
    n_qcbm_layers: int = Field(default=3, description="Prior 모델 레이어 수")
    n_qcbm_shots: int = Field(default=2000, description="Prior 모델 샘플 수")

    # LSTM 학습 관련 하이퍼파라미터
    lstm_n_epochs: int = Field(default=100, description="LSTM 모델 학습 에폭 수")
    n_compound_generation: int = Field(default=1000, description="생성할 분자 수")
    n_generation_steps: int = Field(default=10, description="생성 과정 반복 횟수")

    # LSTM 구조
    n_lstm_layers: int = Field(default=2, description="LSTM 모델 레이어 수")
    embedding_dim: int = Field(default=64, description="임베딩 차원 수")
    hidden_dim: int = Field(default=128, description="은닉층 노드 수")

    # 데이터 및 Device 설정
    data_set_id: int = Field(default=4, description="데이터셋 ID")
    data_set_fraction: float = Field(default=0.005, description="데이터셋 비율")
    device: Literal["cpu", "cuda", "auto"] = "auto"
    gpu_count: int = Field(default=1, description="GPU 수")

    # 테스트 및 배치 설정
    n_test_samples: int = Field(default=20_000, description="테스트 샘플 수")
    batch_size: int = Field(default=128, description="배치 크기")
    dataset_frac: float = Field(default=1.0, description="데이터셋 비율")

    # Chemistry42 Sample 관련 설정
    n_samples_chemistry42: int = Field(default=30, description="화학 42 샘플 수")
    n_test_samples_chemistry42: int = Field(default=300, description="화학 42 테스트 샘플 수")

    # 최적화 및 Temperature 설정
    optimizer_name: str = Field(default="COBYLA", description="최적화 알고리즘 이름")
    do_greedy_sampling: bool = Field(default=False, description="그리디 샘플링 여부")
    temprature:float = Field(default=0.5, description="온도")
    prior_maxiter:int = Field(default=50, description="Prior 모델 최대 반복 횟수")
    prior_tol:float = Field(default=1e-4, description="Prior 모델 최적화 허용 오차")
    
    # 성능 최적화 설정
    fast_reward: str = Field(default="fast", description="보상 함수 속도 (original/fast/minimal)")
    
    # 병렬처리 설정
    use_parallel_reward: bool = Field(default=True, description="보상 계산에 병렬처리 사용 여부")  
    parallel_n_cores: int = Field(default=8, description="병렬처리에 사용할 CPU 코어 수 (최대 8 권장)")
    parallel_chunk_size: int = Field(default=2000, description="병렬처리 청크 크기 (1000-5000 권장)")
    
    # 병렬 데이터셋 생성 설정
    use_parallel_dataset: bool = Field(default=True, description="데이터셋 생성에 병렬처리 사용 여부")
    parallel_dataset_cores: int = Field(default=8, description="데이터셋 생성에 사용할 CPU 코어 수")
    parallel_dataset_chunk_size: int = Field(default=10000, description="데이터셋 병렬처리 청크 크기")

    # 실험 저장 경로
    experiment_root:str = Field(default="./outputs", description="실험 루트")
    n_benchmark_samples:int = Field(default=100_000, description="벤치마크 샘플 수")
    plot_root:str = Field(default="./outputs/plots", description="그래프 저장 경로")
    
    max_mol_weight:int = Field(default=800)
    
    # WandB 모니터링 설정
    use_wandb: bool = Field(default=True, description="WandB 사용 여부")
    wandb_project: str = Field(default="kras-drug-discovery", description="WandB 프로젝트 이름")
    wandb_entity: str = Field(default=None, description="WandB 팀/사용자 이름 (선택사항)")
    experiment_name: str = Field(default=None, description="실험 이름 (자동 생성시 None)")


    def create_experiment_dir(self) -> None:
        """
        실험 결과 디렉토리를 생성하고 기본 정보를 저장
        (실제 필요한 서브디렉토리는 파일 저장 시점에 생성)
        """
        import datetime
        
        # 메인 실험 디렉토리만 생성
        os.makedirs(self.experiment_root, exist_ok=True)
        
        # plot_root 디렉토리도 생성 (별도 경로인 경우)
        if self.plot_root != os.path.join(self.experiment_root, "plots"):
            os.makedirs(self.plot_root, exist_ok=True)
        
        # 실험 시작 시간 및 설정 정보 기록
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        info_file = os.path.join(self.experiment_root, "experiment_info.txt")
        
        with open(info_file, "w") as f:
            f.write(f"Experiment started: {timestamp}\n")
            f.write(f"Prior model: {self.prior_model}\n")
            f.write(f"Temperature: {self.temprature}\n")
            f.write(f"Batch size: {self.batch_size}\n")
            f.write(f"LSTM epochs: {self.lstm_n_epochs}\n")
            f.write(f"Device: {self.device}\n")
            f.write(f"Output directory: {self.experiment_root}\n")
        
        print(f"✅ 실험 디렉토리 생성: {self.experiment_root}")
        print(f"📝 실험 정보 저장: experiment_info.txt")
        print(f"📁 서브폴더는 필요할 때 자동 생성됩니다")


    # @classmethod : 클래스 메서드는 클래스 자체에 속한 메서드
    @classmethod
    def from_namespace(cls, namespace) -> "TrainingArgs":
        """
        argparse 네임스페이스로부터 인스턴스 생성
        """
        namespace_dict = vars(namespace)
        namespace_dict.pop("config_file", None)

        return cls(**namespace_dict)
    

    @classmethod 
    def from_file(cls, path: str) -> "TrainingArgs":
        """
        JSON 파일로부터 학습 파라미터를 로드하는 클래스 메서드
        
        Args:
            path: JSON 설정 파일 경로
            
        Returns:
            TrainingArgs 인스턴스
        """
        assert os.path.exists(path), f"File {path} does not exist"
        assert path.endswith(".json"), f"File {path} is not a json file"
        with open(path, "r") as f:
            args = json.load(f)
        return cls(**args)
