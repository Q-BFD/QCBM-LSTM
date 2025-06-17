import os
import datetime
import hashlib
import getpass
import socket
from pathlib import Path

from .logging_utils import get_logger

class ExperimentManager:
    """
    실험 환경(디렉토리, 이름, 정보 파일)을 관리하는 클래스.
    TrainingArgs 객체를 받아 필요한 모든 Side Effect를 처리합니다.
    """
    def __init__(self, args):
        self.args = args
        self.experiment_dir = None
        self.dirs = {}
        self.logger = get_logger()

        # 이름 생성 로직을 __init__에서 직접 호출하여 항상 실행되도록 보장합니다.
        self._generate_experiment_name()
        self._setup_directories()
        self._save_config_info()

    def _generate_experiment_name(self):
        """
        실험 이름을 생성합니다.
        - JSON 파일에 이름이 있으면 접두사로 사용합니다.
        - 이름이 없으면 사용자명을 접두사로 사용합니다.
        - 모델 파라미터, IP, 해시를 조합하여 최종 이름을 완성합니다.
        """
        base_name = self.args.experiment_name or getpass.getuser()
        self.logger.info(f"실험 이름 생성을 위해 '{base_name}'을(를) 기본 접두사로 사용합니다.")
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address_full = s.getsockname()[0]
            s.close()
            ip_suffix = "".join([part[-1] for part in ip_address_full.split('.')])
        except Exception:
            ip_suffix = "no-ip"

        hash_input = f"{datetime.datetime.now().isoformat()}_{base_name}_{ip_suffix}"
        hash_6digit = hashlib.md5(hash_input.encode()).hexdigest()[:6]

        dynamic_parts = [
            self.args.prior_model,
            f"l{self.args.n_lstm_layers}",
            f"d{self.args.hidden_dim}",
            f"t{self.args.temprature}",
            f"r-{self.args.reward_strategy}",
            f"ip{ip_suffix}",
            hash_6digit
        ]
        
        final_name = f"{base_name}_{'_'.join(map(str, dynamic_parts))}"
        self.args.experiment_name = final_name
        self.logger.info(f"✅ 최종 생성된 실험 이름: {self.args.experiment_name}")

    def _setup_directories(self):
        """실험 결과 저장을 위한 디렉토리 구조를 생성합니다."""
        base_dir = Path(self.args.experiment_root)
        self.experiment_dir = base_dir / self.args.experiment_name
        
        subdirectories = ["checkpoints", "samples", "plots", "logs", "stats"]
        for subdir in subdirectories:
            (self.experiment_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        self.dirs = {
            'base': self.experiment_dir,
            **{subdir: self.experiment_dir / subdir for subdir in subdirectories}
        }
        self.logger.info(f"✅ 실험 디렉토리 구조 생성 완료: {self.experiment_dir}")

    def _save_config_info(self):
        """`experiment_info.txt` 파일에 모든 설정 정보를 상세히 기록합니다."""
        info_file = self.experiment_dir / "experiment_info.txt"
        
        with open(info_file, "w", encoding='utf-8') as f:
            f.write(f"# Experiment: {self.args.experiment_name}\n")
            f.write(f"# Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write("-" * 50 + "\n\n")
            
            # Use model_fields to get descriptions
            if hasattr(self.args, 'model_fields'):
                for field_name, field in self.args.model_fields.items():
                    value = getattr(self.args, field_name)
                    description = field.description or "No description"
                    f.write(f"{field_name}: {value}  # {description}\n")
            else: # Fallback for other argument sources
                for key, value in vars(self.args).items():
                    f.write(f"{key}: {value}\n")
        
        self.logger.info(f"📝 모든 실험 설정을 {info_file}에 저장했습니다.")

    def get_directories(self):
        """생성된 디렉토리 경로 딕셔너리를 반환합니다."""
        return self.dirs 