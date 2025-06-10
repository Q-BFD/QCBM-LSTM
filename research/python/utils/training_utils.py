"""
Utility functions for KRAS drug discovery with QCBM and LSTM models.
This module contains helper functions for data processing, model creation, and result saving.
"""

import os
import time
from pathlib import Path
from argparse import ArgumentParser
from functools import partial

import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from tqdm import tqdm
from rdkit.Chem import Draw
from rdkit import Chem, RDLogger

# Import custom modules
import sys
import os
# Add the research directory to sys.path for absolute imports
research_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(research_root)

# Import from the same utils package
from .selfies_encoding import SelfiesEncoding, truncate_smiles
from .filters import get_diversity, legacy_apply_filters, combine_filter, reward_fc
from .dataloader import new_data_loader, save_obj, load_obj
from .compound_stat import compute_compound_stats

# Import from other modules  
from settings.training_para import TrainingArgs
from model.lstm.noisy_lstm_v3 import NoisyLSTMv3
from model.prior.prior_cls import RandomChoiceSampler
from model.prior.prior_qcbm import SingleBasisQCBM, QCBMAnsatz, ScipyOptimizer

# Optional imports for quantum computing
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("Warning: wandb or qiskit not available. Some features may be disabled.")


# =============================================================================
# WandB Integration Utils
# =============================================================================

def init_wandb(args):
    """Initialize Weights & Biases logging."""
    if not args.use_wandb or not WANDB_AVAILABLE:
        print("📊 WandB monitoring disabled")
        return None
    
    try:
        # Generate experiment name if not provided
        experiment_name = args.experiment_name
        if experiment_name is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"{args.prior_model}_temp{args.temprature}_batch{args.batch_size}_{timestamp}"
        
        # Initialize wandb
        wandb_run = wandb.init(
            project=args.wandb_project,
            entity=args.wandb_entity,
            name=experiment_name,
            config={
                "prior_model": args.prior_model,
                "temperature": args.temprature,
                "batch_size": args.batch_size,
                "lstm_epochs": args.lstm_n_epochs,
                "lstm_layers": args.n_lstm_layers,
                "hidden_dim": args.hidden_dim,
                "embedding_dim": args.embedding_dim,
                "device": args.device,
                "dataset_id": args.data_set_id,
                "dataset_fraction": args.data_set_fraction,
                "prior_epochs": args.prior_n_epochs,
                "qcbm_layers": args.n_qcbm_layers,
                "qcbm_shots": args.n_qcbm_shots,
                "optimizer": args.optimizer_name,
                "max_mol_weight": args.max_mol_weight
            },
            tags=[args.prior_model, f"temp_{args.temprature}", f"batch_{args.batch_size}"]
        )
        
        print(f"🚀 WandB initialized: {wandb_run.name}")
        print(f"📊 Dashboard: {wandb_run.url}")
        return wandb_run
        
    except Exception as e:
        print(f"❌ WandB initialization failed: {e}")
        return None


def log_epoch_metrics(epoch, compound_stats, epoch_time, additional_metrics=None):
    """Log epoch metrics to WandB."""
    if not WANDB_AVAILABLE or not wandb.run:
        return
    
    try:
        metrics = {
            "epoch": epoch,
            "epoch_time": epoch_time,
            "compounds/unique_count": compound_stats.n_unique,
            "compounds/valid_count": compound_stats.n_valid,
            "compounds/unseen_count": compound_stats.n_unseen,
            "fractions/unique": compound_stats.unique_fraction,
            "fractions/valid": compound_stats.valid_fraction,
            "fractions/diversity": compound_stats.diversity_fraction,
        }
        
        # Add any additional metrics
        if additional_metrics:
            metrics.update(additional_metrics)
        
        wandb.log(metrics, step=epoch)
        
    except Exception as e:
        print(f"⚠️ WandB logging failed: {e}")


def log_molecules_to_wandb(epoch, compound_stats, plots_dir):
    """Log molecule images to WandB."""
    if not WANDB_AVAILABLE or not wandb.run:
        return
    
    try:
        # Log molecule image if it exists
        molecule_img_path = plots_dir / f"epoch_{epoch}_molecules.png"
        if molecule_img_path.exists():
            wandb.log({
                "molecules/generated_samples": wandb.Image(str(molecule_img_path), 
                                                         caption=f"Epoch {epoch} - Generated molecules")
            }, step=epoch)
        
        # Log sample SMILES as table
        if len(compound_stats.valid_compounds) > 0:
            sample_smiles = list(compound_stats.valid_compounds)[:10]  # Top 10
            smiles_table = wandb.Table(
                columns=["SMILES", "Epoch"],
                data=[[smiles, epoch] for smiles in sample_smiles]
            )
            wandb.log({"molecules/sample_smiles": smiles_table}, step=epoch)
            
    except Exception as e:
        print(f"⚠️ WandB molecule logging failed: {e}")


def finish_wandb():
    """Finish WandB run."""
    if WANDB_AVAILABLE and wandb.run:
        try:
            wandb.finish()
            print("✅ WandB run finished")
        except Exception as e:
            print(f"⚠️ WandB finish failed: {e}")


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
        prior_sample_dim=args.prior_size,
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

