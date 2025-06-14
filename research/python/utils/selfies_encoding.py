import typing as t            # typing 모듈 : 파이썬의 타입 힌팅(type hinting) 기능을 제공
from collections import deque # 데크(deque) : 양방향 큐(queue) 자료구조를 구현하는 클래스

import numpy as np            # 수치 연산을 위한 라이브러리
import pandas as pd           # 데이터 분석을 위한 라이브러리

# 이미지 처리를 위한 라이브러리 → 내부적으로는 Pillow 가 로드, Pillow 는 사실 "PIL" API 를 그대로 계승한 후속 패키지
from PIL import Image 

import selfies as sf # SELFIES 인코딩 라이브러리
from rdkit.Chem import AllChem as Chem # 화학 구조 처리를 위한 라이브러리
from rdkit.Chem import Draw            # 화학 구조 시각화를 위한 라이브러리

from .mol_methods import * # (사용자 정의) 화학 구조 처리를 위한 메서드들 

import torch
# from orquestra.qml.api import Tensor, convert_to_numpy # 양자 기계 학습을 위한 라이브러리

import time
import multiprocessing as mp
import os
import sys

# --- Optional GPU Imports ---
try:
    import cupy
    # Check if a CUDA-enabled GPU is actually available
    if torch.cuda.is_available():
        GPU_AVAILABLE = True
        print("✅ CUDA GPU and CuPy/CuDF detected. GPU backend is available.")
    else:
        GPU_AVAILABLE = False
        print("⚠️ CuPy/CuDF is installed, but no CUDA-enabled GPU was found. GPU backend is disabled.")
except ImportError:
    GPU_AVAILABLE = False
    print("ℹ️ CuPy/CuDF not found. GPU backend is disabled.")

# --- Helper functions for parallel processing ---

def _process_smiles_chunk(chunk_data):
    """Processes a chunk of SMILES strings to convert them to SELFIES."""
    smiles_list, chunk_id = chunk_data
    results = {'chunk_id': chunk_id, 'valid_smiles': [], 'train_samples': [], 'invalid_rdkit': [], 'invalid_encoding': []}
    for smi in smiles_list:
        if "." in smi:
            smi = max(smi.split("."), key=len)
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            results['invalid_rdkit'].append(smi)
            continue
        try:
            encoded_smiles = sf.encoder(smi)
            results['valid_smiles'].append(smi)
            results['train_samples'].append(encoded_smiles)
        except sf.EncoderError:
            results['invalid_encoding'].append(smi)
    return results

def _process_encoding_chunk(chunk_data):
    """Converts a chunk of padded SELFIES strings to numerical encodings."""
    padded_selfies_chunk, char_to_index, chunk_id = chunk_data
    encoded_samples = [sf.selfies_to_encoding(sel, char_to_index, enc_type="label") for sel in padded_selfies_chunk]
    return chunk_id, encoded_samples

# --- Main Encoder Class ---

