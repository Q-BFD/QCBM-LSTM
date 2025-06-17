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

        self._generate_experiment_name_if_needed()
        self._setup_directories()
        self._save_config_info()

    def _generate_experiment_name_if_needed(self):
        """실험 이름이 제공되지 않은 경우, 주요 파라미터를 기반으로 자동 생성합니다."""
        if self.args.experiment_name and self.args.experiment_name.strip() != "":
            self.logger.info(f"✅ 제공된 실험 이름 사용: {self.args.experiment_name}")
            return

        try:
            username = getpass.getuser()
        except:
            username = "user"

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0].replace('.', '-')
            s.close()
        except:
            ip_address = "no-ip"

        hash_input = f"{datetime.datetime.now().isoformat()}_{username}_{ip_address}"
        hash_6digit = hashlib.md5(hash_input.encode()).hexdigest()[:6]

        name_parts = [
            f"{username}-{ip_address}",
            self.args.prior_model,
            f"l{self.args.n_lstm_layers}",
            f"d{self.args.hidden_dim}",
            f"t{self.args.temprature}",
            f"r-{self.args.reward_strategy}",
            hash_6digit
        ]
        self.args.experiment_name = "_".join(map(str, name_parts))
        self.logger.info(f"🔧 실험 이름이 제공되지 않아 자동으로 생성합니다: {self.args.experiment_name}")

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