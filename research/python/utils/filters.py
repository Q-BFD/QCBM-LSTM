"""
This module provides a flexible and efficient way to calculate rewards for molecules
based on various filtering strategies. It supports multiple reward calculation methods
and can run them in parallel for high performance.
"""
import os
import sys
import time
import multiprocessing as mp
from functools import partial

import torch
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, AllChem, rdmolops, rdMolDescriptors
from rdkit.Chem import rdFingerprintGenerator

# --- Configuration for SA_Score ---
try:
    from rdkit.Contrib import SA_Score as sascorer
except ImportError:
    try:
        from rdkit import RDConfig
        sys.path.append(os.path.join(RDConfig.RDContribDir, 'SA_Score'))
        import sascorer
    except ImportError:
        sascorer = None
        print("Warning: SA_Score (sascorer) could not be imported. SA_Score based rewards will be disabled.")

# --- File-level Filter Initialization ---
_filters_initialized = False
_pains_filters = []
_mcf_wehi_filters = []

def _initialize_filters():
    """Initializes PAINS and MCF/WEHI filters from files."""
    global _filters_initialized, _pains_filters, _mcf_wehi_filters
    if _filters_initialized:
        return

    try:
        research_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        pains_path = os.path.join(research_root, "data/valid-filter/pains.txt")
        with open(pains_path, "r") as f:
            pains_smarts = [line.split(" ")[0] for line in f if line.strip()]
        _pains_filters = [Chem.MolFromSmarts(smarts) for smarts in pains_smarts if smarts]

        mcf_path = os.path.join(research_root, 'data/valid-filter/mcf.csv')
        wehi_path = os.path.join(research_root, 'data/valid-filter/wehi_pains.csv')
        mcf_df = pd.read_csv(mcf_path)
        wehi_df = pd.read_csv(wehi_path, names=['smarts', 'names'])
        combined_df = pd.concat([mcf_df, wehi_df], ignore_index=True)
        mcf_wehi_smarts = combined_df['smarts'].values
        _mcf_wehi_filters = [Chem.MolFromSmarts(smarts) for smarts in mcf_wehi_smarts if smarts]
        
        _filters_initialized = True
        print("✅ PAINS and MCF/WEHI filters initialized successfully.")
    except Exception as e:
        print(f"⚠️ Filter initialization failed: {e}. Some functionalities may be disabled.")

# --- Public Functions ---

def get_diversity(smiles_ls):
    """Calculates the structural diversity of a list of SMILES strings."""
    pred_mols = [Chem.MolFromSmiles(s) for s in smiles_ls if s]
    pred_mols = [m for m in pred_mols if m is not None]
    if len(pred_mols) < 2:
        return 0.0

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=2048)
    pred_fps = [gen.GetFingerprint(mol) for mol in pred_mols]

    similarity = 0
    for i in range(len(pred_fps)):
        sims = DataStructs.BulkTanimotoSimilarity(pred_fps[i], pred_fps[:i])
        similarity += sum(sims)

    n_pairs = len(pred_mols) * (len(pred_mols) - 1) / 2
    diversity = 1 - (similarity / n_pairs) if n_pairs > 0 else 0
    return diversity * 100

