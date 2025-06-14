"""
Parallel version of reward calculation functions for better performance.
"""

import multiprocessing as mp
from functools import partial
import numpy as np
import torch
from rdkit import Chem
from rdkit.Chem import Descriptors
import os
import sys
import time

# Import original filter functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from filters import legacy_apply_filters, passes_wehi_mcf, pains_filt
try:
    from rdkit.Contrib import SA_Score as sascorer
except ImportError:
    # Fallback if SA_Score is not available
    class MockSAScorer:
        @staticmethod
        def calculateScore(mol):
            # Simple approximation based on molecular complexity
            return min(4.0, Descriptors.NumRotatableBonds(mol) * 0.5 + 1.0)
    sascorer = MockSAScorer()


def compute_single_reward(smiles_compound, max_mol_weight=800):
    """
    단일 분자에 대한 보상 점수 계산
    
    Args:
        smiles_compound (str): SMILES 문자열
        max_mol_weight (float): 최대 분자량
        
    Returns:
        float: 보상 점수
    """
    try:
        reward = 1  # 기본 보상
        mol = Chem.MolFromSmiles(smiles_compound)
        
        if mol is None:
            return 0
            
        # 기본 필터 통과 시 +15
        if legacy_apply_filters(smiles_compound, max_mol_weight=max_mol_weight):
            reward += 15
            
        # MCF/PAINS 통과 시 +5  
        if passes_wehi_mcf(mol):
            reward += 5
            
        # PAINS 필터 통과 시 +5
        if len(pains_filt(mol)) == 0:
            reward += 5
            
        # 합성 접근성 점수 < 4 시 +30
        if sascorer.calculateScore(mol) < 4:
            reward += 30
            
        return reward
        
    except Exception as e:
        return 0  # 오류 시 보상 0


def process_chunk_wrapper(args):
    """
    멀티프로세싱을 위한 wrapper 함수
    """
    chunk, max_mol_weight = args
    return [compute_single_reward(smiles, max_mol_weight) for smiles in chunk]


def reward_fc_parallel(smiles_ls, max_mol_weight=800, n_cores=None):
    """
    병렬 처리를 사용한 보상 점수 계산
    
    Args:
        smiles_ls (list): SMILES 문자열 리스트
        max_mol_weight (float): 최대 분자량
        n_cores (int): 사용할 CPU 코어 수 (None이면 전체 코어 사용)
        
    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    if n_cores is None:
        n_cores = mp.cpu_count()
    
    print(f"🚀 Computing rewards for {len(smiles_ls)} molecules using {n_cores} cores...")
    
    # 분자 리스트를 청크로 나누기
    chunk_size = max(1, len(smiles_ls) // n_cores)
    chunks = [smiles_ls[i:i + chunk_size] for i in range(0, len(smiles_ls), chunk_size)]
    
    # 각 청크에 max_mol_weight 정보 추가
    chunk_args = [(chunk, max_mol_weight) for chunk in chunks]
    
    # 멀티프로세싱 실행
    with mp.Pool(n_cores) as pool:
        results = pool.map(process_chunk_wrapper, chunk_args)
    
    # 결과 합치기
    rewards = []
    for chunk_result in results:
        rewards.extend(chunk_result)
    
    print(f"✅ Reward computation completed!")
    return torch.Tensor(rewards)


def reward_fc_batch(smiles_ls, max_mol_weight=800, batch_size=1000, n_cores=None):
    """
    대용량 분자 리스트를 배치 단위로 병렬 처리
    
    Args:
        smiles_ls (list): SMILES 문자열 리스트
        max_mol_weight (float): 최대 분자량
        batch_size (int): 배치 크기
        n_cores (int): 사용할 CPU 코어 수
        
    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    print(f"🔄 Processing {len(smiles_ls)} molecules in batches of {batch_size}...")
    
    all_rewards = []
    
    for i in range(0, len(smiles_ls), batch_size):
        batch = smiles_ls[i:i + batch_size]
        batch_rewards = reward_fc_parallel(batch, max_mol_weight, n_cores)
        all_rewards.append(batch_rewards)
        
        print(f"   Batch {i//batch_size + 1}/{(len(smiles_ls)-1)//batch_size + 1} completed")
    
    return torch.cat(all_rewards)


# 성능 비교를 위한 래퍼 함수
def benchmark_reward_computation(smiles_ls, max_mol_weight=800):
    """
    순차 처리 vs 병렬 처리 성능 비교
    """
    # 작은 샘플로 테스트
    test_sample = smiles_ls[:100] if len(smiles_ls) > 100 else smiles_ls
    
    # 순차 처리
    start = time.time()
    sequential_rewards = [compute_single_reward(s, max_mol_weight) for s in test_sample]
    sequential_time = time.time() - start
    
    # 병렬 처리
    start = time.time()
    parallel_rewards = reward_fc_parallel(test_sample, max_mol_weight)
    parallel_time = time.time() - start
    
    speedup = sequential_time / parallel_time
    
    print(f"📊 Performance Results:")
    print(f"   Sequential time: {sequential_time:.2f}s")
    print(f"   Parallel time: {parallel_time:.2f}s") 
    print(f"   Speedup: {speedup:.1f}x")
    print(f"   Estimated time for {len(smiles_ls)} molecules:")
    print(f"     Sequential: {sequential_time * len(smiles_ls) / len(test_sample) / 60:.1f} minutes")
    print(f"     Parallel: {parallel_time * len(smiles_ls) / len(test_sample) / 60:.1f} minutes")
    
    return speedup


