"""
Main script for KRAS drug discovery using QCBM and LSTM models.
This script orchestrates the training process using utility functions.
"""

import time
import torch
from functools import partial
from tqdm import tqdm
import cProfile
import pstats
import io

# Import utility functions
import sys
import os
# Add parent directory to path for imports from research root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.training_utils import (
    setup_environment, parse_arguments,
    load_or_create_dataset, create_dataloader, setup_filter_functions,
    create_prior_model, create_lstm_model, print_epoch_summary,
    create_train_test_dataloaders
)
from utils.saving_utils import (
    save_epoch_results, save_generation_samples, save_training_summary
)
from utils.wandb_utils import (
    init_wandb, log_epoch_metrics, log_molecules_to_wandb, log_qcbm_distribution, finish_wandb
)
from utils.experiment_manager import ExperimentManager

# Import custom modules
from utils.filters import get_diversity
from utils.compound_stat import compute_compound_stats


def main():
    """Main training loop for KRAS drug discovery."""
    
    # =============================================================================
    # Setup and Initialization
    # =============================================================================
    setup_environment()
    args = parse_arguments()
    
    # Setup experiment environment using the manager
    manager = ExperimentManager(args)
    dirs = manager.get_directories()
    
    print(f"[Info] 모든 결과는 다음 디렉토리에 저장됩니다: {dirs['base']}")
    
    # Initialize WandB monitoring
    wandb_run = init_wandb(args)
    
    # Load data
    data, selfies, train_compounds = load_or_create_dataset(args)
    
    # Create train/test split
    print(f"\n========== Data Split Configuration ==========")
    train_dataloader, test_dataloader = create_train_test_dataloaders(data, args, test_fraction=args.test_fraction)
    print(f"Train batches: {len(train_dataloader)}")
    print(f"Test batches: {len(test_dataloader)}")
    print(f"Test fraction: {args.test_fraction*100:.1f}%")
    
    # Setup functions and models
    validity_fn, rew_fc = setup_filter_functions(args)
    diversity_fn = get_diversity
    decoder_fn = selfies.decode
    
    print(f"\n========== Models Configuration ==========")
    
    # Create models
    prior = create_prior_model(args)
    model = create_lstm_model(args, selfies)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"Prior model: {args.prior_model}")
    print(f"LSTM layers: {args.n_lstm_layers}")
    print(f"Training epochs: {args.lstm_n_epochs}")
    print(f"Batch size: {args.batch_size}")
    
    # =============================================================================
    # Training Loop
    # =============================================================================
    all_compound_stats = []
    
    for epoch in range(1, args.lstm_n_epochs + 1):
        print(f"\n{'='*80}")
        print(f"EPOCH {epoch}/{args.lstm_n_epochs}")
        print(f"{'='*80}")
        epoch_start_time = time.perf_counter()
        
        # -------------------------------------------------------------------------
        # LSTM Training Phase
        # -------------------------------------------------------------------------
        print("[Step 1/6] Training LSTM model...")
        model.train()
        
        epoch_losses = []
        print(f"Training on {len(train_dataloader)} batches...")
        
        # Use tqdm with better settings for remote/SSH environments
        with tqdm(
            total=len(train_dataloader), 
            desc="Training LSTM", 
            ncols=100,
            leave=True,
            position=0,
            ascii=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}'
        ) as pbar:
            for batch_idx, batch in enumerate(train_dataloader):
                inputs = batch
                batch_size = inputs.size(0)
                
                # Generate prior samples
                prior_samples, _, _ = prior.generate(batch_size, sampler=None, backend=None)
                
                # Train LSTM
                batch_result = model.train_on_batch(inputs, prior_samples)
                epoch_losses.append(batch_result['loss'])
                
                pbar.set_postfix({"Loss": f"{batch_result['loss']:.4f}"})
                pbar.update()
                
                # Print progress every 10 batches as backup
                if (batch_idx + 1) % 10 == 0:
                    print(f"  Batch {batch_idx + 1}/{len(train_dataloader)}, Loss: {batch_result['loss']:.4f}")
        
        train_loss = sum(epoch_losses) / len(epoch_losses)
        print(f"✅ LSTM training completed. Average train loss: {train_loss:.4f}")
        
        # -------------------------------------------------------------------------
        # Test Loss Evaluation
        # -------------------------------------------------------------------------
        print("[Step 1.5/6] Evaluating on test set...")
        model.eval()
        
        test_losses = []
        with torch.no_grad():
            for test_batch in test_dataloader:
                test_inputs = test_batch
                test_batch_size = test_inputs.size(0)
                
                # Generate prior samples for test
                test_prior_samples, _, _ = prior.generate(test_batch_size, sampler=None, backend=None)
                
                # Evaluate on test batch
                test_result = model.evaluate_on_batch(test_inputs, test_prior_samples)
                test_losses.append(test_result['test_loss'])
        
        test_loss = sum(test_losses) / len(test_losses)
        print(f"✅ Test evaluation completed. Average test loss: {test_loss:.4f}")
        
        # -------------------------------------------------------------------------
        # Generation and Evaluation Phase
        # -------------------------------------------------------------------------
        model.eval()
        
        print("[Step 2/6] Generating compounds with LSTM...")
        prior_samples_current, _, _ = prior.generate(args.n_test_samples, sampler=None, backend=None)
        encoded_compounds = model.generate(prior_samples_current)
        
        print("[Step 3/6] Calculating compound statistics...")
        compound_stats = compute_compound_stats(
            encoded_compounds,
            decoder_fn,
            diversity_fn,
            validity_fn,
            train_compounds
        )
        
        # -------------------------------------------------------------------------
        # Prior Training Phase
        # -------------------------------------------------------------------------
        print("[Step 4/6] Training prior model...")
        
        # Calculate rewards for prior training
        datanew = rew_fc(list(compound_stats.all_compounds)).cpu()
        soft = torch.nn.Softmax(dim=0)
        probs = soft(datanew)
        
        # Train prior model
        prior_x = prior_samples_current
        prior_y = probs
        result = prior.train_on_batch(
            prior_x, prior_y, 
            sampler=None, backend=None, 
            n_epochs=args.prior_n_epochs
        )
        
        # Extract prior model loss
        prior_loss = result[1][-1] if len(result) > 1 and len(result[1]) > 0 else None
        
        # -------------------------------------------------------------------------
        # Final Generation and Evaluation
        # -------------------------------------------------------------------------
        print("[Step 5/6] Generating compounds after prior training...")
        prior_samples_current, _, _ = prior.generate(args.n_test_samples, sampler=None, backend=None)
        encoded_compounds = model.generate(prior_samples_current)
        
        # Log QCBM distribution to WandB
        log_qcbm_distribution(epoch, prior_samples_current, dirs['plots'], num_histogram_samples=1000)
        
        # Final evaluation with verbose output
        validity_fn_verbose = partial(
            combine_filter,
            max_mol_weight=args.max_mol_weight,
            filter_fc=legacy_apply_filters,
            disable_tqdm=False
        )
        
        compound_stats = compute_compound_stats(
            encoded_compounds,
            decoder_fn,
            diversity_fn,
            validity_fn_verbose,
            train_compounds,
        )
        
        all_compound_stats.append(compound_stats)
        
        # -------------------------------------------------------------------------
        # Save Results
        # -------------------------------------------------------------------------
        print("[Step 6/6] Saving epoch results...")
        
        # Save epoch results with improved organization
        save_epoch_results(
            epoch, compound_stats, args, prior_samples_current,
            encoded_compounds, selfies, prior, model, prior_x, prior_y, dirs
        )
        
        # Save generation samples separately
        save_generation_samples(epoch, compound_stats, dirs)
        
        # Calculate epoch time and print summary
        epoch_end_time = time.perf_counter()
        epoch_time = epoch_end_time - epoch_start_time
        
        print_epoch_summary(epoch, compound_stats, epoch_time, train_loss, test_loss)
        
        # Log metrics to WandB
        additional_metrics = {
            "training/lstm_loss": train_loss,
            "training/test_loss": test_loss,
            "training/batch_count": len(train_dataloader),
            "training/test_batch_count": len(test_dataloader)
        }
        
        if prior_loss is not None:
            additional_metrics["training/prior_loss"] = prior_loss
        
        log_epoch_metrics(epoch, compound_stats, epoch_time, additional_metrics)
        log_molecules_to_wandb(epoch, compound_stats, dirs['plots'])
    
    # =============================================================================
    # Final Summary
    # =============================================================================
    print(f"\n{'='*80}")
    print("TRAINING COMPLETED")
    print(f"{'='*80}")
    
    # Save comprehensive training summary
    save_training_summary(all_compound_stats, args, dirs)
    
    # Print final statistics
    best_stats = max(all_compound_stats, key=lambda x: x.valid_fraction)
    best_epoch = all_compound_stats.index(best_stats) + 1
    
    print(f"\nBest Performance (Epoch {best_epoch}):")
    print(f"  Valid fraction: {best_stats.valid_fraction:.4f}")
    print(f"  Diversity: {best_stats.diversity_fraction:.4f}")
    print(f"  Unique fraction: {best_stats.unique_fraction:.4f}")
    print(f"  Total valid compounds: {best_stats.n_valid:,}")
    print(f"\nAll results saved to: {dirs['base']}")
    print("Training completed successfully! 🎉")
    
    # Finish WandB logging
    finish_wandb()


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()

    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    
    print("\n" + "="*80)
    print("PERFORMANCE PROFILE (TOP 20 CUMULATIVE TIME)")
    print("="*80)
    ps.print_stats(20)
    print(s.getvalue())
    print("="*80)
    