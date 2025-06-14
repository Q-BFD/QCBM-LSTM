"""
Utility functions for KRAS drug discovery with QCBM and LSTM models.
This module contains helper functions for data processing, model creation, and result saving.
"""

import os
from pathlib import Path
from argparse import ArgumentParser
from functools import partial

import torch
from rdkit import RDLogger

# Import custom modules
import sys
# Add the research directory to sys.path for absolute imports
research_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(research_root)

# Import from the same utils package
from .selfies_encoding import SelfiesEncoder
from .filters import calculate_rewards
from .dataloader import new_data_loader, save_obj, load_obj

# Import from other modules
from settings.training_para import TrainingArgs
from model.lstm.noisy_lstm_v3 import NoisyLSTMv3
from model.prior.prior_cls import RandomChoiceSampler
from model.prior.prior_qcbm import SingleBasisQCBM, QCBMAnsatz, ScipyOptimizer


# =============================================================================
# Environment and Configuration Utils
# =============================================================================

def setup_environment():
    """Set up the working directory and disable RDKit logging."""
    # Navigate to research root directory (parent of python folder)
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(current_dir)
    RDLogger.DisableLog("rdApp.*")
    print(f"\n========== Start script ==========")
    print(f"Working directory: {os.getcwd()}")


def parse_arguments():
    """Parse command line arguments and return training configuration."""
    argparser = ArgumentParser()
    argparser.add_argument(
        "--config_file",
        type=str,
        default=None,
        help="Path to config file for training. If not provided, uses default values."
    )
    namespace = argparser.parse_args()
    
    # Use config file if provided, otherwise use defaults from TrainingArgs
    if namespace.config_file and os.path.exists(namespace.config_file):
        print(f"📄 Using config file: {namespace.config_file}")
        args = TrainingArgs.from_file(namespace.config_file)
    else:
        if namespace.config_file:
            print(f"⚠️  Config file not found: {namespace.config_file}")
        print("🎯 Using default configuration from TrainingArgs")
        # Create with all defaults - only need to specify required fields
        args = TrainingArgs(prior_model="QCBM")  # prior_model is the only required field
    
    return args


# =============================================================================
# Data Processing Utils
# =============================================================================

def get_dataset_path(data_id):
    """Get dataset path based on ID."""
    dataset_by_id = {
        0: "data/KRAS_G12D/KRAS_G12D_inhibitors_update2023.csv",
        1: "data/KRAS_G12D/initial_dataset.csv",
        2: "data/KRAS_G12D/initial_data_with_chemistry42_syba_merged_v2.csv",
        3: "data/KRAS_G12D/initial_data_set_with_100k_hits.csv",
        4: "data/KRAS_G12D/1Mstoned_vsc_initial_dataset_insilico_chemistry42_filtered.csv",
        5: "/home/mghazi/workspace/Tartarus/datasets/docking.csv"
    }
    
    path_to_dataset = dataset_by_id.get(data_id, None)
    if path_to_dataset is None:
        raise ValueError(f"Invalid data set id: {data_id}")
    return path_to_dataset


def load_or_create_dataset(args):
    """Load dataset or create it if it doesn't exist."""
    data_id = int(args.data_set_id)
    path_to_dataset = get_dataset_path(data_id)
    path_to_pickle_data = path_to_dataset.split(".")[0]
    
    # If pickle file does not exist, create it
    if not os.path.isfile(f"{path_to_pickle_data}.pkl"):
        print(f"🗄️ Pickle file not found. Creating dataset from {path_to_dataset}...")
        
        # 새로운 통합 SelfiesEncoder 사용
        selfies_encoder = SelfiesEncoder(
            filepath=path_to_dataset,
            backend=args.selfies_backend,
            n_cores=args.selfies_n_jobs,
            chunk_size=args.parallel_dataset_chunk_size
        )
        data_tensor = selfies_encoder.encoded_samples.float()
        
        save_obj([data_tensor, selfies_encoder], f"{path_to_pickle_data}.pkl")
        print(f"💾 Dataset saved to {path_to_pickle_data}.pkl")
    
    # Load pickle file
    print(f"🔄 Loading dataset from {path_to_pickle_data}.pkl...")
    object_loaded = load_obj(f"{path_to_pickle_data}.pkl")
    data, selfies = object_loaded[0], object_loaded[1]
    train_compounds = selfies.valid_smiles # Assuming valid_smiles is populated
    
    print(f"✅ Dataset loaded successfully. Shape: {data.shape}")
    print(f"   Number of valid SMILES: {len(train_compounds):,}")
    
    return data, selfies, train_compounds


def create_dataloader(data, args):
    """Create data loader for training."""
    return new_data_loader(
        data=data,
        batch_size=args.batch_size,
        drop_last=True,
        shuffle=True,
        seed=123,
        fraction=args.data_set_fraction
    )


