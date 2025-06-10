import numpy as np

class RandomChoiceSampler:
    
    def __init__(self, sample_dim: int, choices=(0.0, 1.0)):
        """
        주어진 값들 중에서 랜덤하게 prior 샘플을 생성하는 샘플러.

        Args:
            sample_dim (int): 생성할 prior 벡터의 차원
            choices (tuple): 샘플링에 사용할 값들의 리스트
        """
        self.sample_dim = sample_dim
        self.choices = choices

    def generate(self, batch_size: int) -> np.ndarray:
        """
        (batch_size, sample_dim) 형태의 랜덤 벡터를 생성.

        Args:
            batch_size (int): 생성할 벡터 수

        Returns:
            np.ndarray: shape (batch_size, sample_dim)
        """
        return np.random.choice(self.choices, size=(batch_size, self.sample_dim)).astype(np.float32)