"""
source : https://github.com/aspuru-guzik-group/qcbm/blob/main/src/qcbm/qcbm_ibm.py

"""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.circuit import Parameter
import numpy as np
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
from scipy.optimize import minimize
from functools import partial

import json
import sys
from tqdm import tqdm
import torch




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
        self.qc = QuantumCircuit(num_qubits, num_qubits)  # Add classical bits
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
        self.qc.measure(range(self.num_qubits), range(self.num_qubits))  # Add measurements

    def get_executable_circuit(self, parameters, backend):
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

    def minimize(self, loss_fn, initial_params, sampler, backend, target_probs):
        # sampler, backend, target_probs 고정된 loss 함수 만들기
        wrapped_loss = partial(loss_fn, sampler=sampler, backend=backend, target_probs=target_probs)
        result = minimize(wrapped_loss, initial_params, method=self.method, options=self.options)
        return result



class SingleBasisQCBM:

    def __init__(self, ansatz, optimizer, distance_measure=None, choices=(-1.0, 1.0), param_initializer=None, nshot = 10000):
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
        self.simulator = AerSimulator()

    def _default_distance_measure(self, target_probs, model_probs):
        
        """
        기본 거리 측정 함수: (노이즈 완화를 위해 epsilon 포함된) KL divergence
        """

        epsilon = 1e-2
        return np.sum(target_probs * np.log(target_probs / (model_probs + epsilon) + epsilon))

    def _get_initial_parameters(self, initializer):
        """
        초기 파라미터 설정 함수
        - initializer가 주어졌으면 그것을 사용
        - 아니면 랜덤값으로 초기화
        """

        if np.any(initializer):
            return initializer
        return np.random.uniform(-np.pi / 2, np.pi / 2, self.ansatz.number_of_params)

    def _get_model_object(self, parameters, sampler, backend):
        """
        현재 파라미터로부터 생성된 양자 회로 실행 결과의 확률 분포를 반환
        """

        qc = self.ansatz.get_executable_circuit(parameters, backend)
        # simulator = AerSimulator.from_backend(backend)
        # qc_transpiled = transpile(qc, simulator)
        # job = simulator.run([qc_transpiled], shots=self.nshot)
        job = self.simulator.run([qc], shots=self.nshot)
        result = job.result()
        # quasi_dist = result[0].data
        # counts = quasi_dist.meas.get_counts()
        counts = result.get_counts()
        shots = sum(counts.values())
        # 각 비트스트링에 대한 확률 분포 계산
        probs = np.array([counts.get(f"{i:0{self.num_qubits}b}", 0) / shots for i in range(2**self.num_qubits)])
        return probs

    def _get_generator_fn(self, sampler, backend, random_seed=None):
        """
        학습된 파라미터 기반으로 샘플을 생성하는 함수 생성
        """
        def generator(n_samples, parameters):
            qc = self.ansatz.get_executable_circuit(parameters, backend)
            # simulator = AerSimulator.from_backend(backend)
            # qc_transpiled = transpile(qc, simulator)
            # job = simulator.run([qc_transpiled], shots=self.nshot)
            # simulator = AerSimulator()
            job = self.simulator.run([qc], shots=self.nshot)
            result = job.result()
            # quasi_dist = result[0].data
            # counts = quasi_dist.meas.get_counts()
            counts = result.get_counts()
            
            # Convert probabilities to a list of samples
            # samples_list = [list(map(int, k)) for k, v in counts.items() for _ in range(int(v * n_samples))]
            # 각 비트스트링을 개수만큼 복제하여 샘플 생성
            samples_list = np.array([
                list(map(int, k)) for k, v in counts.items()
                for _ in range(v)  
            ])
            # print(samples_list)
            # Calculate the number of missing samples
            num_missing_samples = n_samples - len(samples_list)
            
            # 필요한 개수보다 적게 생성됐으면, 부족한 만큼 추가 샘플링
            # If we have fewer samples than needed, we need to resample
            if num_missing_samples > 0:
                # Get additional samples based on the probabilities

                keys = list(counts.keys())
                values = np.array(list(counts.values()), dtype=np.float64)
                probs = values / np.sum(values) 

                additional_samples = np.random.choice(
                    keys,
                    size=num_missing_samples,
                    p=probs
                )

                additional_samples = [list(map(int, sample)) for sample in additional_samples]
                samples_list = np.vstack([samples_list, additional_samples])
                # samples_list.extend(additional_samples)
            
            # Convert list of samples to a numpy array
            # 최종적으로 n_samples 크기의 샘플 반환
            samples = np.array(samples_list[:n_samples])
            return samples
        return generator

    def loss_fn(self, parameters, sampler, backend, target_probs):
        model_probs = self._get_model_object(parameters, sampler, backend)
        return self.distance_measure(target_probs, model_probs)
    
    def train_on_batch(self, X, Y, sampler, backend, n_epochs):
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
        with tqdm(total=n_epochs, desc="Training Epochs", file=sys.stdout, miniters=1) as pbar:
            for epoch in range(n_epochs):
                

                # 현재 파라미터에 대해 loss 최소화
                result = self.optimizer.minimize(
                    self.loss_fn,
                    self.params,
                    sampler,
                    backend,
                    target_probs
                )

                self.params = result.x # 다음 단계의 초기값으로 넘김
                loss_values.append(result.fun)
                # loss_values.append(self.loss_fn(self.params, sampler, backend, target_probs))
                
                pbar.set_description(f"Epoch {epoch+1}/{n_epochs}")
                pbar.set_postfix(loss=result.fun)
                pbar.update()
                # tqdm.write(f"[Epoch {epoch+1}/{n_epochs}] Loss: {result.fun:.10f}")
                # Progress bar 업데이트
            
        return result,loss_values

    def generate(self, num_samples, sampler, backend):
        """
        학습된 파라미터로 n개의 샘플 생성
        """
        generator = self._get_generator_fn(sampler, backend)
        samples = generator(num_samples, self.params)
        unique_samples, counts = np.unique(samples, axis=0, return_counts=True)
        probabilities = counts / num_samples
        return torch.Tensor(samples),unique_samples,probabilities

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
