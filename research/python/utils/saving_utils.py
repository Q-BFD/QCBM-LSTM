import os
import time
from pathlib import Path

import pandas as pd
import numpy as np
from rdkit.Chem import Draw
from rdkit import Chem

from .dataloader import save_obj


def save_epoch_results(epoch, compound_stats, args, prior_samples_current,
                      encoded_compounds, selfies, prior, model, prior_x, prior_y, dirs):
    """Save results for current epoch with improved organization."""
    rng = np.random.default_rng()

    # Save molecule images if valid compounds exist
    print(f"🧪 Attempting to generate molecule images for epoch {epoch}")
    print(f"📊 Valid compounds available: {len(compound_stats.valid_compounds)}")

    try:
        if len(compound_stats.valid_compounds) == 0:
            print("❌ No valid compounds found - cannot generate molecule images")
        else:
            # Select molecules for visualization
            if len(compound_stats.valid_compounds) > 20:
                selected_smiles = rng.choice(
                    list(compound_stats.valid_compounds), 20, replace=False
                ).tolist()
                print(f"🎯 Selected 20 random molecules from {len(compound_stats.valid_compounds)} valid compounds")
            else:
                selected_smiles = list(compound_stats.valid_compounds)
                print(f"🎯 Using all {len(selected_smiles)} valid compounds")

            print(f"🔬 Converting SMILES to molecules...")
            print(f"📝 Example SMILES: {selected_smiles[:3]}")

            # Convert SMILES to RDKit molecules, filtering out None values
            mols = []
            valid_smiles = []
            for i, smiles in enumerate(selected_smiles):
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    mols.append(mol)
                    valid_smiles.append(smiles)
                else:
                    print(f"⚠️ Invalid SMILES #{i+1}: {smiles}")

            print(f"✅ Successfully converted {len(mols)} out of {len(selected_smiles)} SMILES")

            if len(mols) > 0:
                # Create plots directory if it doesn't exist
                dirs['plots'].mkdir(exist_ok=True)

                # Generate molecule image
                print(f"🎨 Generating molecule grid image...")
                img = Draw.MolsToGridImage(
                    mols,
                    molsPerRow=min(5, len(mols)),  # Better layout for fewer molecules
                    subImgSize=(200, 200),         # Larger individual molecule images
                    returnPNG=False
                )

                # Save image
                img_path = dirs['plots'] / f"epoch_{epoch}_molecules.png"
                img.save(img_path)
                print(f"💾 Saved molecular images to: {img_path}")
                print(f"📊 Image contains {len(mols)} molecules in grid format")

                # Verify file was created
                if img_path.exists():
                    file_size = img_path.stat().st_size
                    print(f"✅ Image file verified - Size: {file_size} bytes")
                else:
                    print(f"❌ Image file was not created!")

            else:
                print("❌ No valid molecules could be generated from SMILES")

    except Exception as e:
        print(f"❌ Unable to draw molecules: {e}")
        import traceback
        traceback.print_exc()

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