def split_train_test_data(data, test_fraction=0.1, seed=42):
    """
    데이터를 train/test로 분할합니다.
    
    Args:
        data: 전체 데이터셋 (torch.Tensor)
        test_fraction: test 데이터 비율 (기본값: 0.1 = 10%)
        seed: 랜덤 시드
    
    Returns:
        tuple: (train_data, test_data)
    """
    import torch
    import numpy as np
    
    # 재현 가능한 결과를 위한 시드 설정
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    # 데이터 크기
    total_size = len(data)
    test_size = int(total_size * test_fraction)
    train_size = total_size - test_size
    
    # 랜덤하게 인덱스 섞기
    indices = torch.randperm(total_size)
    
    # train/test 분할
    train_indices = indices[:train_size]
    test_indices = indices[train_size:]
    
    train_data = data[train_indices]
    test_data = data[test_indices]
    
    print(f"📊 데이터 분할 완료:")
    print(f"   - 전체 데이터: {total_size:,}개")
    print(f"   - 훈련 데이터: {train_size:,}개 ({(1-test_fraction)*100:.1f}%)")
    print(f"   - 테스트 데이터: {test_size:,}개 ({test_fraction*100:.1f}%)")
    
    return train_data, test_data


def create_train_test_dataloaders(data, args, test_fraction=0.1):
    """
    훈련/테스트 데이터로더를 생성합니다.
    
    Args:
        data: 전체 데이터셋
        args: 훈련 인자
        test_fraction: 테스트 데이터 비율
    
    Returns:
        tuple: (train_dataloader, test_dataloader)
    """
    # 데이터 분할
    train_data, test_data = split_train_test_data(data, test_fraction=test_fraction)
    
    # 훈련 데이터로더 (기존과 동일)
    train_dataloader = new_data_loader(
        data=train_data,
        batch_size=args.batch_size,
        drop_last=True,
        shuffle=True,
        seed=123,
        fraction=args.data_set_fraction
    )
    
    # 테스트 데이터로더 (셔플하지 않음)
    test_dataloader = new_data_loader(
        data=test_data,
        batch_size=args.batch_size,
        drop_last=False,  # 모든 테스트 데이터 사용
        shuffle=False,    # 테스트는 셔플하지 않음
        seed=123,
        fraction=1.0      # 테스트 데이터는 전체 사용
    )
    
    return train_dataloader, test_dataloader


# =============================================================================
# Model Creation Utils
# =============================================================================

def setup_filter_functions(args):
    """Set up filter and reward functions."""
    # validity_fn is currently not used in the main loop but kept for potential future use.
    # A simple lambda function is used as a placeholder.
    validity_fn = lambda x: True
    
    # Set up the reward function using the new unified calculate_rewards
    rew_fc = partial(
        calculate_rewards,
        reward_strategy=args.reward_strategy,
        max_mol_weight=args.max_mol_weight,
        n_cores=args.parallel_n_cores,
        chunk_size=args.parallel_chunk_size
    )
    
    return validity_fn, rew_fc


def create_prior_model(args):
    """Create and return the prior model based on configuration."""
    print(f"Creating {args.prior_model} prior model...")
    
    if args.prior_model == "classical":
        return RandomChoiceSampler(args.prior_size, choices=[0.0, 1.0])
    elif args.prior_model == "QCBM":
        depth = args.n_qcbm_layers
        nshot = args.n_qcbm_shots
        ansatz = QCBMAnsatz(args.num_qubits, depth)
        options = {
            'maxiter': args.prior_maxiter,
            'tol': args.prior_tol,
            'disp': False
        }
        optimizer = ScipyOptimizer(method='COBYLA', options=options)
        return SingleBasisQCBM(ansatz, optimizer, nshot=nshot)
    else:
        raise ValueError(f"Unknown prior model: {args.prior_model}")


def create_lstm_model(args, selfies):
    """Create and return the LSTM model."""
    print(f"Creating LSTM model with {args.n_lstm_layers} layers...")
    
    return NoisyLSTMv3(
        vocab_size=selfies.vocab_size,
        seq_len=selfies.max_length,
        sos_token_index=selfies.start_char_index,
        prior_sample_dim=args.num_qubits,
        padding_token_index=selfies.pad_char_index,
        hidden_dim=args.hidden_dim,
        embedding_dim=args.embedding_dim,
        n_layers=args.n_lstm_layers,
        do_greedy_sampling=args.do_greedy_sampling,
        sampling_temperature=args.temprature
    )


# =============================================================================
# Result Saving Utils
# =============================================================================

def print_epoch_summary(epoch, compound_stats, epoch_time, train_loss=None, test_loss=None):
    """Print formatted epoch summary."""
    print(f"\n{'='*60}")
    print(f"EPOCH {epoch} SUMMARY")
    print(f"{'='*60}")
    print(f"Execution time: {epoch_time:.2f} seconds")
    
    # Loss 정보 출력
    if train_loss is not None:
        print(f"Train loss: {train_loss:.4f}")
    if test_loss is not None:
        print(f"Test loss: {test_loss:.4f}")
    
    # 기존 compound 통계
    print(f"Unique compounds: {compound_stats.n_unique:,}")
    print(f"Valid compounds: {compound_stats.n_valid:,}")
    print(f"Unseen compounds: {compound_stats.n_unseen:,}")
    print(f"Unique fraction: {compound_stats.unique_fraction:.4f}")
    print(f"Valid fraction: {compound_stats.valid_fraction:.4f}")
    print(f"Diversity fraction: {compound_stats.diversity_fraction:.4f}")
    print(f"{'='*60}") 