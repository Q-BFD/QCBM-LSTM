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
from .selfies_encoding import SelfiesEncoding
from .selfies_encoding_parallel import ParallelSelfiesEncoding, create_parallel_dataset
from .filters import legacy_apply_filters, combine_filter, reward_fc
from .filters_fast import fast_reward_fc, minimal_reward_fc
from .filters_parallel import reward_fc_optimized
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


def create_experiment_directories(args):
    """Create experiment directory and return paths for result storage."""
    # Create main experiment directory and info file
    args.create_experiment_dir()
    
    base_dir = Path(args.experiment_root)
    
    # Return only the directories that are actually used
    # Subdirectories will be created automatically when files are saved
    return {
        'base': base_dir,
        'checkpoints': base_dir / "checkpoints",     # 모델 체크포인트
        'samples': base_dir / "samples",             # 생성된 분자 샘플  
        'plots': base_dir / "plots",                 # 분자 이미지, 그래프
        'logs': base_dir / "logs",                   # 실험 로그
        'stats': base_dir / "stats"                  # 통계 데이터
    }


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
        print(f"Creating dataset from {path_to_dataset}...")
        
        # 병렬 처리 옵션 확인
        use_parallel = getattr(args, 'use_parallel_dataset', False)
        
        if use_parallel:
            print("🚀 병렬 데이터셋 생성 모드 활성화")
            parallel_cores = getattr(args, 'parallel_dataset_cores', None)
            chunk_size = getattr(args, 'parallel_dataset_chunk_size', 10000)
            
            data, selfies = create_parallel_dataset(
                path_to_dataset,
                n_cores=parallel_cores,
                chunk_size=chunk_size
            )
        else:
            print("📊 순차 데이터셋 생성 모드")
            selfies = SelfiesEncoding(path_to_dataset, dataset_identifier="KRAS_Dataset_1M")
            encoded_samples_th = torch.tensor(selfies.encoded_samples)
            data = encoded_samples_th.float()
        
        save_obj([data, selfies], f"{path_to_pickle_data}.pkl")
        print(f"Dataset saved to {path_to_pickle_data}.pkl")
    
    # Load pickle file
    print(f"Loading dataset from {path_to_pickle_data}.pkl...")
    object_loaded = load_obj(f"{path_to_pickle_data}.pkl")
    selfies = object_loaded[1]
    train_compounds = selfies.valid_smiles
    data = object_loaded[0]
    print(f"Dataset loaded successfully. Shape: {data.shape}")
    print(f"Number of valid SMILES: {len(train_compounds)}")
    
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


# =============================================================================
# Model Creation Utils
# =============================================================================

def setup_filter_functions(args):
    """Set up filter and reward functions."""
    validity_fn = partial(
        combine_filter,
        max_mol_weight=args.max_mol_weight,
        filter_fc=legacy_apply_filters,
        disable_tqdm=True
    )
    
    # 병렬처리 vs 일반 처리 선택
    if hasattr(args, 'use_parallel_reward') and args.use_parallel_reward:
        print(f"🚀 Using parallel reward computation:")
        print(f"   Cores: {args.parallel_n_cores}")
        print(f"   Chunk size: {args.parallel_chunk_size}")
        print(f"   Expected speedup: ~10x faster")
        
        rew_fc = partial(
            reward_fc_optimized,
            max_mol_weight=args.max_mol_weight,
            chunk_size=args.parallel_chunk_size,
            n_cores=args.parallel_n_cores
        )
    else:
        # 빠른 reward 함수 선택 (기존 로직)
        if hasattr(args, 'fast_reward') and args.fast_reward == 'minimal':
            print("🚀 Using minimal reward function (865x faster)")
            rew_fc = partial(minimal_reward_fc, max_mol_weight=args.max_mol_weight)
        elif hasattr(args, 'fast_reward') and args.fast_reward == 'fast':
            print("🚀 Using fast reward function (83x faster)")
            rew_fc = partial(fast_reward_fc, max_mol_weight=args.max_mol_weight)
        else:
            print("📊 Using original reward function (full accuracy)")
            rew_fc = partial(
                reward_fc,
                max_mol_weight=args.max_mol_weight,
                filter_fc=legacy_apply_filters
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
        vocab_size=selfies.num_emd,
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

def print_epoch_summary(epoch, compound_stats, epoch_time):
    """Print formatted epoch summary."""
    print(f"\n{'='*60}")
    print(f"EPOCH {epoch} SUMMARY")
    print(f"{'='*60}")
    print(f"Execution time: {epoch_time:.2f} seconds")
    print(f"Unique compounds: {compound_stats.n_unique:,}")
    print(f"Valid compounds: {compound_stats.n_valid:,}")
    print(f"Unseen compounds: {compound_stats.n_unseen:,}")
    print(f"Unique fraction: {compound_stats.unique_fraction:.4f}")
    print(f"Valid fraction: {compound_stats.valid_fraction:.4f}")
    print(f"Diversity fraction: {compound_stats.diversity_fraction:.4f}")
    print(f"{'='*60}") 