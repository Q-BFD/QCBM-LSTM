"""
Parallel version of SELFIES encoding for faster dataset creation.
"""
import typing as t
import time
import multiprocessing as mp
from functools import partial
from collections import deque

import numpy as np
import pandas as pd
import torch

import selfies as sf
from rdkit.Chem import AllChem as Chem

from .mol_methods import *


def process_smiles_chunk(chunk_data):
    """
    SMILES 청크를 병렬로 처리하는 함수
    
    Args:
        chunk_data (tuple): (smiles_list, chunk_id)
        
    Returns:
        dict: 처리 결과
    """
    smiles_list, chunk_id = chunk_data
    
    results = {
        'chunk_id': chunk_id,
        'valid_smiles': [],
        'train_samples': [],
        'invalid_rdkit': [],
        'invalid_encoding': []
    }
    
    for smi in smiles_list:
        # 멀티프래그먼트 처리
        if "." in smi:
            smi = max(smi.split("."), key=len)
        
        # RDKit 유효성 검사
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            results['invalid_rdkit'].append(smi)
            continue
            
        # SELFIES 인코딩
        try:
            encoded_smiles = sf.encoder(smi)
            results['valid_smiles'].append(smi)
            results['train_samples'].append(encoded_smiles)
        except sf.EncoderError:
            results['invalid_encoding'].append(smi)
            continue
    
    return results


def process_encoding_chunk(chunk_data):
    """
    SELFIES 숫자 인코딩을 병렬로 처리하는 함수
    """
    padded_selfies_chunk, char_to_index, chunk_id = chunk_data
    
    encoded_samples = [
        sf.selfies_to_encoding(sel, char_to_index, enc_type="label")
        for sel in padded_selfies_chunk
    ]
    
    return chunk_id, encoded_samples


