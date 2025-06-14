#!/usr/bin/env python3
"""
QCBM-LSTM 병렬처리 최적화 실험 실행 스크립트

이 스크립트는 다음 최적화가 적용된 완전한 실험을 실행합니다:
- 865배 빠른 reward_fc (minimal/fast 버전)
- 병렬 처리 최적화 (2.7배 개선)
- Train/Test loss 분할 및 WandB 모니터링
- QCBM 분포 시각화
- 자동 성능 벤치마킹

사용법:
    python run_parallel_experiment.py
    python run_parallel_experiment.py --config custom_config.json
    python run_parallel_experiment.py --dry-run  # 설정만 확인
"""

import argparse
import json
import os
import time
import sys
import psutil
import subprocess
from pathlib import Path
from datetime import datetime
import traceback

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_banner():
    """실험 시작 배너 출력"""
    print("=" * 80)
    print("🚀 QCBM-LSTM 병렬처리 최적화 실험")
    print("=" * 80)
    print("📊 포함된 최적화:")
    print("   ✅ 865배 빠른 reward_fc (minimal/fast 버전)")
    print("   ✅ 병렬 처리 (2.7배 개선)")
    print("   ✅ Train/Test loss 분할")
    print("   ✅ WandB 실시간 모니터링")
    print("   ✅ QCBM 분포 시각화")
    print("   ✅ 자동 성능 벤치마킹")
    print("=" * 80)


def check_system_resources():
    """시스템 리소스 확인"""
    print("\n🔍 시스템 리소스 확인:")
    
    # CPU 정보
    cpu_count = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"   💻 CPU: {cpu_count}코어, 현재 사용률: {cpu_percent:.1f}%")
    
    # 메모리 정보
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    memory_available_gb = memory.available / (1024**3)
    print(f"   🧠 메모리: {memory_gb:.1f}GB 총용량, {memory_available_gb:.1f}GB 사용 가능")
    
    # 디스크 정보
    disk = psutil.disk_usage('.')
    disk_free_gb = disk.free / (1024**3)
    print(f"   💾 디스크: {disk_free_gb:.1f}GB 여유 공간")
    
    # 권장 사항 확인
    warnings = []
    if cpu_count < 8:
        warnings.append(f"⚠️ CPU 코어 수({cpu_count})가 권장 사양(8코어) 미만입니다.")
    if memory_available_gb < 6:
        warnings.append(f"⚠️ 사용 가능한 메모리({memory_available_gb:.1f}GB)가 권장 사양(6GB) 미만입니다.")
    if disk_free_gb < 10:
        warnings.append(f"⚠️ 디스크 여유 공간({disk_free_gb:.1f}GB)이 권장 사양(10GB) 미만입니다.")
    
    if warnings:
        print("\n⚠️ 시스템 권장사항:")
        for warning in warnings:
            print(f"   {warning}")
        print("   💡 성능이 저하될 수 있습니다.")
    else:
        print("   ✅ 모든 시스템 요구사항을 충족합니다!")
    
    return len(warnings) == 0


