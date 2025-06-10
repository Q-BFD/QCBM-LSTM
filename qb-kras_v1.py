import os
import sys
import time

# Change working directory to the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir = '/Users/jina/Library/CloudStorage/Dropbox/Yonsei-2025/Study/KRAS'
os.chdir(current_dir)

import json
from pathlib import Path

import pandas as pd
import numpy as np

# For data validation and model definition
from pydantic import BaseModel, Field
# For type hints and named tuples
from typing import Literal, NamedTuple

# Argument parser for command line
from argparse import ArgumentParser
# Partial function application
from functools import partial

from inspect import signature

import torch
import torch.optim as optim

# Optimization library
from scipy.optimize import minimize

import wandb  # Experiment tracking library
from tqdm import tqdm # Progress bar
import matplotlib.pyplot as plt
from rdkit.Chem import Draw
from rdkit import Chem, RDLogger

# Import custom modules
from utils.selfies_encoding import SelfiesEncoding, truncate_smiles # SELFIES Encoding, truncate_smiles
from settings.training_para import TrainingArgs    # Training parameter settings
from utils.filters import get_diversity # Diversity calculation function
from utils.filters import legacy_apply_filters, combine_filter, reward_fc # Filter functions
from utils.dataloader import new_data_loader, train_data_loader, save_obj, load_obj # Data loader
from utils.compound_stat import compute_compound_stats, canonicalize # Compound statistics calculation

from model.lstm.noisy_lstm_v3 import NoisyLSTMv3 # LSTM model
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler # Quantum computing
from model.prior.prior_cls import RandomChoiceSampler # Prior sampling
from model.prior.prior_qcbm import SingleBasisQCBM, QCBMAnsatz, ScipyOptimizer # QCBM related

print(f"\n========== Start script ==========")
### Command line arguments ###------------------------------------------------

# python qb-kras_v1.py --config_file ./settings/benchmark_models_settings_qcbm.json
argparser = ArgumentParser()
argparser.add_argument(
    "--config_file",
    type=str,
    default="./settings/benchmark_models_settings_qcbm.json",
    help="Path to config file for training."
)

namespace = argparser.parse_args()
# Read config file and create training parameter object
args = TrainingArgs.from_file(namespace.config_file)

### Dataset ###------------------------------------------------

dataset_by_id = {
    0: "data/KRAS_G12D/KRAS_G12D_inhibitors_update2023.csv",
    1: "data/KRAS_G12D/initial_dataset.csv",
    2: "data/KRAS_G12D/initial_data_with_chemistry42_syba_merged_v2.csv",
    3: "data/KRAS_G12D/initial_data_set_with_100k_hits.csv",
    4: "data/KRAS_G12D/1Mstoned_vsc_initial_dataset_insilico_chemistry42_filtered.csv",
    5: "/home/mghazi/workspace/Tartarus/datasets/docking.csv"
}

data_id = int(args.data_set_id)

# Set the path to the selected dataset
path_to_dataset = dataset_by_id.get(data_id, None)
if path_to_dataset is None:
    raise ValueError(f"Invalid data set id: {data_id}")

# Set the path to the pickle data
path_to_pickle_data = dataset_by_id[data_id].split(".")[0]

# If pickle file does not exist, create it
if os.path.isfile(f"{path_to_pickle_data}.pkl") == False:
  
    selfies = SelfiesEncoding(path_to_dataset, dataset_identifier="KRAS_Dataset_1M") # SELFIES encoding
    encoded_samples_th = torch.tensor(selfies.encoded_samples) # torch.Size([1010272, 777])
    # Convert tensor to float type
    data = encoded_samples_th.float()
    
    # Save data and selfies object as a pickle file
    save_obj([data,selfies],f"{path_to_pickle_data}.pkl")

# Load pickle file
object_loaded = load_obj(f"{path_to_pickle_data}.pkl")    
selfies = object_loaded[1] # Selfies Encoding class
train_compounds = selfies.valid_smiles # 유효한 SMILES 문자열 리스트
data = object_loaded[0]
print(f"\n========== Object loaded ==========")


