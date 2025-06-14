"""
Fast reward computation with simplified filters for better performance.
"""

import torch
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fast_reward_fc(smiles_ls, max_mol_weight=800):
    """
    빠른 보상 점수 계산 (핵심 필터만 사용)
    
    보상 기준:
    - 유효한 분자 +5
    - 분자량 조건 +10  
    - 로그P 조건 +10
    - 회전 결합 조건 +10
    - H-bond 조건 +10
    
    Args:
        smiles_ls (list): SMILES 문자열 리스트
        max_mol_weight (float): 최대 분자량
        
    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    rewards = []
    
    for smiles in smiles_ls:
        try:
            reward = 1  # 기본 보상
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                rewards.append(0)
                continue
                
            # 기본 유효성 +5
            reward += 5
            
            # 분자량 조건 (300-800) +10
            mol_weight = rdMolDescriptors.CalcExactMolWt(mol)
            if 300 <= mol_weight <= max_mol_weight:
                reward += 10
                
            # LogP 조건 (-2 to 5) +10  
            logp = Descriptors.MolLogP(mol)
            if -2 <= logp <= 5:
                reward += 10
                
            # 회전 가능한 결합 수 (<10) +10
            rotatable_bonds = Descriptors.NumRotatableBonds(mol)
            if rotatable_bonds < 10:
                reward += 10
                
            # H-bond 기증자/수용자 조건 +10
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            if hbd <= 5 and hba <= 10:
                reward += 10
                
            rewards.append(reward)
            
        except Exception:
            rewards.append(0)
    
    return torch.Tensor(rewards)


def minimal_reward_fc(smiles_ls, max_mol_weight=800):
    """
    최소한의 필터만 사용한 초고속 버전
    
    보상 기준:
    - 유효한 분자 +10
    - 분자량 조건 +20
    - 원자 수 조건 +20
    
    Args:
        smiles_ls (list): SMILES 문자열 리스트 
        max_mol_weight (float): 최대 분자량
        
    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    rewards = []
    
    for smiles in smiles_ls:
        try:
            reward = 1
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                rewards.append(0)
                continue
                
            # 기본 유효성 +10
            reward += 10
            
            # 분자량 조건 +20
            mol_weight = rdMolDescriptors.CalcExactMolWt(mol)
            if mol_weight <= max_mol_weight:
                reward += 20
                
            # 원자 수 조건 (5-50) +20
            num_atoms = mol.GetNumAtoms()
            if 5 <= num_atoms <= 50:
                reward += 20
                
            rewards.append(reward)
            
        except Exception:
            rewards.append(0)
    
    return torch.Tensor(rewards)


# 성능 비교 함수
def compare_reward_methods(smiles_ls):
    """
    다양한 reward 계산 방법 성능 비교
    """
    import time
    from filters import reward_fc  # 원본 함수
    
    print("🏃‍♂️ Comparing reward computation methods...")
    
    # 테스트 샘플
    test_sample = smiles_ls[:500] if len(smiles_ls) > 500 else smiles_ls
    
    methods = [
        ("Original reward_fc", reward_fc),
        ("Fast reward_fc", fast_reward_fc), 
        ("Minimal reward_fc", minimal_reward_fc)
    ]
    
    results = {}
    
    for name, method in methods:
        try:
            start = time.time()
            rewards = method(test_sample)
            elapsed = time.time() - start
            
            results[name] = {
                'time': elapsed,
                'avg_reward': rewards.mean().item(),
                'max_reward': rewards.max().item()
            }
            
            print(f"✅ {name}: {elapsed:.2f}s, avg_reward: {rewards.mean():.1f}")
            
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            
    return results


if __name__ == "__main__":
    # 테스트
    test_smiles = [
        "CCO", "c1ccccc1", "CC(=O)O", "CCN", 
        "c1ccc2c(c1)ccc1ccccc12", "CC(C)CC(=O)O"
    ] * 100
    
    results = compare_reward_methods(test_smiles)
    
    if len(results) > 1:
        original_time = results["Original reward_fc"]["time"]
        for name, data in results.items():
            if name != "Original reward_fc":
                speedup = original_time / data["time"]
                print(f"🚀 {name} speedup: {speedup:.1f}x") 