def load_config(config_path):
    """설정 파일 로드 (주석 제거 후)"""
    print(f"\n📄 설정 파일 로드: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 주석 라인 제거 (// 로 시작하는 라인)
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('//') and not stripped.startswith('"//'):
                clean_lines.append(line)
        
        # JSON 파싱
        clean_json = ''.join(clean_lines)
        config = json.loads(clean_json)
        
        print("   ✅ 설정 파일 로드 성공")
        return config
        
    except Exception as e:
        print(f"   ❌ 설정 파일 로드 실패: {e}")
        return None


def validate_config(config):
    """설정 검증"""
    print("\n🔍 설정 검증:")
    
    required_fields = [
        'experiment_name', 'prior_model', 'lstm_n_epochs', 
        'batch_size', 'use_parallel_reward', 'fast_reward'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in config:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"   ❌ 필수 설정 누락: {missing_fields}")
        return False
    
    # 병렬 처리 설정 검증
    if config.get('use_parallel_reward', False):
        cores = config.get('parallel_n_cores', 1)
        chunk_size = config.get('parallel_chunk_size', 1000)
        available_cores = psutil.cpu_count(logical=True)
        
        if cores > available_cores:
            print(f"   ⚠️ 설정된 코어 수({cores})가 시스템 코어 수({available_cores})를 초과합니다.")
            config['parallel_n_cores'] = available_cores
            print(f"   🔧 자동 조정: {available_cores}코어로 설정")
    
    print("   ✅ 설정 검증 완료")
    return True


def print_experiment_summary(config):
    """실험 요약 출력"""
    print("\n📋 실험 설정 요약:")
    print(f"   🏷️ 실험명: {config['experiment_name']}")
    print(f"   📁 결과 디렉토리: {config['experiment_root']}")
    print(f"   🔬 모델: {config['prior_model']}")
    print(f"   📊 에폭: {config['lstm_n_epochs']}")
    print(f"   📦 배치 크기: {config['batch_size']}")
    print(f"   🧪 테스트 비율: {config.get('test_fraction', 0.1)*100:.1f}%")
    
    # 성능 최적화 설정
    print(f"\n⚡ 성능 최적화:")
    print(f"   🏃 빠른 reward_fc: {config.get('fast_reward', 'original')}")
    print(f"   🔄 병렬 처리: {'활성화' if config.get('use_parallel_reward', False) else '비활성화'}")
    if config.get('use_parallel_reward', False):
        print(f"   💻 병렬 코어: {config.get('parallel_n_cores', 1)}개")
        print(f"   📦 청크 크기: {config.get('parallel_chunk_size', 1000):,}개")
    
    # 예상 성능 개선
    if config.get('fast_reward') == 'minimal':
        print(f"   📈 예상 속도 개선: ~865배 (reward_fc)")
    elif config.get('fast_reward') == 'fast':
        print(f"   📈 예상 속도 개선: ~83배 (reward_fc)")
    
    if config.get('use_parallel_reward', False):
        print(f"   📈 병렬 처리 개선: ~2.7배")
    
    # WandB 설정
    print(f"\n📊 모니터링:")
    print(f"   📈 WandB: {'활성화' if config.get('use_wandb', False) else '비활성화'}")
    if config.get('use_wandb', False):
        print(f"   🎯 프로젝트: {config.get('wandb_project', 'default')}")


def create_experiment_script(config):
    """실험 실행을 위한 임시 스크립트 생성"""
    script_content = f'''#!/usr/bin/env python3
# 자동 생성된 실험 실행 스크립트
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main
from settings.training_para import TrainingArgs

# 설정 로드
args = TrainingArgs()

# 실험 설정 적용
args.experiment_name = "{config['experiment_name']}"
args.experiment_root = "{config['experiment_root']}"
args.prior_model = "{config['prior_model']}"
args.lstm_n_epochs = {config['lstm_n_epochs']}
args.batch_size = {config['batch_size']}
args.temprature = {config.get('temprature', 0.7)}
args.test_fraction = {config.get('test_fraction', 0.1)}
args.fast_reward = "{config.get('fast_reward', 'original')}"
args.use_parallel_reward = {str(config.get('use_parallel_reward', False)).lower()}
args.parallel_n_cores = {config.get('parallel_n_cores', 1)}
args.parallel_chunk_size = {config.get('parallel_chunk_size', 1000)}
args.use_wandb = {str(config.get('use_wandb', False)).lower()}
args.wandb_project = "{config.get('wandb_project', 'qcbm-lstm')}"

# 추가 설정들
for key, value in {dict([(k, v) for k, v in config.items() if not k.startswith('//') and not k.startswith('experiment')])}.items():
    if hasattr(args, key):
        if isinstance(value, str):
            setattr(args, key, "{{}}")
        else:
            setattr(args, key, {{}})

# 실험 실행
if __name__ == "__main__":
    main()
'''.format(config)
    
    # 임시 스크립트 파일 생성
    script_path = "temp_experiment_runner.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    return script_path


def run_experiment(config, dry_run=False):
    """실험 실행"""
    if dry_run:
        print("\n🔍 DRY RUN 모드 - 실제 실험은 실행하지 않습니다.")
        return True
    
    print("\n🚀 실험 시작!")
    
    # 실험 디렉토리 생성
    experiment_dir = Path(config['experiment_root'])
    experiment_dir.mkdir(parents=True, exist_ok=True)
    
    # 설정 파일 백업
    config_backup_path = experiment_dir / "experiment_config.json"
    with open(config_backup_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"   📄 설정 백업: {config_backup_path}")
    
    # 시작 시간 기록
    start_time = time.time()
    
    try:
        # main.py를 직접 import하여 실행
        print("   🔄 실험 모듈 로딩...")
        
        from main import main
        from settings.training_para import TrainingArgs
        
        print("   ⚙️ 설정 적용...")
        
        # 설정에서 주석 제거
        clean_config = {k: v for k, v in config.items() if not k.startswith('//')}
        
        # TrainingArgs 인스턴스 생성 (설정값으로 직접 생성)
        try:
            args = TrainingArgs(**clean_config)
        except Exception as e:
            print(f"   ❌ TrainingArgs 생성 실패: {e}")
            # 최소 필수 설정으로 폴백
            fallback_config = clean_config.copy()
            if 'prior_model' not in fallback_config:
                fallback_config['prior_model'] = 'QCBM'
            args = TrainingArgs(**fallback_config)
        
        # 실험 디렉토리 생성 (TrainingArgs 메소드 사용)
        args.create_experiment_dir()
        
        print(f"   🎯 실험 실행 중... (예상 시간: {config['lstm_n_epochs']} epochs)")
        print("   💡 진행 상황은 터미널 출력 또는 WandB에서 확인하세요.")
        
        # 메인 실험 실행
        main()
        
        # 성공 시간 계산
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n🎉 실험 완료!")
        print(f"   ⏱️ 총 실행 시간: {elapsed_time/3600:.2f}시간 ({elapsed_time/60:.1f}분)")
        print(f"   📁 결과 저장: {experiment_dir}")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n❌ 실험 실행 중 오류 발생!")
        print(f"   ⏱️ 실행 시간: {elapsed_time/60:.1f}분")
        print(f"   🐛 오류 내용: {str(e)}")
        print("\n📋 상세 오류 정보:")
        traceback.print_exc()
        
        # 오류 로그 저장
        error_log_path = experiment_dir / "error_log.txt"
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"실험 실행 오류\n")
            f.write(f"시간: {datetime.now()}\n")
            f.write(f"실행 시간: {elapsed_time/60:.1f}분\n")
            f.write(f"오류: {str(e)}\n\n")
            f.write("상세 오류 정보:\n")
            f.write(traceback.format_exc())
        
        print(f"   📄 오류 로그 저장: {error_log_path}")
        return False