class SelfiesEncoder:
    """
    A comprehensive class to encode SMILES strings into SELFIES and then into
    numerical tensors, supporting multiple backends for performance optimization.
    """
    def __init__(
        self,
        filepath: str,
        backend: str = 'auto',
        n_cores: int = -1,
        chunk_size: int = 10000,
        max_length: t.Optional[int] = None,
        start_char: str = "[^]",
        pad_char: str = "[nop]",
    ):
        self.filepath = filepath
        
        # --- Core count setup ---
        if n_cores == -1:
            self.n_cores = mp.cpu_count()
            print(f"🖥️  Using all available {self.n_cores} cores for SELFIES encoding.")
        elif n_cores is None: # Fallback for safety
            self.n_cores = min(mp.cpu_count(), 8)
            print(f"🖥️  `n_cores` is None, defaulting to {self.n_cores} cores for SELFIES encoding.")
        else:
            self.n_cores = max(1, n_cores) # Ensure at least 1 core
            print(f"🖥️  Using {self.n_cores} specified cores for SELFIES encoding.")

        self.chunk_size = chunk_size
        self._max_length_user = max_length
        self._start_char = start_char
        self._pad_char = pad_char

        # --- Backend Selection ---
        if backend == 'auto':
            self.backend = 'gpu' if GPU_AVAILABLE else 'parallel'
        else:
            if backend == 'gpu' and not GPU_AVAILABLE:
                print(f"⚠️ GPU backend requested but not available. Falling back to 'parallel'.")
                self.backend = 'parallel'
            else:
                self.backend = backend
        
        print(f"🚀 SelfiesEncoder initialized with '{self.backend}' backend.")
        
        # --- Run Full Encoding Pipeline ---
        self._run_pipeline()

    def _run_pipeline(self):
        """Executes the complete encoding pipeline from file to final tensor."""
        start_time = time.time()
        
        # 1. Load data
        print(f"📊 Reading CSV file: {self.filepath}")
        df = pd.read_csv(self.filepath)
        smiles_list = df.smiles.tolist()
        print(f"   ...Found {len(smiles_list):,} total SMILES strings.")
        
        # 2. Process SMILES to SELFIES (CPU or Parallel)
        self.train_samples, self.valid_smiles, self.invalid_smiles_rdkit, self.invalid_smiles_encoding = self._smiles_to_selfies(smiles_list)
        
        # 3. Create vocabulary from valid SELFIES
        self._create_vocabulary()
        
        # 4. Determine max length and pad SELFIES strings
        self._setup_padding()
        
        # 5. Convert padded SELFIES to numerical encodings (CPU or Parallel)
        encoded_np_array = self._selfies_to_numerical()
        
        # 6. Convert final numpy array to a torch.Tensor (using GPU if available)
        self._encoded_samples_tensor = self._to_torch_tensor(encoded_np_array)
        
        total_time = time.time() - start_time
        print(f"\n🎉 SELFIES encoding pipeline finished in {total_time:.2f} seconds.")
        print(f"   Final tensor shape: {self.encoded_samples.shape}")

    def _smiles_to_selfies(self, smiles_list):
        """Handles the conversion from a list of SMILES to a list of SELFIES."""
        print(f"🔄 Converting {len(smiles_list):,} SMILES to SELFIES...")
        # This part is always CPU-bound, so we use parallel processing if possible
        if self.backend in ['parallel', 'gpu']: # GPU backend also benefits from parallel CPU pre-processing
            return self._smiles_to_selfies_parallel(smiles_list)
        else: # 'cpu' backend
            return self._smiles_to_selfies_cpu(smiles_list)

    def _smiles_to_selfies_cpu(self, smiles_list):
        """Processes SMILES to SELFIES sequentially on the CPU."""
        train_samples, valid_smiles, invalid_rdkit, invalid_encoding = [], [], [], []
        for smi in smiles_list:
            if "." in smi:
                smi = max(smi.split("."), key=len)
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                invalid_rdkit.append(smi)
                continue
            try:
                encoded_smiles = sf.encoder(smi)
                if encoded_smiles:
                    valid_smiles.append(smi)
                    train_samples.append(encoded_smiles)
            except sf.EncoderError:
                invalid_encoding.append(smi)
        
        print(f"   ...Finished. Found {len(valid_smiles):,} valid SELFIES.")
        return train_samples, valid_smiles, invalid_rdkit, invalid_encoding

    def _smiles_to_selfies_parallel(self, smiles_list):
        """Uses multiprocessing to convert SMILES to SELFIES in parallel."""
        chunks = [(smiles_list[i:i + self.chunk_size], i // self.chunk_size) for i in range(0, len(smiles_list), self.chunk_size)]
        print(f"   ...Using {self.n_cores} cores to process {len(chunks)} chunks.")
        
        with mp.Pool(self.n_cores) as pool:
            results = pool.map(_process_smiles_chunk, chunks)
        
        # Aggregate results
        train_samples, valid_smiles, invalid_rdkit, invalid_encoding = [], [], [], []
        for result in sorted(results, key=lambda x: x['chunk_id']):
            train_samples.extend(result['train_samples'])
            valid_smiles.extend(result['valid_smiles'])
            invalid_rdkit.extend(result['invalid_rdkit'])
            invalid_encoding.extend(result['invalid_encoding'])
            
        print(f"   ...Finished. Found {len(valid_smiles):,} valid SELFIES.")
        return train_samples, valid_smiles, invalid_rdkit, invalid_encoding

    def _create_vocabulary(self):
        """Creates the character-to-index mapping from the training samples."""
        print("📚 Building vocabulary...")
        alphabet_set = sf.get_alphabet_from_selfies(self.train_samples)
        alphabet_set.add(self._pad_char)
        alphabet_set.add(self._start_char)
        self.alphabet = sorted(list(alphabet_set))
        self.char_to_index = {c: i for i, c in enumerate(self.alphabet)}
        self.index_to_char = {i: c for c, i in self.char_to_index.items()}
        self.vocab_size = len(self.alphabet)
        print(f"   ...Vocabulary size: {self.vocab_size}")

    def _setup_padding(self):
        """Calculates max length and creates a list of padded SELFIES strings."""
        print("📏 Applying padding...")
        if self._max_length_user is None:
            # Calculate max length dynamically if not provided
            max_len_selfies = 0
            if self.train_samples:
                max_len_selfies = max(sf.len_selfies(s) for s in self.train_samples)
            self._max_length = max_len_selfies
        else:
            self._max_length = self._max_length_user

        # Pad all selfies
        self.padded_selfies = [s + self._pad_char * (self._max_length - sf.len_selfies(s)) for s in self.train_samples]
        print(f"   ...All sequences padded to max length: {self.max_length}")

    def _selfies_to_numerical(self):
        """Converts padded SELFIES strings to a numpy array of numerical indices."""
        print("🔢 Converting SELFIES to numerical format...")
        if self.backend in ['parallel', 'gpu']:
            chunks = [(self.padded_selfies[i:i + self.chunk_size], self.char_to_index, i // self.chunk_size) for i in range(0, len(self.padded_selfies), self.chunk_size)]
            with mp.Pool(self.n_cores) as pool:
                results = pool.map(_process_encoding_chunk, chunks)
            
            # Aggregate results
            encoded_samples = []
            for _, chunk_encoded in sorted(results, key=lambda x: x[0]):
                encoded_samples.extend(chunk_encoded)
            return np.array(encoded_samples, dtype=np.int64)
        else: # 'cpu' backend
            encoded_samples = [sf.selfies_to_encoding(s, self.char_to_index, "label") for s in self.padded_selfies]
            return np.array(encoded_samples, dtype=np.int64)

    def _to_torch_tensor(self, np_array):
        """Converts a numpy array to a torch.Tensor, using GPU if available."""
        print("⚡ Converting numpy array to torch.Tensor...")
        tensor = torch.tensor(np_array, dtype=torch.long) # Use long for indices
        if self.backend == 'gpu':
            print("   ...Moving tensor to GPU.")
            return tensor.cuda()
        return tensor

    # --- Public Properties and Methods ---

    @property
    def encoded_samples(self) -> torch.Tensor:
        """Returns the final encoded samples as a torch.Tensor."""
        return self._encoded_samples_tensor

    @property
    def max_length(self) -> int:
        return self._max_length
    
    @property
    def pad_char_index(self) -> int:
        return self.char_to_index[self._pad_char]
    
    @property
    def start_char_index(self) -> int:
        return self.char_to_index[self._start_char]

    def decode(self, encoded_tensor: torch.Tensor) -> t.List[str]:
        """Decodes a tensor of numerical indices back to SMILES strings."""
        if not isinstance(encoded_tensor, torch.Tensor):
            raise TypeError("Input must be a torch.Tensor.")

        # Move tensor to CPU and convert to list of lists
        if encoded_tensor.is_cuda:
            encoded_tensor = encoded_tensor.cpu()
        
        encoded_indices_list = encoded_tensor.numpy().tolist()

        decoded_smiles_list = []
        for encoded_indices in encoded_indices_list:
            try:
                # Convert indices to SELFIES string
                selfies_string = sf.encoding_to_selfies(
                    encoded_indices, self.index_to_char, enc_type="label"
                )
                
                # Remove special characters
                if self._start_char in selfies_string:
                    selfies_string = selfies_string.replace(self._start_char, "")
                if self._pad_char in selfies_string:
                    selfies_string = selfies_string.split(self._pad_char, 1)[0]
                
                # Decode to SMILES
                decoded_smile = sf.decoder(selfies_string)
                decoded_smiles_list.append(decoded_smile)
            except Exception:
                # If any error occurs during decoding, append an empty string
                decoded_smiles_list.append("")
                
        return decoded_smiles_list

#===============================================================================================================


def truncate_smiles(
    smiles: t.Iterable[str], padding_char: str = "_", min_length: int = 1
) -> t.List[str]:
    """
    SMILES 문자열 리스트에서 패딩 문자가 등장하기 전까지의 부분만 잘라낸 후,
    최소 길이(min_length)보다 짧은 SMILES는 제거하는 함수입니다.

    📌 사용 예시:
        >>> smiles = ['cc2_N', 'cc2__', 'cc2']
        >>> truncate_smiles(smiles)
        ['cc2', 'cc2', 'cc2']

    🧠 주 용도:
        - LSTM 등 시퀀스 모델에서 출력된 SMILES 중 '_' 같은 패딩 문자가 포함된 경우
        - 패딩 이후 내용을 제거하여 유효한 부분만 추출
        - 너무 짧은 결과는 제거하여 품질 향상

    Args:
        smiles (Iterable[str]): 처리할 SMILES 문자열 리스트 (str iterable).
        padding_char (str, optional): 패딩 문자를 나타내는 문자 (기본값: "_").
        min_length (int, optional): 최소 SMILES 길이 (기본값: 1). 이보다 짧으면 제외.

    Returns:
        List[str]: 잘린 후 유효한 SMILES 문자열 리스트
    """

    # 결과를 빠르게 누적하기 위해 리스트 초기화
    truncated_smiles = list()

    for smile in smiles:
        # padding_char가 존재한다면 해당 인덱스까지 자름
        try:
            truncated_smile = smile[: smile.index(padding_char)]
        except ValueError:
            # 패딩 문자가 없는 경우는 전체 문자열 그대로 사용
            truncated_smile = smile

        # 최소 길이 조건을 만족하면 결과 리스트에 추가
        if len(truncated_smile) >= min_length:
            truncated_smiles.append(truncated_smile)

    # 최종 잘라낸 SMILES 리스트 반환
    return list(truncated_smiles)