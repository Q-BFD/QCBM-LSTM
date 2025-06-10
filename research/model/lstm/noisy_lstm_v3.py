# Modified version of NoisyLSTMv3 without orquestra dependencies

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from warnings import warn

import torch
import torch.nn as nn
from torch.distributions import Categorical



#===============================================================================================================

class Concatenate(nn.Module):
    """A layer that concatenates multiple tensor into a single tensor along a given dimention"""

    def __init__(self, dim: int = -1) -> None:
        """
        Args:
            dim (int, optional): dimension along which to concatenate tensors. Defaults to -1.
        """
        super().__init__()
        self.dim = dim


    """
    # other version 
    def forward(self, x1, x2):
        return torch.cat((x1, x2), dim=self.dim)
    """
    def forward(self, *tensors: torch.Tensor) -> torch.Tensor:
        return torch.concat(tensors, dim=self.dim)
        

    

@dataclass
class NoisyLSTMv3Config:
    name: str
    vocab_size: int
    projection_dim: int
    n_embeddings: int
    embedding_dim: int
    latent_dim: int
    n_layers: int
    dropout: float
    bidirectional: bool
    padding_token_index: Optional[int] = None

    def as_dict(self) -> Dict:
        """Config를 dict로 반환 (Save/Load 시 활용)."""
        return self.__dict__
#===============================================================================================================


