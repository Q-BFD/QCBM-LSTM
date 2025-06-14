import datetime

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