class ParallelSelfiesEncoding:
    """
    병렬 처리를 지원하는 SELFIES 인코딩 클래스
    """
    
    def __init__(
        self,
        filepath: str,
        dataset_identifier: str,
        start_char: str = "[^]",
        pad_char: str = "[nop]",
        max_length: t.Optional[int] = None,
        n_cores: int = None,
        chunk_size: int = 10000
    ):
        print(f"🚀 병렬 SELFIES 인코딩 시작...")
        
        self.dataset_identifier = dataset_identifier
        self._filepath = filepath
        self.n_cores = n_cores if n_cores else min(mp.cpu_count(), 8)
        self.chunk_size = chunk_size
        
        # 초기화
        self.train_samples = []
        self.invalid_smiles_rdkit = []
        self.invalid_smiles_encoding = []
        self.valid_smiles = []
        
        start_time = time.time()
        
        # 1. CSV 읽기
        print(f"📊 CSV 파일 읽는 중...")
        self.df = pd.read_csv(self._filepath)
        smiles_list = self.df.smiles.tolist()
        print(f"   총 {len(smiles_list):,}개 SMILES 로드됨")
        
        # 2. 병렬 SMILES 처리
        print(f"🔄 {self.n_cores}개 코어로 SMILES 병렬 처리 중...")
        self._parallel_process_smiles(smiles_list)
        
        processing_time = time.time() - start_time
        print(f"✅ SMILES 처리 완료: {processing_time:.1f}초")
        print(f"   유효 SMILES: {len(self.valid_smiles):,}개")
        print(f"   무효 (RDKit): {len(self.invalid_smiles_rdkit):,}개")
        print(f"   무효 (SELFIES): {len(self.invalid_smiles_encoding):,}개")
        
        # 3. 알파벳 생성 및 매핑
        print(f"📚 어휘 사전 생성 중...")
        self._create_vocabulary(start_char, pad_char)
        
        # 4. 최대 길이 설정
        self.data_length = max(map(len, self.train_samples))
        fallback_max_length = int(len(max(self.train_samples, key=len)) * 1.5)
        self._max_length = max_length if max_length is not None else fallback_max_length
        print(f"   최대 길이: {self.max_length}")
        
        # 5. 패딩 및 숫자 인코딩
        print(f"🔢 패딩 및 숫자 인코딩 중...")
        self._parallel_create_encoded_samples()
        
        total_time = time.time() - start_time
        print(f"🎉 전체 처리 완료: {total_time:.1f}초")
        print(f"   데이터 shape: {self.encoded_samples.shape}")
        
    def _parallel_process_smiles(self, smiles_list):
        """SMILES 리스트를 병렬로 처리"""
        # 청크로 분할
        chunks = []
        for i in range(0, len(smiles_list), self.chunk_size):
            chunk = smiles_list[i:i + self.chunk_size]
            chunks.append((chunk, i // self.chunk_size))
        
        print(f"   {len(chunks)}개 청크로 분할")
        
        # 병렬 처리
        with mp.Pool(self.n_cores) as pool:
            results = pool.map(process_smiles_chunk, chunks)
        
        # 결과 병합
        for result in results:
            self.valid_smiles.extend(result['valid_smiles'])
            self.train_samples.extend(result['train_samples'])
            self.invalid_smiles_rdkit.extend(result['invalid_rdkit'])
            self.invalid_smiles_encoding.extend(result['invalid_encoding'])
    
    def _create_vocabulary(self, start_char, pad_char):
        """어휘 사전 생성"""
        alphabet_set = sf.get_alphabet_from_selfies(self.train_samples)
        alphabet_set.add(pad_char)
        alphabet_set.add(start_char)
        self.alphabet = list(alphabet_set)
        
        self.char_to_index = dict((c, i) for i, c in enumerate(self.alphabet))
        self.index_to_char = {v: k for k, v in self.char_to_index.items()}
        
        self.num_emd = len(self.char_to_index)
        self._pad_char = pad_char
        self._start_char = start_char
        
        print(f"   어휘 크기: {self.num_emd}개")
    
    def _parallel_create_encoded_samples(self):
        """패딩 및 숫자 인코딩을 병렬로 처리"""
        # 패딩 적용
        padded_selfies = deque()
        for selfie in self.train_samples:
            n_padding_tokens = self.max_length - sf.len_selfies(selfie)
            padding = self._pad_char * n_padding_tokens
            padded_selfie = selfie + padding
            padded_selfies.append(padded_selfie)
        
        padded_selfies = list(padded_selfies)
        
        # 병렬 숫자 인코딩
        chunks = []
        for i in range(0, len(padded_selfies), self.chunk_size):
            chunk = padded_selfies[i:i + self.chunk_size]
            chunks.append((chunk, self.char_to_index, i // self.chunk_size))
        
        with mp.Pool(self.n_cores) as pool:
            results = pool.map(process_encoding_chunk, chunks)
        
        # 결과 정렬 및 병합
        results.sort(key=lambda x: x[0])  # chunk_id로 정렬
        encoded_samples = []
        for _, chunk_encoded in results:
            encoded_samples.extend(chunk_encoded)
        
        self._encoded_samples = np.asarray(encoded_samples)
    
    @property
    def encoded_samples(self) -> np.ndarray:
        return self._encoded_samples
    
    @property
    def max_length(self) -> int:
        return self._max_length
    
    @property
    def pad_char(self) -> str:
        return self._pad_char
    
    @property
    def start_char(self) -> str:
        return self._start_char
    
    @property
    def pad_char_index(self) -> int:
        return self.char_to_index[self._pad_char]
    
    @property
    def start_char_index(self) -> int:
        return self.char_to_index[self._start_char]
    
    def decode_fn(self, encoded_selfies: t.Union[np.ndarray, torch.Tensor]) -> t.List[str]:
        """디코딩 함수 (기존과 동일)"""
        if isinstance(encoded_selfies, torch.Tensor):
            numpy_array = encoded_selfies.detach().cpu().numpy()
            encoded_sf_list = numpy_array.tolist()
        elif isinstance(encoded_selfies, np.ndarray):
            encoded_sf_list = encoded_selfies.tolist()
        else:
            raise TypeError("Input must be a torch.Tensor or np.ndarray")
        
        decoded_sf_list = list()
        for encoded_sf in encoded_sf_list:
            selfies = sf.encoding_to_selfies(
                encoded_sf, self.index_to_char, enc_type="label"
            )
            if self._start_char in selfies:
                selfies = selfies.replace(self._start_char, "")
            decoded_smile = sf.decoder(selfies)
            decoded_sf_list.append(decoded_smile)
        return decoded_sf_list


# 편의 함수
def create_parallel_dataset(filepath: str, n_cores: int = None, chunk_size: int = 10000):
    """
    병렬 데이터셋 생성 편의 함수
    
    Args:
        filepath: CSV 파일 경로
        n_cores: 사용할 코어 수 (None이면 자동)
        chunk_size: 청크 크기
        
    Returns:
        tuple: (data_tensor, selfies_encoder)
    """
    print(f"🔧 병렬 데이터셋 생성 시작...")
    
    selfies = ParallelSelfiesEncoding(
        filepath, 
        dataset_identifier="KRAS_Dataset_1M",
        n_cores=n_cores,
        chunk_size=chunk_size
    )
    
    encoded_samples_th = torch.tensor(selfies.encoded_samples)
    data = encoded_samples_th.float()
    
    print(f"✅ 데이터셋 생성 완료!")
    print(f"   Shape: {data.shape}")
    print(f"   Memory: {data.element_size() * data.nelement() / 1024 / 1024 / 1024:.2f} GB")
    
    return data, selfies 