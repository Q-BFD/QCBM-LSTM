import typing as t            # typing 모듈 : 파이썬의 타입 힌팅(type hinting) 기능을 제공
from collections import deque # 데크(deque) : 양방향 큐(queue) 자료구조를 구현하는 클래스

import numpy as np            # 수치 연산을 위한 라이브러리
import pandas as pd           # 데이터 분석을 위한 라이브러리

# 이미지 처리를 위한 라이브러리 → 내부적으로는 Pillow 가 로드, Pillow 는 사실 “PIL” API 를 그대로 계승한 후속 패키지
from PIL import Image 

import selfies as sf # SELFIES 인코딩 라이브러리
from rdkit.Chem import AllChem as Chem # 화학 구조 처리를 위한 라이브러리
from rdkit.Chem import Draw            # 화학 구조 시각화를 위한 라이브러리

from .mol_methods import * # (사용자 정의) 화학 구조 처리를 위한 메서드들 

import torch
# from orquestra.qml.api import Tensor, convert_to_numpy # 양자 기계 학습을 위한 라이브러리




# SelfiesEncoding 클래스 정의 
class SelfiesEncoding:
    """
        SELFIES 인코딩 클래스 초기화.SMILES를 SELFIES로 변환하고 숫자 인코딩하여 모델 학습에 적합한 형태로 준비

        Args:
            filepath (str): SMILES를 포함한 CSV 파일 경로
            dataset_identifier (str): 데이터셋 이름 또는 식별자
            start_char (str): SELFIES 시퀀스 시작 문자
            pad_char (str): SELFIES 패딩 문자
            max_length (t.Optional[int], optional): 시퀀스 최대 길이 (기본값: 가장 긴 시퀀스 * 1.5)
                : an optional argument to specify the maximum length of sequences.
                  If not specified, the length of the 1.5 times the longest sequence in the provided file will be used.
    """
    def __init__(
        self,
        filepath: str,
        dataset_identifier: str,
        start_char: str = "[^]",
        pad_char: str = "[nop]",
        max_length: t.Optional[int] = None,
    ):
        self.dataset_identifier = dataset_identifier
        self._filepath = filepath
        self.df = pd.read_csv(self._filepath)

        # 샘플 리스트 초기화
        self.train_samples = []    # 유효한 SELFIES 시퀀스 저장
        self.invalid_smiles_rdkit = []   # 유효하지 않은 SMILES 저장 by rdkit 유효성검사
        self.invalid_smiles_encoding = [] # 유효하지 않은 SMILES 저장 by selfies encoding process
        self.valid_smiles = []
        """
        Error 1. SELFIES의 기본 제약조건인 최대 4개의 결합을 초과하는 문제 발생
            예시. CN1CCC(c2nc(OCC3CCCN3C)nc3c2C#[PH](=O)N(Cc2ccccc2)C3)C1

            수정 방법 : 제약 조건의 해제 또는 변경
            a. 제약 완전 해제 : sf.set_semantic_constraints({})
            b. 특정 원소만 제약 수정
                # [PH1]의 최대 결합 수를 6으로 늘려줌
                constraints["[PH1]"] = 6
                # 다시 설정
                sf.set_semantic_constraints(constraints)
            c. Valid한 set으로만 사용

        Error 2. kekulization failed
            예시. SMILES: NCCCCCOCC1c2n[c-]n[o+]c2CCN1c1ccccc1C(F)(F)F

            수정 방법 : 화학 구조 처리 옵션 변경
            a. 기본 설정 유지
            b. 특정 원소만 제약 수정
                # 특정 원소의 화학 구조 처리 옵션 변경
                Chem.Kekulize(mol, clearAromaticFlags=False)
                # 다시 설정
                Chem.Kekulize(mol, clearAromaticFlags=True)
            c. Valid한 set으로만 사용
        """
        for smi in self.df.smiles.tolist():
            # “.” 로 연결된 멀티프래그먼트 SMILES에서, 문자열 길이가 더 긴 조각(fragment)만 골라내는 로직
            # => “molA.molB” 식으로 두 분자가 연결된 SMILES 중에서, 길이가 더 긴(=아마도 무게가 크거나 주된) 분자만 골라내도록 하는 전처리 구문
            # 예시. “C1CCCCC1.C1CCCCC1” → “C1CCCCC1” 로 변환
            if "." in smi:
                smi = max(smi.split("."), key=len)
            

            # RDKit으로 유효성 검사 => 추가 by 진아 선생님
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                self.invalid_smiles_rdkit.append(smi)
                # print(f"[INVALID] SMILES (RDKit 실패): {com}")
                continue

            try:
                encoded_smiles = sf.encoder(smi)
                self.valid_smiles.append(smi)
            except sf.EncoderError as e:
                # encoder error 처리 - 예외가 난 SMILES는 error set 저장 및 로그 생성 후 계속 진행
                self.invalid_smiles_encoding.append(smi)
                # print(f"Error encoding {com}: {e}")
                continue

            # 인코딩된 SMILES가 None이 아닌 경우, train_samples 리스트에 추가
            if encoded_smiles is not None:
                self.train_samples.append(encoded_smiles)
        
        print(f"Converted {len(self.train_samples)} SMILES entries to SELFIES")
        # print(len(self.train_samples))
        
        # 알파벳 생성 : 모든 토큰을 중복 없이 모아서 집합(set)으로 만듦
        alphabet_set = sf.get_alphabet_from_selfies(self.train_samples)

        # 특수 토큰 추가 (패딩, 시작 토큰)
        """
        start_char("[^]")와 pad_char("[nop]") 
            - SELFIES 기반 시퀀스 모델링에서 특수 토큰(vocabulary special tokens) 으로 사용
            - 기본 SELFIES 알파벳에는 포함되지 않으므로, 모델이 이해할 수 있도록 직접 추가

        [nop] (Padding Token)
            - 용도: 모든 SELFIES 시퀀스를 동일한 길이로 맞춰 주기 위해, 짧은 시퀀스의 뒤에 채워 넣는 토큰
            - 필요성
                - LSTM이나 QCBM 같은 순차 모델은 입력 길이가 고정되어 있거나, 배치 단위로 묶을 때 같은 길이가 되어야 학습·추론이 편리
	            - "[nop]" 토큰을 만나면 “여기는 실제 분자 정보가 아님”을 알 수 있음

        [^] (Start-of-Sequence Token)
            - 용도: 시퀀스의 시작 위치를 명시해 주는 토큰
            - 필요성
                - 모델이 입력 시퀀스가 어디서부터 시작되는지, 혹은 “첫 토큰”을 구분해야 할 때 사용
	            - 디코더(샘플링) 단계에서 “처음에 뭐부터 생성할지”를 지시
        """
        alphabet_set.add(pad_char)
        alphabet_set.add(start_char)
        self.alphabet = list(alphabet_set)


        # mapping char -> index and mapping index -> char
        # 2개의 Dictionary 생성
        # enumerate() : 리스트의 인덱스와 값을 동시에 반환하는 함수

        # char -> index : Model 입력용 숫자 Seq로 변환
        # 예: ("[C]", 0), ("[=O]", 1), …
        self.char_to_index = dict(
            (c, i) for i, c in enumerate(self.alphabet) # (인덱스, 토큰) 쌍을 (토큰, 인덱스) 형태로 뒤집는 과정
            )

        # index -> char : 디코딩 시 사용
        # 예: (0, "[C]"), (1, "[=O]"), …
        self.index_to_char = {v: k for k, v in self.char_to_index.items()}

        # 모델에 넣기 전에 알아야 할 기본 정보들(어휘 크기, 특수 토큰, 최대 길이)”을 한 번에 초기화
        self.num_emd = len(self.char_to_index) # 딕셔너리에 담긴 토큰 개수(어휘 크기, vocabulary size)를 가져와 num_emd(임베딩 차원 수)로 저장
        self._pad_char = pad_char
        self._start_char = start_char
        self.data_length = max(map(len, self.train_samples)) # 가장 긴 시퀀스의 길이를 저장

        # 훈련 샘플 중 가장 긴 시퀀스 길이의 150%”를 대체 기본값(fallback_max_length)으로 설정
        fallback_max_length = int(len(max(self.train_samples, key=len)) * 1.5) 
        # max_length의 설정
        self._max_length = max_length if max_length is not None else fallback_max_length 

        # 디코딩 과정에서 추적할 문자열 리스트
        self.track_strings = []
        # self.encoded_samples_size = len(self.encoded_samples)

    # 인덱스에 해당하는 문자 반환
    def get_char_at(self, index: int) -> str:
        return self.index_to_char[index]

    # 인덱스에 해당하는 문자 리스트 반환
    def get_chars_at(self, indices: t.List[int]) -> t.List[str]:
        return [self.get_char_at(index) for index in indices]

    # 문자에 해당하는 인덱스 반환
    def get_index_of(self, char: str) -> int:
        return self.char_to_index[char]

    # 단일 SELFIES에 패딩 추가
    def pad_selfie(self, selfie: str) -> str:
        """Add padding to a selfie such that the length of the padded selfie,
        matches that of the longest selfie in the dataset.
        """
        n_padding_tokens = self.max_length - sf.len_selfies(selfie)
        padding = self.pad_char * n_padding_tokens
        padded_selfie = selfie + padding

        return padded_selfie

    # train_samples 전체에 패딩 적용
    @property
    def padded_selfies(self) -> t.List[str]:
        """Returns a list of selfies padded such that
        every string has the length of the longest string.
        """
        # faster appends and pops at edges
        padded_selfies = deque()
        for selfie in self.train_samples:
            padded_selfies.append(self.pad_selfie(selfie))

        return list(padded_selfies)

    # 패딩 문자 반환
    @property
    def pad_char(self) -> str:
        """
        SELFIES 패딩에 사용되는 특수 토큰 문자열 반환.
            - 예: '[nop]' 같은 토큰이 패딩용으로 사용됨
            - 디코딩 시 무시됨
        """
        return self._pad_char

    # 시작 문자 반환
    @property
    def start_char(self) -> str:
        """
        SELFIES 시퀀스 시작 문자 반환.
            - 예: '[^]' 같은 토큰이 시작 토큰으로 사용됨
        """
        return self._start_char

    # 패딩 문자 인덱스 반환
    @property
    def pad_char_index(self) -> int:
        """
        SELFIES 패딩 문자의 인덱스 반환.
            - 예: '[nop]' -> 57
            - 숫자 encoding 된 SELFIES 벡터를 다룰 때 필요
        """
        return self.get_index_of(self.pad_char)

    # 시작 문자 인덱스 반환
    @property
    def start_char_index(self) -> int:
        """
        시작 문자의 인덱스 반환.
            - 예: '[^]' -> 58
            - 시퀀스 생성 또는 디코딩 시 사용
        """
        return self.get_index_of(self.start_char)

    # 최대 길이 반환
    @property
    def max_length(self) -> int:
        """
        SELFIES 시퀀스의 최대 길이 반환.
            - 학습 시 모델 입력 길이를 고정해야 하기 때문에 필요
            - 자동 계산된 fallback 값 또는 수동 지정된 max_length 사용
        """
        return self._max_length

    # @property
    # def encoded_samples(self) -> np.ndarray:
    #     # Encode samples
    #     to_use = [
    #         sample
    #         for sample in self.train_samples
    #         if mm.verified_and_below(sample, self.max_length)
    #     ]
    #     encoded_samples = [
    #         mm.encode(sam, self.max_length, self.char_to_index) for sam in to_use
    #     ]
    #     return np.asarray(encoded_samples)

    # 인코딩된 샘플 반환 
    @property
    def encoded_samples(self) -> np.ndarray:
        # Encode samples
        # to_use = [
        #     sample
        #     for sample in self.train_samples
        #     if mm.verified_and_below(sample, self.max_length)
        # ]
        """
        패딩된 SELFIES 문자열들을 숫자 인덱스 시퀀스로 변환하여 numpy 배열로 반환.
        - 예: '[C][=O][N]' → [12, 45, 67]
        - 모델 입력 (X)으로 바로 사용 가능
        - enc_type='label': 순차 인덱스
            char_to_index = {'[C]': 0, '[=O]': 1, '[O]': 2, '[nop]': 3} 일 때
            selfie = '[C][C][=O][O]' 👉 [0, 0, 1, 2]
        """
        encoded_samples = [
            sf.selfies_to_encoding(sel, self.char_to_index, enc_type="label")
            for sel in self.padded_selfies
        ]
        return np.asarray(encoded_samples)

    # @property
    # def one_hot_encoded_samples(self) -> np.ndarray:
    #     encoded_samples = self.encoded_samples
    #     n_samples = encoded_samples.shape[0]
    #     one_hot_encoding = np.zeros((n_samples, self.max_length, self.num_emd))
    #     for i_seq, seq in enumerate(encoded_samples):
    #         for i_element, element in enumerate(seq):
    #             one_hot_encoding[i_seq, i_element, element] = 1.0

    #     return one_hot_encoding

    # def decode_one_hot_smiles(self, smiles_one_hot: Tensor) -> t.List[str]:
    #     encoded_smiles_list = convert_to_numpy(smiles_one_hot).argmax(axis=2)
    #     return self.decode_smiles(encoded_smiles_list)

    # 숫자 시퀀스를 SELFIES 문자열로 디코딩
    def digit_to_selfies(self, encoded_selfies):
        """
        숫자 시퀀스를 SELFIES 문자열로 복원 : 인덱스 벡터 → SELFIES 문자열 
            - 디코딩에 사용됨
        """
        selfies = sf.encoding_to_selfies(
            encoded_selfies, self.index_to_char, enc_type="label"
        )
        return selfies

    # orquestra.qml.api 
    # Tensor -> torch.Tensor
    # convert_to_numpy -> numpy.ndarray

    # 숫자 시퀀스를 SMILES 문자열로 디코딩
    def decode_fn(self, encoded_selfies: t.Union[np.ndarray, torch.Tensor]) -> t.List[str]:
        """
        숫자 인덱스 시퀀스 (encoded_selfies) → SELFIES 문자열 → SMILES 문자열로 디코딩.
        - SELFIES 토큰을 시작 문자 제거하고
        - sf.decoder()를 통해 최종 SMILES 복원
        """

        # smiles are going to be one-hot encoded
        # encoded_sf_list = convert_to_numpy(encoded_selfies).tolist()

        """
        encoded_selfies
        : torch.Tensor of shape (batch_size, seq_len, vocab_size) or (batch_size, seq_len)
        """

        if isinstance(encoded_selfies, torch.Tensor):
            # 1) torch.Tensor → NumPy array
            #    (detach, cpu 이동 후 .numpy() 로 변환) -> lists 형태로 변환
            numpy_array = encoded_selfies.detach().cpu().numpy()
            encoded_sf_list = numpy_array.tolist()
        elif isinstance(encoded_selfies, np.ndarray):
            encoded_sf_list = encoded_selfies.tolist()
        else:
            raise TypeError("Input must be a torch.Tensor or np.ndarray")

        # 3) 디코딩 : 정수 시퀀스 → SELFIES 문자열
        self.track_strings = []
        decoded_sf_list = list()

        for encoded_sf in encoded_sf_list:
            # 정수 시퀀스 → SELFIES 문자열
            decoded_sf = self.digit_to_selfies(encoded_sf)
            # start token 제거
            if self._start_char in decoded_sf:
                decoded_sf = decoded_sf.replace(self._start_char, "")
            # SELFIES → SMILES
            decoded_smile = sf.decoder(decoded_sf)
            decoded_sf_list.append(decoded_smile)
        return decoded_sf_list

    # 숫자 시퀀스를 SELFIES 문자열로 디코딩
    def decode_char_selfies(self, encoded_selfies: t.Union[np.ndarray, torch.Tensor]) -> t.List[str]:
        """
        SELFIES 문자열 형식 자체를 디코딩 -> SMILES 문자열로 변환.
        ※ decode_fn 는 숫자 인코딩을 SELFIES 로 바꾸고 이를 SMILES 로 디코딩하는 함수
            - 숫자 인코딩이 아닌 문자 기반 SELFIES 입력용
        """
        if isinstance(encoded_selfies, torch.Tensor):
            numpy_array = encoded_selfies.detach().cpu().numpy()
            encoded_sf_list = numpy_array.tolist()
        elif isinstance(encoded_selfies, np.ndarray):
            encoded_sf_list = encoded_selfies.tolist()
        else:
            raise TypeError("Input must be a torch.Tensor or np.ndarray")

        # 디코딩 과정에서 추적할 문자열 리스트
        decoded_sf_list = list()
        sf.decoder()
        for encoded_sf in encoded_sf_list:
            decoded_smile = sf.decoder(encoded_sf)
            decoded_sf_list.append(decoded_smile)
        return decoded_sf_list

    """
    # 원본 코드

    def decode_fn(self, encoded_selfies: Tensor) -> t.List[str]:
        # smiles are going to be one-hot encoded
        encoded_sf_list = convert_to_numpy(encoded_selfies).tolist()
        self.track_strings = []
        decoded_sf_list = list()
        for encoded_sf in encoded_sf_list:
            decoded_sf = self.digit_to_selfies(encoded_sf)
            if self._start_char in decoded_sf:
                decoded_sf = decoded_sf.replace(self._start_char, "")
            decoded_smile = sf.decoder(decoded_sf)
            decoded_sf_list.append(decoded_smile)
        return decoded_sf_list

    def decode_char_selfies(self, encoded_selfies: Tensor) -> t.List[str]:
        # smiles are going to be one-hot encoded
        encoded_sf_list = convert_to_numpy(encoded_selfies).tolist()
        decoded_sf_list = list()
        sf.decoder()
        for encoded_sf in encoded_sf_list:
            decoded_smile = sf.decoder(encoded_sf)
            decoded_sf_list.append(decoded_smile)
        return decoded_sf_list
    """
    
    
    # 화학 구조 시각화
    def draw_smiles(self, smiles: str, molsPerRow: int = 0) -> Image:
        mols = [Chem.MolFromSmiles(s) for s in smiles]
        mols_filtered = [mol for mol in mols if mol is not None]
        if len(mols_filtered) == 0:
            raise RuntimeError("No Valid smiles were provided.")

        if molsPerRow <= 0:
            molsPerRow = len(mols)

        img = Draw.MolsToGridImage(mols, molsPerRow=molsPerRow, returnPNG=False)
        return img
    
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