def save_epoch_results(epoch, compound_stats, args, prior_samples_current, 
                      encoded_compounds, selfies, prior, model, prior_x, prior_y, dirs):
    """Save results for current epoch with improved organization."""
    rng = np.random.default_rng()
    
    # Save molecule images if valid compounds exist
    try:
        if len(compound_stats.valid_compounds) > 20:
            selected_smiles = rng.choice(
                list(compound_stats.valid_compounds), 20, replace=False
            )
        else:
            selected_smiles = list(compound_stats.valid_compounds)
        
        if selected_smiles:
            # Create plots directory if it doesn't exist
            dirs['plots'].mkdir(exist_ok=True)
            
            mols = [Chem.MolFromSmiles(smile_) for smile_ in selected_smiles]
            img = Draw.MolsToGridImage(mols, molsPerRow=20, returnPNG=False)
            img.save(dirs['plots'] / f"epoch_{epoch}_molecules.png")
            print(f"[Info] Saved molecular images for epoch {epoch}")
            print(f"[Info] Example valid SMILES: {selected_smiles[:3]}")
    except Exception as e:
        print(f"Unable to draw molecules: {e}")
    
    # Save model checkpoint with improved naming
    try:
        checkpoint_data = {
            "epoch": epoch,
            "prior_samples": prior_samples_current,
            "model_samples": encoded_compounds,
            "selfies": selfies,
            "prior": prior,
            "model": model,
            "prior_x": prior_x,
            "prior_y": prior_y,
            "compound_stats": compound_stats,
            "timestamp": time.time()
        }
        
        # Create checkpoints directory if it doesn't exist
        dirs['checkpoints'].mkdir(exist_ok=True)
        
        checkpoint_path = dirs['checkpoints'] / f"checkpoint_epoch_{epoch:03d}.pkl"
        save_obj(checkpoint_data, str(checkpoint_path))
        print(f"[Info] Saved checkpoint: {checkpoint_path}")
        
    except Exception as e:
        print(f"Unable to save checkpoint for epoch {epoch}: {e}")


def save_generation_samples(epoch, compound_stats, dirs):
    """Save generated samples for each epoch."""
    try:
        samples_data = {
            "epoch": epoch,
            "all_compounds": list(compound_stats.all_compounds),
            "unique_compounds": list(compound_stats.unique_compounds), 
            "valid_compounds": list(compound_stats.valid_compounds),
            "unseen_compounds": list(compound_stats.unseen_compounds),
            "statistics": {
                "n_unique": compound_stats.n_unique,
                "n_valid": compound_stats.n_valid,
                "n_unseen": compound_stats.n_unseen,
                "unique_fraction": compound_stats.unique_fraction,
                "valid_fraction": compound_stats.valid_fraction,
                "diversity_fraction": compound_stats.diversity_fraction,
            }
        }
        
        # Create samples directory if it doesn't exist
        dirs['samples'].mkdir(exist_ok=True)
        
        # Save as CSV for easy analysis
        df = pd.DataFrame({'smiles': samples_data['all_compounds']})
        csv_path = dirs['samples'] / f"generated_epoch_{epoch:03d}.csv"
        df.to_csv(csv_path, index=False)
        
        # Save detailed data as pickle
        pkl_path = dirs['samples'] / f"samples_epoch_{epoch:03d}.pkl"
        save_obj(samples_data, str(pkl_path))
        
        print(f"[Info] Saved generation samples for epoch {epoch}")
        
    except Exception as e:
        print(f"Unable to save generation samples for epoch {epoch}: {e}")


def save_training_summary(all_compound_stats, args, dirs):
    """Save comprehensive training summary."""
    print("[Step] Saving training summary...")
    
    try:
        # Create summary statistics
        summary_rows = []
        for i, stats in enumerate(all_compound_stats, 1):
            summary_rows.append({
                "epoch": i,
                "n_unique": stats.n_unique,
                "n_valid": stats.n_valid,
                "n_unseen": stats.n_unseen,
                "unique_fraction": stats.unique_fraction,
                "valid_fraction": stats.valid_fraction,
                "diversity_fraction": stats.diversity_fraction,
                "valid_smiles_sample": ";".join(list(stats.valid_compounds)[:10])  # First 10 only
            })
        
        summary_df = pd.DataFrame(summary_rows)
        
        # Create directories if they don't exist
        dirs['stats'].mkdir(exist_ok=True)
        dirs['logs'].mkdir(exist_ok=True)
        
        # Save summary CSV
        summary_path = dirs['stats'] / "training_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        
        # Save detailed statistics as pickle
        detailed_path = dirs['stats'] / "detailed_compound_stats.pkl"
        save_obj(all_compound_stats, str(detailed_path))
        
        # Create and save training log
        log_data = {
            "experiment_config": vars(args),
            "total_epochs": len(all_compound_stats),
            "final_stats": {
                "best_valid_fraction": max(stats.valid_fraction for stats in all_compound_stats),
                "best_diversity": max(stats.diversity_fraction for stats in all_compound_stats),
                "best_unique_fraction": max(stats.unique_fraction for stats in all_compound_stats),
            },
            "timestamp": time.time()
        }
        
        log_path = dirs['logs'] / "experiment_log.pkl"
        save_obj(log_data, str(log_path))
        
        print(f"[Success] Training summary saved to {summary_path}")
        print(f"[Success] Detailed statistics saved to {detailed_path}")
        print(f"[Success] Experiment log saved to {log_path}")
        
    except Exception as e:
        print(f"Error saving training summary: {e}")


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