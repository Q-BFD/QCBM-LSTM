# 필수 라이브러리 임포트
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, TensorDataset
import cloudpickle

# save in file:

def save_obj(obj, file_path):
    """
    파이썬 객체를 바이너리 파일로 저장하는 함수
    
    Args:
        obj: 저장할 파이썬 객체
        file_path: 저장할 파일 경로
        
    Returns:
        저장 결과
    """
    
    with open(file_path, "wb") as f:
        r = cloudpickle.dump(obj, f)
    return r


def load_obj(file_path):
    with open(file_path, "rb") as f:
        obj = cloudpickle.load(f)
    return obj
    
    

# 데이터셋을 정의하는 커스텀 클래스
class CustomDataset(Dataset):
    def __init__(self, data, labels=None):
        self.data = data
        self.labels = labels

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        if self.labels is not None:
            return self.data[idx], self.labels[idx]
        return self.data[idx]


def train_data_loader(data, probs, batch_size):
    # probs: softmax된 가중치 벡터
    sampler = torch.utils.data.WeightedRandomSampler(weights=probs, num_samples=len(data), replacement=True)
    dataset = TensorDataset(data)
    loader = DataLoader(dataset, sampler=sampler, batch_size=batch_size)
    return loader

# 데이터 로더 함수 정의
def new_data_loader(data, **loader_kwargs):

    # 데이터 로더 설정 추출
    batch_size = loader_kwargs.get("batch_size", 128)
    drop_last = loader_kwargs.get("drop_last", True)
    shuffle = loader_kwargs.get("shuffle", True)
    seed = loader_kwargs.get("seed", 42)
    fraction = loader_kwargs.get("fraction", 1.0)
    
    # 랜덤 시드 설정 및 데이터 셔플링
    rng = np.random.default_rng(seed)
    data = rng.permutation(data)
    
    # 데이터 축소 (fraction 비율만큼 사용)
    if fraction < 1.0:
        num_samples = int(len(data) * fraction)
        data = data[:num_samples]
    
    # 데이터셋 생성 및 데이터 로더 반환
    dataset = CustomDataset(data)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
        num_workers=0
    )
    return dataloader