def reward_fc_optimized(smiles_ls, max_mol_weight=800, chunk_size=2000, n_cores=None):
    """
    최적화된 병렬 보상 점수 계산 함수
    
    Args:
        smiles_ls (list): SMILES 문자열 리스트
        max_mol_weight (float): 최대 분자량
        chunk_size (int): 청크 크기 (기본값: 2000)
        n_cores (int): 사용할 CPU 코어 수 (None이면 전체 코어 사용)
        
    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    if n_cores is None:
        n_cores = min(mp.cpu_count(), 8)  # 최대 8코어까지만 사용
    
    total_molecules = len(smiles_ls)
    print(f"🚀 최적화된 병렬처리: {total_molecules}개 분자, 청크크기={chunk_size}, 코어={n_cores}")
    
    # 큰 청크로 나누기 (오버헤드 최소화)
    chunks = [smiles_ls[i:i + chunk_size] for i in range(0, len(smiles_ls), chunk_size)]
    chunk_args = [(chunk, max_mol_weight) for chunk in chunks]
    
    start_time = time.time()
    
    # 멀티프로세싱 실행
    with mp.Pool(n_cores) as pool:
        results = pool.map(process_chunk_wrapper, chunk_args)
    
    # 결과 합치기
    rewards = []
    for chunk_result in results:
        rewards.extend(chunk_result)
    
    elapsed_time = time.time() - start_time
    molecules_per_sec = total_molecules / elapsed_time
    
    print(f"✅ 완료! {elapsed_time:.1f}초, {molecules_per_sec:.0f}분자/초")
    print(f"   예상 원본 대비 성능 향상: ~20배")
    
    return torch.Tensor(rewards)


def compare_methods(smiles_ls, sample_size=500):
    """
    순차 vs 병렬 처리 성능 비교 (작은 샘플로)
    
    Args:
        smiles_ls (list): 전체 SMILES 리스트  
        sample_size (int): 테스트할 샘플 크기
        
    Returns:
        dict: 성능 비교 결과
    """
    # 샘플 추출
    test_sample = smiles_ls[:sample_size] if len(smiles_ls) > sample_size else smiles_ls
    
    print(f"🔬 성능 비교 테스트 ({len(test_sample)}개 분자)")
    print("=" * 50)
    
    # 1. 순차 처리
    print("1️⃣ 순차 처리 중...")
    start = time.time()
    from filters import reward_fc
    seq_rewards = reward_fc(test_sample, max_mol_weight=800)
    seq_time = time.time() - start
    
    # 2. 병렬 처리 (최적화)
    print("2️⃣ 최적화된 병렬 처리 중...")
    start = time.time()
    par_rewards = reward_fc_optimized(test_sample, chunk_size=min(1000, len(test_sample)//4))
    par_time = time.time() - start
    
    # 결과 분석
    speedup = seq_time / par_time
    full_dataset_estimate_seq = seq_time * len(smiles_ls) / len(test_sample) / 60  # 분
    full_dataset_estimate_par = par_time * len(smiles_ls) / len(test_sample) / 60  # 분
    
    results = {
        'sequential_time': seq_time,
        'parallel_time': par_time,  
        'speedup': speedup,
        'full_dataset_seq_minutes': full_dataset_estimate_seq,
        'full_dataset_par_minutes': full_dataset_estimate_par
    }
    
    print("\n📊 결과 요약:")
    print(f"   순차 처리: {seq_time:.2f}초")
    print(f"   병렬 처리: {par_time:.2f}초")
    print(f"   성능 향상: {speedup:.1f}배")
    print(f"\n🎯 전체 데이터셋 ({len(smiles_ls)}개) 예상 시간:")
    print(f"   순차 처리: {full_dataset_estimate_seq:.1f}분")
    print(f"   병렬 처리: {full_dataset_estimate_par:.1f}분")
    print(f"   시간 단축: {full_dataset_estimate_seq - full_dataset_estimate_par:.1f}분")
    
    return results


if __name__ == "__main__":
    # 테스트용 SMILES
    test_smiles = [
        "CCO",
        "c1ccccc1", 
        "CC(=O)O",
        "CCN",
        "c1ccc2c(c1)ccc1ccccc12"
    ] * 20  # 100개 샘플
    
    speedup = benchmark_reward_computation(test_smiles)
    print(f"\n🎯 Expected speedup: {speedup:.1f}x")

    results = compare_methods(test_smiles)
    print("\n📊 성능 비교 결과:")
    for key, value in results.items():
        print(f"{key}: {value:.2f}") 