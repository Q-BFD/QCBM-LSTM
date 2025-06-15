from dataclasses import dataclass
from typing import List, Set, Callable
from rdkit import Chem

from torch import Tensor

# Import filters directly to be used in stats calculation
from .filters import _check_legacy_filters, _check_pains, _check_mcf_wehi, _check_sa_score, sascorer


def is_valid_compound(smi: str, max_mol_weight: float = 800) -> bool:
    """
    Checks if a SMILES string represents a valid compound based on the 'original' reward criteria.
    This function consolidates the filtering logic for consistent validation.
    """
    if not smi or not isinstance(smi, str):
        return False
        
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return False
        
        # Check against all primary filters. If any fails, it's not valid.
        if _check_legacy_filters(mol, smi, max_mol_weight) == 0:
            return False
        if _check_pains(mol) == 0:
            return False
        if _check_mcf_wehi(mol) == 0:
            return False
        
        # Correctly check SA score. It should be less than 4.
        if sascorer and sascorer.calculateScore(mol) >= 4:
            return False
            
        return True
    except Exception:
        # If any error occurs during processing, treat as invalid
        return False

@dataclass
class CompoundsStatistics:
    unique_compounds: Set[str]  # generated compounds that are unique
    valid_compounds: Set[str]  # generated, unique compounds that are also valid
    unseen_compounds: Set[
        str
    ]  # generated, unique, valid compounds that are also not present in train data
    all_compounds: List[str]
    label_compounds: List[str]
    diversity_fraction: float
    valid_fraction: float
    unique_fraction: float
    # Diversity %
    # Fraction of molecules that pass the filter
    # Fraction of unique molecules

    @property
    def n_unique(self) -> int:
        return len(self.unique_compounds)

    @property
    def n_valid(self) -> int:
        return len(self.valid_compounds)

    @property
    def n_unseen(self) -> int:
        return len(self.unseen_compounds)

    @property
    def total_compounds(self) -> int:
        return len(self.all_compounds)


def canonicalize(smiles_list):
        return set(Chem.MolToSmiles(Chem.MolFromSmiles(s), canonical=True) for s in smiles_list if Chem.MolFromSmiles(s))

def compute_compound_stats(
    compounds: Tensor,
    decoder_fn: Callable[[Tensor], List[str]],
    diversity_fn: Callable,
    train_compounds: List[str],
) -> CompoundsStatistics:
    """
    Computes statistics for a batch of generated compounds.
    The validity is now checked using a consolidated `is_valid_compound` function
    that mirrors the 'original' reward strategy.
    """
    print("\n--- Computing Compound Stats ---")
    
    generated_compounds = decoder_fn(compounds)
    print(f"  - Decoded {len(generated_compounds)} compounds from tensor.")

    diversity_fraction = diversity_fn(generated_compounds)
    print(f"  - Calculated diversity: {diversity_fraction:.4f}")

    unqiue_generated_compounds = set(generated_compounds)
    print(f"  - Found {len(unqiue_generated_compounds)} unique compounds.")

    # Use the new, consistent validation function
    unique_valid_compounds = {
        s for s in unqiue_generated_compounds if is_valid_compound(s)
    }
    print(f"  - Found {len(unique_valid_compounds)} valid compounds after filtering.")

    unique_unseen_valid_compounds = unique_valid_compounds - set(train_compounds)
    print(f"  - Found {len(unique_unseen_valid_compounds)} unseen compounds (not in training set).")
    
    total_compounds = len(generated_compounds)
    unique_fraction = len(unqiue_generated_compounds) / total_compounds if total_compounds > 0 else 0
    filter_fraction = len(unique_valid_compounds) / len(unqiue_generated_compounds) if len(unqiue_generated_compounds) > 0 else 0

    print(f"  - Unique fraction: {unique_fraction:.2%}")
    print(f"  - Valid fraction (of unique): {filter_fraction:.2%}")
    print("---------------------------------")

    stats = CompoundsStatistics(
        unqiue_generated_compounds,
        unique_valid_compounds,
        unique_unseen_valid_compounds,
        generated_compounds,
        [1] * len(generated_compounds),
        diversity_fraction,
        filter_fraction,
        unique_fraction,
    )
    return stats