def calculate_rewards(smiles_ls, 
                      reward_strategy: str = 'original', 
                      max_mol_weight: float = 800,
                      n_cores: int = None,
                      chunk_size: int = 2000):
    """
    Calculates reward scores for a list of SMILES strings in parallel.
    """
    _initialize_filters()

    reward_functions = {
        'original': _calculate_reward_original,
        'fast': _calculate_reward_fast,
        'minimal': _calculate_reward_minimal,
    }
    
    if reward_strategy not in reward_functions:
        raise ValueError(f"Invalid reward_strategy. Choose from {list(reward_functions.keys())}")
        
    single_reward_func = partial(reward_functions[reward_strategy], max_mol_weight=max_mol_weight)

    if n_cores is None:
        n_cores = min(mp.cpu_count(), 8)
    
    total_molecules = len(smiles_ls)
    if total_molecules == 0:
        return torch.Tensor([])
        
    effective_chunk_size = min(chunk_size, (total_molecules // n_cores) + 1) if n_cores > 0 else total_molecules
    if effective_chunk_size == 0: effective_chunk_size = 1

    print(f"🚀 Calculating rewards for {total_molecules:,} molecules...")
    print(f"   Strategy: {reward_strategy}, Cores: {n_cores}, Chunk Size: {effective_chunk_size:,}")

    start_time = time.time()
    
    with mp.Pool(n_cores) as pool:
        rewards = pool.map(single_reward_func, smiles_ls, chunksize=effective_chunk_size)
    
    elapsed_time = time.time() - start_time
    molecules_per_sec = total_molecules / elapsed_time if elapsed_time > 0 else 0
    
    print(f"✅ Reward calculation complete in {elapsed_time:.2f}s ({molecules_per_sec:,.0f} molecules/sec)")
    
    return torch.Tensor(rewards)

# --- Internal Reward Components (Building Blocks) ---

def _check_legacy_filters(mol, smi, max_mol_weight):
    if any(sub in smi for sub in ["C-", "N+", "C+", "S+", "S-", "O+"]): return 0
    if rdmolops.GetFormalCharge(mol) != 0: return 0
    if Descriptors.NumRadicalElectrons(mol) != 0: return 0
    if rdMolDescriptors.CalcNumBridgeheadAtoms(mol) > 2: return 0
    return 15

def _check_pains(mol):
    return 0 if any(mol.HasSubstructMatch(p) for p in _pains_filters) else 5

def _check_mcf_wehi(mol):
    h_mol = Chem.AddHs(mol)
    return 0 if any(h_mol.HasSubstructMatch(f) for f in _mcf_wehi_filters) else 5

def _check_sa_score(mol):
    return 30 if sascorer and sascorer.calculateScore(mol) < 4 else 0

def _check_molecular_weight(mol, max_mol_weight, min_mol_weight=300):
    mol_weight = Descriptors.ExactMolWt(mol)
    return 10 if min_mol_weight <= mol_weight <= max_mol_weight else 0

def _check_logp(mol, min_logp=-2, max_logp=5):
    logp = Descriptors.MolLogP(mol)
    return 10 if min_logp <= logp <= max_logp else 0
    
def _check_rotatable_bonds(mol, max_bonds=10):
    return 10 if Descriptors.NumRotatableBonds(mol) < max_bonds else 0

def _check_h_bonds(mol, max_hbd=5, max_hba=10):
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return 10 if hbd <= max_hbd and hba <= max_hba else 0

def _check_atom_count(mol, min_atoms=5, max_atoms=50):
    return 20 if min_atoms <= mol.GetNumAtoms() <= max_atoms else 0

# --- Internal Reward Calculation Strategies ---

def _calculate_reward_original(smiles, max_mol_weight=800):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: return 0
    
    reward = 1.0
    reward += _check_legacy_filters(mol, smiles, max_mol_weight)
    reward += _check_pains(mol)
    reward += _check_mcf_wehi(mol)
    reward += _check_sa_score(mol)
    return reward

def _calculate_reward_fast(smiles, max_mol_weight=800):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: return 0

    reward = 1.0 + 5
    reward += _check_molecular_weight(mol, max_mol_weight)
    reward += _check_logp(mol)
    reward += _check_rotatable_bonds(mol)
    reward += _check_h_bonds(mol)
    return reward

def _calculate_reward_minimal(smiles, max_mol_weight=800):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: return 0
        
    reward = 1.0 + 10
    reward += 20 if Descriptors.ExactMolWt(mol) <= max_mol_weight else 0
    reward += _check_atom_count(mol)
    return reward