import datetime
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("Warning: wandb is not available. WandB logging will be disabled.")


def init_wandb(args):
    """Initialize Weights & Biases logging."""
    if not args.use_wandb or not WANDB_AVAILABLE:
        print("📊 WandB monitoring disabled")
        return None
    
    try:
        # Generate experiment name if not provided
        experiment_name = args.experiment_name
        if experiment_name is None:
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
                "test_fraction": args.test_fraction,
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
        print("⚠️ WandB not available - skipping molecule logging")
        return
    
    try:
        # Log molecule image if it exists
        molecule_img_path = plots_dir / f"epoch_{epoch}_molecules.png"
        print(f"🔍 Checking for molecule image: {molecule_img_path}")
        
        if molecule_img_path.exists():
            print(f"✅ Found molecule image, uploading to WandB...")
            wandb.log({
                "molecules/generated_samples": wandb.Image(str(molecule_img_path), 
                                                         caption=f"Epoch {epoch} - Generated molecules")
            }, step=epoch)
            print(f"🚀 Successfully uploaded molecule image for epoch {epoch}")
        else:
            print(f"❌ Molecule image not found: {molecule_img_path}")
        
        # Log sample SMILES as table
        if len(compound_stats.valid_compounds) > 0:
            sample_smiles = list(compound_stats.valid_compounds)[:10]  # Top 10
            smiles_table = wandb.Table(
                columns=["SMILES", "Epoch"],
                data=[[smiles, epoch] for smiles in sample_smiles]
            )
            wandb.log({"molecules/sample_smiles": smiles_table}, step=epoch)
            print(f"📊 Uploaded SMILES table with {len(sample_smiles)} entries")
        else:
            print("⚠️ No valid compounds to upload as SMILES table")
            
    except Exception as e:
        print(f"⚠️ WandB molecule logging failed: {e}")
        import traceback
        traceback.print_exc()


def finish_wandb():
    """Finish WandB run."""
    if WANDB_AVAILABLE and wandb.run:
        try:
            wandb.finish()
            print("✅ WandB run finished")
        except Exception as e:
            print(f"⚠️ WandB finish failed: {e}")


def log_qcbm_distribution(epoch, prior_samples, plots_dir, num_histogram_samples=1000):
    """
    QCBM 샘플 분포를 histogram으로 wandb에 로그합니다.
    
    Args:
        epoch: 현재 에폭
        prior_samples: QCBM에서 생성된 샘플 (torch.Tensor 또는 numpy.ndarray)
        plots_dir: 플롯 저장 디렉토리
        num_histogram_samples: histogram에 사용할 샘플 수
    """
    if not WANDB_AVAILABLE or not wandb.run:
        return
    
    try:
        # Convert to numpy if needed
        if hasattr(prior_samples, 'numpy'):
            samples = prior_samples.numpy()
        else:
            samples = np.array(prior_samples)
        
        # Limit number of samples for histogram
        if len(samples) > num_histogram_samples:
            indices = np.random.choice(len(samples), num_histogram_samples, replace=False)
            samples = samples[indices]
        
        num_qubits = samples.shape[1]
        
        # 1. 각 큐비트 위치별 0/1 분포 histogram
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'QCBM Distribution Analysis - Epoch {epoch}', fontsize=16)
        
        # 1-1. 각 큐비트별 활성화 확률
        qubit_probs = np.mean(samples, axis=0)
        axes[0, 0].bar(range(num_qubits), qubit_probs, alpha=0.7, color='skyblue')
        axes[0, 0].set_title('Qubit Activation Probabilities')
        axes[0, 0].set_xlabel('Qubit Index')
        axes[0, 0].set_ylabel('P(qubit=1)')
        axes[0, 0].set_ylim(0, 1)
        axes[0, 0].grid(True, alpha=0.3)
        
        # 1-2. 비트스트링을 정수로 변환한 분포
        binary_to_int = np.array([int(''.join(map(str, sample.astype(int))), 2) for sample in samples])
        axes[0, 1].hist(binary_to_int, bins=min(50, 2**num_qubits), alpha=0.7, color='lightcoral')
        axes[0, 1].set_title('Binary Pattern Distribution (as integers)')
        axes[0, 1].set_xlabel('Binary Pattern (as integer)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 1-3. 각 샘플의 Hamming weight (1의 개수) 분포
        hamming_weights = np.sum(samples, axis=1)
        axes[1, 0].hist(hamming_weights, bins=range(num_qubits + 2), alpha=0.7, color='lightgreen')
        axes[1, 0].set_title('Hamming Weight Distribution')
        axes[1, 0].set_xlabel('Number of 1s in binary string')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 1-4. 상위 frequent patterns
        unique_patterns, counts = np.unique(samples, axis=0, return_counts=True)
        top_n = min(10, len(unique_patterns))
        top_indices = np.argsort(counts)[-top_n:][::-1]
        
        top_patterns = [''.join(map(str, unique_patterns[i].astype(int))) for i in top_indices]
        top_counts = counts[top_indices]
        
        y_pos = np.arange(len(top_patterns))
        axes[1, 1].barh(y_pos, top_counts, alpha=0.7, color='gold')
        axes[1, 1].set_yticks(y_pos)
        axes[1, 1].set_yticklabels(top_patterns)
        axes[1, 1].set_title(f'Top {top_n} Most Frequent Patterns')
        axes[1, 1].set_xlabel('Frequency')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        qcbm_plot_path = plots_dir / f"epoch_{epoch}_qcbm_distribution.png"
        plt.savefig(qcbm_plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # Log to wandb
        wandb.log({
            "qcbm/distribution_analysis": wandb.Image(str(qcbm_plot_path),
                                                     caption=f"QCBM Distribution - Epoch {epoch}"),
            "qcbm/avg_hamming_weight": np.mean(hamming_weights),
            "qcbm/unique_patterns": len(unique_patterns),
            "qcbm/entropy": -np.sum((counts/len(samples)) * np.log2(counts/len(samples) + 1e-10)),
            "qcbm/max_pattern_freq": np.max(counts) / len(samples)
        }, step=epoch)
        
        # Individual histograms for each metric
        wandb.log({
            "qcbm/qubit_probabilities": wandb.Histogram(qubit_probs),
            "qcbm/binary_patterns_as_int": wandb.Histogram(binary_to_int),
            "qcbm/hamming_weights": wandb.Histogram(hamming_weights)
        }, step=epoch)
        
        print(f"📊 QCBM distribution logged to WandB for epoch {epoch}")
        print(f"   - Unique patterns: {len(unique_patterns)}/{len(samples)}")
        print(f"   - Average Hamming weight: {np.mean(hamming_weights):.2f}")
        print(f"   - Entropy: {-np.sum((counts/len(samples)) * np.log2(counts/len(samples) + 1e-10)):.2f}")
        
    except Exception as e:
        print(f"⚠️ QCBM distribution logging failed: {e}")
        import traceback
        traceback.print_exc() 