dataloader = (
    new_data_loader(
        data=data, 
        batch_size=args.batch_size,
        drop_last=True,
        shuffle=True,
        seed=123,
        fraction=args.data_set_fraction
    )
)

# Disable RDKit log
RDLogger.DisableLog("rdApp.*")

### Training parameters ###------------------------------------------------


prior_sample_size = args.prior_size                        # prior 모델에서 샘플링할 수
lstm_n_batch_size = args.batch_size                        # LSTM 학습 배치 크기
data_set = args.data_set_id                                # 사용할 데이터셋 ID
prior_model = args.prior_model                             # prior 모델 종류 (QCBM, RBM 등)
n_qcbm_layers = args.n_qcbm_layers                         # QCBM 레이어 수
hidden_dim = args.hidden_dim                               # LSTM hidden 크기
embedding_dim = args.embedding_dim                         # LSTM 임베딩 차원
n_lstm_layers = args.n_lstm_layers                         # LSTM 레이어 수
lstm_n_epochs = args.lstm_n_epochs                         # LSTM 학습 에폭 횟수
prior_n_epochs = args.prior_n_epochs                       # prior 모델 학습 에폭
n_test_samples = args.n_test_samples                       # 테스트용 샘플 수
n_compound_generation = args.n_compound_generation         # 생성할 총 분자 수
n_generation_steps = args.n_generation_steps               # 생성 반복 횟수
dataset_frac = args.dataset_frac                           # 사용할 데이터셋 비율
N_SAMPLES_CHEMISTRY42 = args.n_samples_chemistry42         # Chemistry42 평가 샘플 수
N_TEST_SAMPLES_CHEMISTRY42 = args.n_test_samples_chemistry42  # Chemistry42 테스트 샘플 수
optimizer_name = args.optimizer_name                       # 사용할 최적화 알고리즘 이름
do_greedy_sampling = args.do_greedy_sampling               # greedy 샘플링 여부
temprature = args.temprature                               # softmax 샘플링 온도
experiment_root = args.experiment_root                     # 결과 저장 경로
n_benchmark_samples = args.n_benchmark_samples             # 벤치마크용 생성 샘플 수
device = args.device
max_mol_weight = args.max_mol_weight
prior_maxiter = args.prior_maxiter
prior_tol = args.prior_tol
plot_root = args.plot_root

### Define functions ###------------------------------------------------

validity_fn = partial(
    combine_filter,
    max_mol_weight=max_mol_weight,
    filter_fc=legacy_apply_filters,
    disable_tqdm= True
)

rew_fc = partial(
                reward_fc, 
                max_mol_weight=max_mol_weight, 
                filter_fc=legacy_apply_filters
                )

diversity_fn = get_diversity
decoder_fn = selfies.decode_fn 
truncate_fn = truncate_smiles

print(f"\n========== Define functions ==========")
### Prior model ###------------------------------------------------

if prior_model == "classical":
    prior = RandomChoiceSampler(prior_sample_size, choices=[0.0, 1.0])
elif prior_model == "QCBM":
    # QiskitRuntimeService.save_account(channel="ibm_quantum", token='Your-Token-Number', overwrite=True, set_as_default=True)
    # service = QiskitRuntimeService(channel="ibm_quantum")
    # print(service.backends()) 
    # backend = service.backend("ibm_yonsei")
    depth = args.n_qcbm_layers
    nshot = args.n_qcbm_shots
    ansatz = QCBMAnsatz(prior_sample_size, depth)
    # sampler = Sampler(backend=backend)
    options = {
        'maxiter': prior_maxiter,   # Maximum number of iterations
        'tol': prior_tol,      # Tolerance for termination
        'disp': False      # Display convergence messages
    }
    optimizer = ScipyOptimizer(method='COBYLA', options=options)
    prior = SingleBasisQCBM(ansatz, optimizer, nshot=nshot)