# NoisyLSTMv3 모델 Core 학습 모듈을 정의하는 클래스
class _Model(nn.Module):
    def __init__(
        self,
        prior_sample_dim: int,
        lstm: nn.LSTM,
        n_embeddings: int,
        embedding_dim: int,
        output_dim: int,
        projection_activation_fn: nn.Module = nn.Identity(),
        output_activation: nn.Module = nn.Identity(),
        padding_token_index: int = 0,
    ) -> None:
        super().__init__()

        # projection_dim: prior 샘플을 LSTM에 넣기 전에 nn.Linear를 통해 변환한 후의 차원
        self.n_embeddings = n_embeddings   # 임베딩 크기 (예: 문자열 토큰 수)
        self.embedding_dim = embedding_dim # 입력 시퀀스(예: SMILES, SELFIES 등)의 각 토큰을 벡터로 표현한 차원
        self.output_dim = output_dim       # 출력 크기 (예: 문자열 토큰 수)
        self.n_directions: int = 2 if lstm.bidirectional else 1 # 양방향 LSTM인지 확인
        self.n_layers = lstm.num_layers # LSTM 레이어 수    
        self.hidden_size = lstm.hidden_size # LSTM 은닉 상태 크기

        prior_samples_size = prior_sample_dim # prior 샘플 크기
        lstm_input_dim = lstm.input_size      # LSTM 입력 크기 (embedding_dim + prior_sample_projection_dim)
        lstm_hidden_size = lstm.hidden_size   # LSTM 은닉 상태 크기 (hidden_dim)

        self.projection_dim = lstm_input_dim - embedding_dim  # prior 샘플을 LSTM에 넣기 전에 nn.Linear를 통해 변환한 후의 차원
        self.embedding = nn.Embedding(n_embeddings, embedding_dim, padding_idx=padding_token_index)
        # prior 샘플을 LSTM에 넣기 전에 nn.Linear를 통해 변환 ( prior_sample_dim -> projection_dim )
        self.linear_projection = nn.Linear(prior_samples_size, self.projection_dim)
        self.linear_projection_activation = projection_activation_fn
        self.concatenate = Concatenate(dim=-1)
        self.recurrent_net = lstm
        self.output_classifier = nn.Linear(self.n_directions * lstm_hidden_size, output_dim)
        self.output_activation = output_activation

    def forward(
            self,
            inputs: torch.Tensor,
            prior_samples: torch.Tensor,
            hidden_state: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
            ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """Forward pass through the model
           : LSTM 모델의 순전파 과정을 정의하는 함수 : 입력 시퀀스를 받아 출력 시퀀스를 생성하는 함수
        Args:   
            inputs (torch.Tensor): input sequence of integers, where each integer corresponds to a token in a corpus. Shape: (Batch Size, Sequence Length).
            prior_samples (torch.Tensor): samples from a prior distribution. Shape: (Batch Size, Noise Dimension), where <B> is the batch size and <ND> is the dimension of a single sample.
            hidden_state (Optional[Tuple[torch.Tensor, torch.Tensor]], optional): initial hidden state. Defaults to None.
                Expected shape (for each element of tuple): (B, D*n_layers, H), where <B> is the batch size and <H> is the hidden size of the LSTM,
                and <D> is 1 if the LSTM is unidirectional, and 2 if it is bidirectional.
                This is different to the default shape of the hidden state returned by the LSTM, which is (D*n_layers, B, H). The transposed
                variation is compatible with DataParallel, which splits along dimension 0. Hidden state will be transposed before being
                passed to the model (swap dimensions 0 and 1).
            
            inputs (torch.Tensor): 입력 시퀀스, 각 정수는 코퍼스의 토큰에 해당하는 정수 시퀀스 형태: (배치 크기, 시퀀스 길이)            
            prior_samples (torch.Tensor): 사전 분포에서 추출한 샘플로 형태: (배치 크기, 노이즈 차원), 여기서 <B>는 배치 크기이고 <ND>는 단일 샘플의 차원
            hidden_state (Optional[Tuple[torch.Tensor, torch.Tensor]], optional): 초기 은닉 상태. 기본값은 None
                예상되는 형태 (튜플의 각 요소에 대해): (B, D*n_layers, H), 여기서 <B>는 배치 크기이고 <H>는 LSTM의 은닉 크기입니다.
                <D>는 LSTM이 단방향일 경우 1, 양방향일 경우 2입니다.
                이는 LSTM이 반환하는 기본 은닉 상태의 형태인 (D*n_layers, B, H)와는 다릅니다. 전치된 형태는 차원 0을 따라 분할하는 DataParallel과 호환
                은닉 상태는 모델에 전달되기 전에 전치 (차원 0과 1을 교환).

        Returns:
            Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]: sequence of class logits, and the final hidden state.
        """
        # noise shape: (Batch Size, Noise Dimension)
        # inputs shape: (Batch Size, Sequence Length)
        # LSTM에 들어가는 입력은 길이 1 (L=1) -> 한 번에 시퀀스를 다 생성하지 않고, 한 토큰씩 반복적으로 생성 하기때문..!!
        batch_size, sequence_length = inputs.shape
        # prior_samples shape: (Batch Size, Noise Dimension)에서 noise_dim만 추출
        _, noise_dim = prior_samples.shape

        # can only concat similar tensors so we first expand to 3D, then repeat to match shape of input
        # noise shape: (B, SL, ND)
        # (B, D) 크기의 prior 벡터를 시퀀스 길이 L만큼 복제해서 (B, SL, D) 형태로 변환 -> 모든 시퀀스 타임 스템에서 동일한 noise vector 사용
        prior_samples = prior_samples.view((batch_size, 1, noise_dim)).expand((batch_size, sequence_length, noise_dim))
        
        # (B, SL, ProjDim)
        prior_samples = self.linear_projection(prior_samples)
        prior_samples = self.linear_projection_activation(prior_samples)
        
        # (B, SL, EmbDim)
        inputs = self.embedding(inputs)

        # (B, SL, ProjDim + EmbDim), note that ProjDim + EmbDim = LSTM Input Dim
        input_concat = self.concatenate(inputs, prior_samples)

        # # (D*n_layers, batch_size, hidden_size), (D*n_layers, batch_size, hidden_size)
        # # ===== (1) LSTM에 넣기 전에 hidden state 변환 =====
        # if hidden_state is not None:
        #     h, c = hidden_state # 현재 hidden state: (B, D*n_layers, H)
        #     h = h.transpose(0, 1).contiguous()  # (D*n_layers, B, H)
        #     c = c.transpose(0, 1).contiguous()
        #     hidden_state = (h, c)

        # # ===== (2) LSTM 수행 =====
        outputs, hidden_state = self.recurrent_net(input_concat, hidden_state)

        # # ===== (3) 다시 (B, D*n_layers, H) 형식으로 바꾸기 =====
        # h, c = hidden_state
        # h = h.transpose(0, 1).contiguous()
        # c = c.transpose(0, 1).contiguous()
        # hidden_state = (h, c)
        # # (batch_size, D*n_layers, hidden_size), (batch_size, D*n_layers, hidden_size)


        outputs = self.output_classifier(outputs)
        return self.output_activation(outputs), hidden_state

#===============================================================================================================

class NoisyLSTMv3(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        seq_len: int,
        sos_token_index: int,
        prior_sample_dim: int,
        padding_token_index: Optional[int] = None,
        prior_sample_projection_dim: int = 64,
        projection_activation_fn: nn.Module = nn.Identity(),
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        n_layers: int = 1,
        dropout: float = 0.0,
        lr: float = 0.001,
        loss_key: str = "loss",
        model_identifier: str = "noisy-lstm-v3",
        do_greedy_sampling: bool = False,
        sampling_temperature: float = 1.0,
    ) -> None: 
        super().__init__()
        lstm = nn.LSTM(
            input_size=embedding_dim + prior_sample_projection_dim,
            hidden_size=hidden_dim,
            bidirectional=False,
            batch_first=True, # 첫 번째 차원을 배치 차원으로 사용 (Batch, Length, Dimension) 형태로 입력 받음
            num_layers=n_layers,
            dropout=dropout,
        )

        self.vocab_size = vocab_size
        self.seq_len = seq_len
        self.sos_token_index = sos_token_index # 시작 토큰 인덱스
        self.padding_token_index = padding_token_index # 패딩 토큰 인덱스
        self._input_size = (seq_len,) # 입력 시퀀스 길이
        self.prior_sample_dim = prior_sample_dim # prior 샘플 크기

        if not isinstance(sampling_temperature, (float, int)) or sampling_temperature <= 0.0:
            raise ValueError(f"Sampling temperature must be a positive number, got {sampling_temperature}")
        self._sampling_temperature = float(sampling_temperature)

        if not isinstance(do_greedy_sampling, bool):
            raise ValueError(f"Greedy sampling must be a boolean, got {do_greedy_sampling}")

        if do_greedy_sampling and sampling_temperature != 1.0:
            warn("Sampling temperature will be ignored when greedy sampling is enabled")

        self._do_greedy_sampling = do_greedy_sampling

        self.n_directions = 1
        self.n_layers = n_layers
        self.hidden_size = hidden_dim
        self.n_embeddings = vocab_size
        self.embedding_dim = embedding_dim
        self.dropout = dropout
        self.projection_dim = prior_sample_projection_dim

        self._model = _Model(
            prior_sample_dim=prior_sample_dim,
            lstm=lstm,
            n_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            output_dim=vocab_size,
            padding_token_index=padding_token_index,
            projection_activation_fn=projection_activation_fn,
        )

        self.optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)
        self.loss_fn = nn.NLLLoss()
        self.loss_key = loss_key
        self.model_identifier = model_identifier

    # _Model 클래스의 forward 메서드를 호출하여 모델의 순전파 과정을 수행
    def forward(self, inputs: torch.Tensor, prior_samples: torch.Tensor, hidden_state: Optional[Tuple[torch.Tensor, torch.Tensor]] = None) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        return self._model(inputs, prior_samples, hidden_state)

    # 초기 입력 토큰 생성
    def _make_xo(self, n_samples: int) -> torch.Tensor:
        device = next(self.parameters()).device
        return torch.full((n_samples, 1), self.sos_token_index, device=device)

    # 초기 은닉 상태와 셀 상태 생성
    def _make_initial_hidden_state(self, n_samples: int) -> Tuple[torch.Tensor, torch.Tensor]:
        h0 = self._make_h0(n_samples)
        c0 = self._make_c0(n_samples)
        return h0, c0

    # 초기 셀 상태 생성
    def _make_c0(self, batch_size: int) -> torch.Tensor:
        device = next(self.parameters()).device
        return torch.zeros(self.n_layers, batch_size, self.hidden_size, device=device)

    # 초기 은닉 상태 생성
    def _make_h0(self, batch_size: int) -> torch.Tensor:
        device = next(self.parameters()).device
        return torch.zeros(self.n_layers, batch_size, self.hidden_size, device=device)

    # 배치 단위로 학습 수행
    def train_on_batch(self, data: torch.Tensor, prior_samples: torch.Tensor) -> dict:

        if prior_samples is None:
            raise ValueError("Received None for prior_samples.")

        self.train() # 모델을 학습 모드로 설정
        self.optimizer.zero_grad() # 그래디언트 초기화 - 이전 반복에서 계산된 그래디언트 값을 초기화

        # 입력 데이터의 차원 확인
        if len(data.size()) != 2:
            raise ValueError(f"Expected 2D tensor as input, but got {len(data.size())}D tensor.")

        batch_size, seq_len = data.shape
        x0 = self._make_xo(batch_size)
        
        model_inputs = torch.cat((x0, data[:, : seq_len - 1]), dim=1).long()

        class_logits_sequence, _ = self.forward(model_inputs, prior_samples)
        log_prob_sequence = nn.LogSoftmax(-1)(class_logits_sequence)
        generated_sequence_t = log_prob_sequence.permute(0, 2, 1)
        loss = self.loss_fn(generated_sequence_t, data.long())

        loss.backward()
        self.optimizer.step()

        return {self.loss_key: loss.item()}


    def _generate_w_probs(
            self, 
            n_samples: int, 
            prior_samples: torch.Tensor, 
            random_seed: Optional[int] = None
            ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generate samples from the underlying model and return the raw form along with the
        conditional probabilities of each of the sequences.

        Args:
            n_samples (int): then number of samples to generate.
            random_seed (Optional[int], optional): an optional random seed for reproducibility. Defaults to None.
        Returns:
            Tuple[torch.Tensor, torch.Tensor]: the raw generated sequences and the associated probabilities.
        """

        # (B, 1) 형식의 <START> 토큰 시퀀스
        inputs = self._make_xo(n_samples)
        # STM에 넣을 초기 hidden state를 (h0, c0) 형태로 생성
        # shape: (n_layers, B, hidden_dim)
        hidden_state = self._make_initial_hidden_state(n_samples)
        # 빈 시퀀스를 저장할 텐서를 만들고, 시퀀스 길이만큼 샘플을 생성할 준비
        device = next(self.parameters()).device
        outputs = torch.zeros((n_samples, self.seq_len), device=device)
        seq_probabilities = torch.ones((n_samples, 1))


        # 생성은 토큰을 한 개씩 반복해서 만들며,
        # 생성된 토큰은 다음 시점의 입력으로 사용 (모든 배치에 대해 토큰 하나씩 생성 loop)
        with torch.no_grad():
            for index in range(0, self.seq_len):
                # inputs: 현재까지 생성된 시퀀스를 입력으로 줌
                # prior_samples: condition 역할 (전 타임스텝에 동일한 prior 반복 사용)
                # class_logit_sequence: 각 위치에서 각 토큰에 대한 로짓 (B, 1, vocab_size)
                class_logit_sequence, hidden_state = self.forward(inputs, prior_samples, hidden_state)

                if self._do_greedy_sampling: # Greedy Sampling: 가장 확률이 높은 토큰만 선택
                    sampled_token_indices = torch.argmax(class_logit_sequence.squeeze(1), dim=-1)
                else: 
                    # Stochastic Sampling (확률적 샘플링) -> 확률 분포에 따라 토큰 선택
                    cat_distribution = Categorical(logits=class_logit_sequence.squeeze(1) / self._sampling_temperature)
                    sampled_token_indices = cat_distribution.sample()

                outputs[:, index] = sampled_token_indices
                inputs = sampled_token_indices.unsqueeze(1)# 직전 하나의 토큰만 사용. 
                # inputs 갱신
        return outputs, seq_probabilities

    def generate(self, prior_samples: torch.Tensor, random_seed: Optional[int] = None) -> torch.Tensor:
        device = next(self.parameters()).device
        prior_samples = prior_samples.to(device)
        n_samples = prior_samples.size(0)
        generated_sequences, _ = self._generate_w_probs(n_samples, prior_samples, random_seed)
        return generated_sequences

    @property
    def config(self) -> dict:
        return {
            "name": self.model_identifier,
            "vocab_size": self.vocab_size,
            "projection_dim": self.projection_dim,
            "n_embeddings": self.n_embeddings,
            "embedding_dim": self.embedding_dim,
            "latent_dim": self.hidden_size,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
            "bidirectional": self.n_directions > 1,
            "padding_token_index": self.padding_token_index,
        }

    @property
    def sample_size(self) -> Tuple[int, ...]:
        device = next(self.parameters()).device
        prior_samples = torch.zeros((1, self.prior_sample_dim), device=device)
        generated_samples = self.generate(prior_samples)
        return generated_samples.shape[1:]

    @property
    def input_size(self) -> Tuple[int, ...]:
        return self._input_size

    def enable_greedy_sampling(self) -> None:
        self._do_greedy_sampling = True

    def disable_greedy_sampling(self) -> None:
        self._do_greedy_sampling = False
