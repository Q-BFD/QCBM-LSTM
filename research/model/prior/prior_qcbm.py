"""
source : https://github.com/aspuru-guzik-group/qcbm/blob/main/src/qcbm/qcbm_ibm.py

"""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.circuit import Parameter
import numpy as np
from scipy.optimize import minimize
from functools import partial
import json
import sys
from tqdm import tqdm
import torch

# Qiskit 1.0+ uses primitives
from qiskit.primitives import Sampler

class QCBMAnsatz:
    
    def __init__(self, num_qubits, depth):
        """
        QCBMAnsatz 객체를 초기화합니다.

        Args:
            num_qubits (int): 사용할 큐비트 수
            depth (int): 회로의 층 수 (entangling layer 포함)
        """
        
        self.num_qubits = num_qubits
        self.number_of_qubits = num_qubits
        self.depth = depth
        # 파라미터 목록 생성 (총 num_qubits * depth개)
        self.params = [Parameter(f'theta_{i}') for i in range(num_qubits * depth)]
        self.number_of_params = len(self.params)
        self.qc = QuantumCircuit(num_qubits) # No classical bits needed for Sampler
        self._build_circuit()

    def _build_circuit(self):
        """
        QCBM 회로를 구성하는 내부 메서드
        - 각 층마다 각 큐비트에 RY 회전 게이트 적용
        - 층마다 인접한 큐비트 간 CNOT 게이트로 얽힘 생성
        - 마지막에 전 큐비트 측정
        """

        param_idx = 0 # 파라미터 인덱스 초기화
        for _ in range(self.depth):
            # RY 회전 게이트를 모든 큐비트에 적용
            for qubit in range(self.num_qubits):
                self.qc.ry(self.params[param_idx], qubit)
                param_idx += 1

            # CNOT 게이트를 인접 큐비트 쌍에 적용하여 얽힘 생성
            for qubit in range(self.num_qubits - 1):
                self.qc.cx(qubit, qubit + 1)
        # Sampler does not require classical measurements to be added to the circuit
        # It calculates probabilities directly from the final statevector.

    def get_executable_circuit(self, parameters):
        """
        주어진 파라미터로 회로에 값을 바인딩하고, 지정된 backend에 맞게 transpile된 회로 반환

        Args:
            parameters (List[float]): 파라미터 값 리스트
            backend: 실행할 백엔드 (시뮬레이터 또는 실제 양자 하드웨어)

        Returns:
            QuantumCircuit: 파라미터가 할당되고 transpile된 실행 가능한 양자 회로
        """

        # 파라미터 → 실제 값으로 매핑
        param_dict = {self.params[i]: parameters[i] for i in range(len(self.params))}

        # 원본 회로 복사
        qc_copy = self.qc.copy()

        # 파라미터 값 바인딩 (inplace)
        qc_copy.assign_parameters(param_dict, inplace=True)
        # Transpile the circuit for the specific backend
        # simulator = AerSimulator.from_backend(backend)
        # transpiled_circuit = transpile(qc_copy, backend=simulator)
        return qc_copy




class ScipyOptimizer:
    def __init__(self, method='COBYLA', options=None):
        self.method = method
        self.options = options if options else {}

    def minimize(self, loss_fn, initial_params, target_probs):
        wrapped_loss = partial(loss_fn, target_probs=target_probs)
        result = minimize(wrapped_loss, initial_params, method=self.method, options=self.options)
        return result