### LSTM model ###------------------------------------------------

model = NoisyLSTMv3(
    vocab_size=selfies.num_emd,
    seq_len=selfies.max_length,
    sos_token_index=selfies.start_char_index,
    prior_sample_dim=prior_sample_size,
    padding_token_index=selfies.pad_char_index,
    hidden_dim=hidden_dim,
    embedding_dim=embedding_dim,
    n_layers=n_lstm_layers,
    do_greedy_sampling=do_greedy_sampling,
    sampling_temperature=temprature
)

optimizer = optim.Adam(model.parameters(), lr=0.001)


generated_compunds = {}
all_compound = []


### Run ------------------------------------------------
for epoch in range(1, lstm_n_epochs + 1):
    print(f"\n========== Epoch {epoch} / {lstm_n_epochs} ==========")
    epoch_start_time = time.perf_counter()
    print("[Step] Training LSTM model...")
    with tqdm(total=len(dataloader), leave=True, dynamic_ncols=True) as pbar:        
        for batch_idx, batch in enumerate(dataloader):
            inputs = batch
            batch_size = inputs.size(0)
            seq_len = inputs.size(1)
            prior_samples, unique_samples, probabilities = prior.generate(batch_size, sampler = None, backend = None)
            batch_result = model.train_on_batch(inputs, prior_samples)
            pbar.set_postfix(dict(Loss=batch_result["loss"]))
            pbar.update()
    model.eval()
    print("[Step] Generating compounds with prior and LSTM...")
    prior_samples_current, unique_samples, probabilities = prior.generate(n_test_samples, sampler = None, backend = None)
    encoded_compounds = model.generate(prior_samples_current)
    print("[Step] Calculating compound statistics...")
    validity_fn = partial(
        combine_filter,
        max_mol_weight=max_mol_weight,
        filter_fc=legacy_apply_filters,
        disable_tqdm= True
    )
    compound_stats = compute_compound_stats(
        encoded_compounds,
        decoder_fn,
        diversity_fn,
        validity_fn,
        train_compounds
    )
    datanew = rew_fc(list(compound_stats.all_compounds)).cpu()
    soft = torch.nn.Softmax(dim=0)
    probs = soft(datanew)
    print("[Step] Training prior model (QCBM or classical)...")
    prior_x = prior_samples_current
    prior_y = probs
    result = prior.train_on_batch(prior_x, prior_y, sampler = None, backend = None, n_epochs = prior_n_epochs)
    print("[Step] Generating new compounds after prior training...")
    prior_samples_current, unique_samples, probabilities = prior.generate(n_test_samples, sampler = None, backend = None)
    encoded_compounds = model.generate(prior_samples_current)
    print("[Step] Calculating statistics for new compounds to evaluate prior model...")
    validity_fn = partial(
        combine_filter,
        max_mol_weight=max_mol_weight,
        filter_fc=legacy_apply_filters,
        disable_tqdm= False
    )
    compound_stats = compute_compound_stats(
        encoded_compounds,
        decoder_fn,
        diversity_fn,
        validity_fn,
        train_compounds,
    )
    all_compound.append(compound_stats)
    pbar.set_postfix(
        dict(
            Loss=batch_result["loss"],
            NumUniqueGenerated=compound_stats.n_unique,
            NumValidGenerated=compound_stats.n_valid,
            NumUnseenGenerated=compound_stats.n_unseen,
            unique_fraction=compound_stats.unique_fraction,
            valid_fraction=compound_stats.valid_fraction,
            diversity_fraction=compound_stats.diversity_fraction,
        )
    )  
    generated_compunds[str(epoch)] = dict(
        samples={
            "all": list(compound_stats.all_compounds),
            "unique": list(compound_stats.unique_compounds),
            "valid": list(compound_stats.valid_compounds),
            "unseen": list(compound_stats.unseen_compounds),
            "prior": list(prior_samples_current.tolist()),
            "unique_fraction": compound_stats.unique_fraction,
            "valid_fraction": compound_stats.valid_fraction,
            "diversity_fraction": compound_stats.diversity_fraction,
        }
    )
    model.train()
    epoch_end_time = time.perf_counter()
    print(f"[Epoch {epoch}] Elapsed time: {epoch_end_time - epoch_start_time:.3f} seconds")
    rng = np.random.default_rng()
    log_t0_wandb = {
            "NumUniqueGenerated":compound_stats.n_unique,
            "NumValidGenerated":compound_stats.n_valid,
            "NumUnseenGenerated":compound_stats.n_unseen,
            "unique_fraction":compound_stats.unique_fraction,
            "valid_fraction":compound_stats.valid_fraction,
            "diversity_fraction":compound_stats.diversity_fraction,
        }
    # Print meaningful SMILES before drawing
    # print(f"[Info] Number of unique compounds: {compound_stats.n_unique}")
    # print(f"[Info] Number of valid compounds: {compound_stats.n_valid}")
    # print(f"[Info] Number of unseen compounds: {compound_stats.n_unseen}")
    # if len(compound_stats.unseen_compounds) > 0:
    #     print(f"[Info] Example unseen SMILES: {list(compound_stats.unseen_compounds)[:5]}")
    # if len(compound_stats.valid_compounds) > 0:
    #     print(f"[Info] Example valid SMILES: {list(compound_stats.valid_compounds)[:5]}")
    try:
        if len(compound_stats.valid_compounds) > 20:
            selected_smiles = rng.choice(
                list(compound_stats.valid_compounds), 20, replace=False
            )
        else:
            selected_smiles = list(compound_stats.valid_compounds)
        mols = [Chem.MolFromSmiles(smile_) for smile_ in selected_smiles]
        img = Draw.MolsToGridImage(mols, molsPerRow=20, returnPNG=False)
        log_t0_wandb.update({"dicovery": wandb.Image(img)})
        img.save(f"{plot_root}/epoch_{epoch}.png")
        print(f"[Info] Example valid SMILES: {selected_smiles}")
    except Exception as e:
        print(f"Unable to draw molecules: {e}")
    try:
        data_ = {
            "prior_samples": prior_samples_current,
            "model_samples": encoded_compounds,
            "selfies": selfies,
            "prior": prior,
            "model": model,
            "prior_x":prior_x,
            "prior_y":prior_y,
            "compound_stats":compound_stats
        }
        file_name = f"mode_prior_{epoch}"
        save_obj(data_, f"{experiment_root}/{file_name}.pkl")
    except Exception as e:
        print(f"Unable to save model and prior in epoch {epoch}: {e}")

# After all epochs, save summary CSV
print("[Step] Saving summary CSV of all epochs...")
summary_rows = []
for i, stats in enumerate(all_compound, 1):
    summary_rows.append({
        "epoch": i,
        "n_unique": stats.n_unique,
        "n_valid": stats.n_valid,
        "n_unseen": stats.n_unseen,
        "unique_fraction": stats.unique_fraction,
        "valid_fraction": stats.valid_fraction,
        "diversity_fraction": stats.diversity_fraction,
        "valid_smiles": ";".join(list(stats.valid_compounds))
    })
summary_df = pd.DataFrame(summary_rows)
csv_path = f"{experiment_root}/compound_stats_summary.csv"
summary_df.to_csv(csv_path, index=False)


# 각 epoch별로 생성된 모든 SMILES를 CSV로 저장
print("[Step] Saving all generated samples per epoch to CSV...")
for epoch, epoch_data in generated_compunds.items():
    all_samples = epoch_data['samples']['all']
    df = pd.DataFrame({'smiles': all_samples})
    csv_path_epoch = f"{experiment_root}/generated_samples_epoch_{epoch}.csv"
    df.to_csv(csv_path_epoch, index=False)
    