def print_post_experiment_info(config):
    """실험 후 정보 출력"""
    print("\n📊 실험 후 확인사항:")
    
    # 결과 디렉토리
    experiment_dir = Path(config['experiment_root'])
    if experiment_dir.exists():
        print(f"   📁 결과 디렉토리: {experiment_dir.absolute()}")
        
        # 주요 결과 파일들 확인
        key_files = [
            "stats/training_summary.csv",
            "plots",
            "logs/experiment_log.pkl"
        ]
        
        for file_path in key_files:
            full_path = experiment_dir / file_path
            if full_path.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} (생성되지 않음)")
    
    # WandB 정보
    if config.get('use_wandb', False):
        print(f"\n📈 WandB 대시보드:")
        project = config.get('wandb_project', 'qcbm-lstm')
        print(f"   🌐 프로젝트: {project}")
        print(f"   📊 URL: https://wandb.ai/[your-entity]/{project}")
        print("   💡 로그인 후 실험 결과를 확인하세요.")
    
    # 성능 분석 추천
    print(f"\n🔍 권장 분석:")
    print("   📊 training/test_loss 비교로 오버피팅 확인")
    print("   🧬 molecules/generated_samples로 분자 품질 확인")
    print("   📈 qcbm/distribution_analysis로 QCBM 학습 확인")
    print("   ⏱️ epoch_time으로 성능 개선 확인")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="QCBM-LSTM 병렬처리 최적화 실험 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_parallel_experiment.py                           # 기본 설정으로 실행
  python run_parallel_experiment.py --config custom.json     # 커스텀 설정으로 실행
  python run_parallel_experiment.py --dry-run                # 설정만 확인
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='settings/parallel_experiment.json',
        help='설정 파일 경로 (기본값: settings/parallel_experiment.json)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 실험 없이 설정만 확인'
    )
    
    args = parser.parse_args()
    
    # 배너 출력
    print_banner()
    
    # 시스템 리소스 확인
    system_ok = check_system_resources()
    
    # 설정 파일 로드
    config = load_config(args.config)
    if config is None:
        print("\n❌ 설정 파일 로드 실패. 실험을 중단합니다.")
        return 1
    
    # 설정 검증
    if not validate_config(config):
        print("\n❌ 설정 검증 실패. 실험을 중단합니다.")
        return 1
    
    # 실험 요약 출력
    print_experiment_summary(config)
    
    # 시스템 경고가 있을 경우 사용자 확인
    if not system_ok and not args.dry_run:
        print("\n⚠️ 시스템 권장사항을 충족하지 않습니다.")
        response = input("그래도 계속 진행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("실험이 취소되었습니다.")
            return 0
    
    # 실험 실행
    success = run_experiment(config, dry_run=args.dry_run)
    
    if success and not args.dry_run:
        print_post_experiment_info(config)
        print("\n🎊 모든 과정이 완료되었습니다!")
        return 0
    elif args.dry_run:
        print("\n✅ DRY RUN 완료 - 설정이 정상적으로 확인되었습니다.")
        return 0
    else:
        print("\n💥 실험 실행에 실패했습니다.")
        return 1


if __name__ == "__main__":
    exit(main()) 