class SingleBasisQCBM:

    def __init__(self, ansatz, optimizer, distance_measure=None, choices=(-1.0, 1.0), param_initializer=None, nshot=10000):
        """
        QCBM (Quantum Circuit Born Machine)을 기반으로 한 단일 분포 학습기 초기화
        
        - ansatz: 파라미터화된 양자 회로 객체 (예: QCBMAnsatz)
        - optimizer: scipy 기반 최적화 알고리즘 객체
        - distance_measure: 분포 간 거리 측정 함수 (default: KL divergence)
        - choices: 이진 샘플링을 위한 기본값 (현재는 사용되지 않음)
        - param_initializer: 초기 파라미터 설정 함수 또는 값
        """

        self.ansatz = ansatz
        self.optimizer = optimizer
        self.num_qubits = ansatz.number_of_qubits
        self.distance_measure = distance_measure if distance_measure else self._default_distance_measure
        self.choices = choices
        self.params = self._get_initial_parameters(param_initializer)
        self.nshot = nshot
        # Use the modern Qiskit Sampler primitive
        self.sampler = Sampler()

    def _default_distance_measure(self, target_probs, model_probs):
        
        """
        기본 거리 측정 함수: (노이즈 완화를 위해 epsilon 포함된) KL divergence
        """

        epsilon = 1e-6 # A small epsilon to avoid log(0)
        # Ensure model_probs is a numpy array for vectorized operations
        model_probs = np.array(list(model_probs.values()))
        # Align target_probs and model_probs, assuming they cover the same space
        # Here we assume model_probs keys are integers from 0 to 2**n-1
        full_model_probs = np.zeros(2**self.num_qubits)
        for i, prob in enumerate(model_probs):
             full_model_probs[i] = prob

        # To prevent division by zero or log of zero, add epsilon
        return np.sum(target_probs * (np.log(target_probs + epsilon) - np.log(full_model_probs + epsilon)))

    def _get_initial_parameters(self, initializer):
        """
        초기 파라미터 설정 함수
        - initializer가 주어졌으면 그것을 사용
        - 아니면 랜덤값으로 초기화
        """

        if initializer is not None and np.any(initializer):
            return initializer
        return np.random.uniform(-np.pi / 2, np.pi / 2, self.ansatz.number_of_params)

    def _get_model_probs(self, parameters):
        """
        현재 파라미터로부터 생성된 양자 회로 실행 결과의 확률 분포를 반환
        """

        qc = self.ansatz.get_executable_circuit(parameters)
        # The Sampler primitive runs the circuit and returns the probability distribution
        job = self.sampler.run(circuits=[qc], shots=self.nshot)
        result = job.result()
        # The result object from Sampler gives a quasi-distribution
        quasi_dist = result.quasi_dists[0]
        # It contains the probabilities for each outcome.
        # We can get it as a dictionary of {outcome: probability}
        probs_dict = quasi_dist.binary_probabilities()
        
        # Create a full probability vector
        full_probs = np.zeros(2**self.num_qubits)
        for b, p in probs_dict.items():
            index = int(b, 2)
            full_probs[index] = p
        return full_probs

    def _get_generator_fn(self):
        """
        학습된 파라미터 기반으로 샘플을 생성하는 함수 생성
        """
        def generator(n_samples, parameters):
            qc = self.ansatz.get_executable_circuit(parameters)
            job = self.sampler.run([qc], shots=n_samples) # Run with n_samples shots
            result = job.result()
            
            # Sampler already returns counts-like data, let's use that
            quasi_dist = result.quasi_dists[0]
            # convert integer outcomes to bitstrings
            counts = {f'{k:0{self.num_qubits}b}': v*n_samples for k, v in quasi_dist.items()}
            
            samples_list = []
            for bitstring, count in counts.items():
                # Ensure count is an integer for range()
                for _ in range(int(round(count))):
                    samples_list.append(list(map(int, bitstring)))
            
            # If rounding leads to a different number of samples, adjust
            if len(samples_list) != n_samples:
                # This part is tricky. For simplicity, we can just truncate or pad.
                if len(samples_list) > n_samples:
                    samples_list = samples_list[:n_samples]
                else:
                    # If we need more, we can sample from the distribution
                    diff = n_samples - len(samples_list)
                    bitstrings = list(counts.keys())
                    probabilities = np.array(list(counts.values())) / sum(counts.values())
                    extra_samples = np.random.choice(bitstrings, size=diff, p=probabilities)
                    for s in extra_samples:
                        samples_list.append(list(map(int, s)))

            return np.array(samples_list)
        return generator

    def loss_fn(self, parameters, target_probs):
        model_probs = self._get_model_probs(parameters)
        return self.distance_measure(target_probs, model_probs)
    
    def train_on_batch(self, X, Y, sampler=None, backend=None, n_epochs=10):
        """
        주어진 데이터 X, Y를 기반으로 파라미터를 업데이트
        - X: 입력 비트스트링 [[0 1 0 1] [1 1 1 1 ]]
        - Y: 각 입력에 대한 타깃 확률 값 [[0.1 0.9]]
        """
        target_probs = np.zeros(2**self.num_qubits)
        loss_values = []

        # target_probs: 입력된 샘플 기반 확률 벡터 생성
        for x, y in zip(X, Y):
            index = int("".join(map(str, x.int().tolist())), 2)
            target_probs[index] = y
            # index = int("".join(map(str, x)), 2)
            # target_probs[index] = y

        # 최적화 루프
        print(f"Training QCBM for {n_epochs} iterations (not epochs)...")
        with tqdm(total=n_epochs, desc="Optimizing QCBM", ncols=80) as pbar:
            def callback(xk):
                pbar.update(1)
                loss = self.loss_fn(xk, target_probs)
                pbar.set_postfix(loss=f"{loss:.6f}")

            # Scipy's minimize has its own iteration loop.
            # maxiter in options will control the number of "epochs"
            self.optimizer.options['maxiter'] = n_epochs
            self.optimizer.options['callback'] = callback
            
            result = self.optimizer.minimize(
                self.loss_fn,
                self.params,
                target_probs
            )
            self.params = result.x
            # The final loss is in result.fun
            loss_values = [result.fun] * n_epochs # A bit of a hack for logging

        print(f"✅ QCBM training completed. Final loss: {result.fun:.6f}")
        return result, loss_values

    def generate(self, num_samples, sampler=None, backend=None):
        """
        학습된 파라미터로 n개의 샘플 생성
        """
        generator = self._get_generator_fn()
        samples = generator(num_samples, self.params)
        unique_samples, counts = np.unique(samples, axis=0, return_counts=True)
        probabilities = counts / num_samples
        return torch.Tensor(samples), unique_samples, probabilities

    def save_params(self, filename):
        """
        현재 파라미터 값을 JSON 파일로 저장
        """
        with open(filename, 'w') as f:
            json.dump(self.params.tolist(), f)

    def load_params(self, filename):
        """
        저장된 파라미터 JSON 파일로부터 파라미터 로딩
        """
        with open(filename, 'r') as f:
            self.params = np.array(json.load(f))
