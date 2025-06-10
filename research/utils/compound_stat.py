from dataclasses import dataclass
from typing import List, Set, Callable
from rdkit import Chem

from torch import Tensor


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
    validity_fn: Callable[[List[str]], List[str]],
    train_compounds: List[str],
) -> CompoundsStatistics:
    generated_compounds = decoder_fn(compounds)

    # truncate samples by removing anything that comes after the `pad_char`
    # generated_compounds = truncate_fn(generated_compounds)
    diversity_fraction = diversity_fn(generated_compounds)

    unqiue_generated_compounds = set(generated_compounds)

    # gives us only valid unique compounds
    filtered_set = validity_fn(generated_compounds)
    unique_valid_compounds = set(filtered_set)

    # valid unique compounds that are also not present in the training data
    # unique_train_compounds = set(train_compounds)
    # unique_unseen_valid_compounds = unique_valid_compounds.difference(
    #     unique_train_compounds
    # )
    # print(2)
    unique_unseen_valid_compounds = unique_valid_compounds.difference(train_compounds)
    # print(3)
    # fraction of unique valid compounds that are unseen
    unique_fraction = 100 * len(unqiue_generated_compounds) / len(compounds)
    filter_fraction = 100 * len(filtered_set) / len(compounds)
    # print(4)
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
    # print(5)
    return stats