# 표준 library
import logging
import time
import os, sys

import requests # HTTP 요청 및 응답 처리
import sqlite3  # 데이터베이스 연결 및 쿼리 실행
from datetime import datetime

import numpy as np # 수치 연산 라이브러리
import pandas as pd # 데이터 분석 라이브러리
from tqdm import tqdm # 진행 상태 표시 라이브러리

import torch


# RDKit library
from rdkit import Chem, DataStructs

import rdkit.Chem as rdc
import rdkit.Chem.Descriptors as rdcd

from rdkit.Chem.Crippen import MolLogP
from rdkit.Chem.Descriptors import ExactMolWt
from rdkit.Chem.Lipinski import NumHAcceptors, NumHDonors

from rdkit.Chem import (
    Draw,
    AllChem,
    rdFingerprintGenerator,
    Crippen,
    Descriptors,
    Lipinski,
    rdMolDescriptors as rdcmd,
    rdmolops as rdcmo,
)

# SAScore
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDConfig
sys.path.append(os.path.join(RDConfig.RDContribDir, 'SA_Score'))
# now you can import sascore!
import sascorer

#===============================================================================================================

# Diversity Calculation

def get_diversity(smiles_ls):
    """
    SMILES 문자열 리스트를 입력받아 분자 간 구조적 다양성(1 - 평균 Tanimoto 유사도)을 백분율로 반환합니다.

    Args:
        smiles_ls (list[str]): SMILES 문자열들의 리스트

    Returns:
        float: 다양성 지표 (0~100 사이 값, 높을수록 다양함)
    """

    # 1. SMILES → RDKit 분자 객체로 변환
    pred_mols = [Chem.MolFromSmiles(s) for s in smiles_ls]  # 분자 객체로 변환
    pred_mols = [x for x in pred_mols if x is not None]     # 유효하지 않은 분자 제거

    # 2. 분자 객체 → 피쳐 벡터로 변환
    # Morgan 지문은 분자의 각 원자를 중심으로 특정 반경(radius) 내의 환경을 탐색하여 고유한 식별자를 생성
    # 이러한 식별자들은 해시 함수를 통해 고정된 크기의 비트 벡터로 변환되며, 이는 분자의 구조적 정보를 압축하여 표현
    
    # 각 분자의 Morgan fingerprint 생성 (radius=3, 길이=2048)

    # 기존 코드
    # pred_fps = [AllChem.GetMorganFingerprintAsBitVect(x, 3, 2048) for x in pred_mols]
    # -> warning 발생하여 아래와 수정 

    # Morgan 지문 생성기 초기화 (반경=3, 지문 크기=2048비트) : 
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=2048)
    # 각 분자의 fingerprint 생성
    pred_fps = [gen.GetFingerprint(mol) for mol in pred_mols]

    # 3. 피쳐 벡터 간 유사도 계산
    similarity = 0
    # 모든 fingerprint 쌍에 대한 Tanimoto 유사도 계산 (누적)
    for i in range(len(pred_fps)):
        # i번째 분자와 이전 모든 분자의 유사도 계산
        sims = DataStructs.BulkTanimotoSimilarity(pred_fps[i], pred_fps[:i])
        similarity += sum(sims)

    # 4. 모든 fingerprint 쌍의 수
    n = len(pred_fps)
    n_pairs = n * (n - 1) / 2

    # 5. 다양성 = 1 - 평균 유사도
    diversity = 1 - (similarity / n_pairs)

    # 6. 결과를 백분율로 변환하여 출력
    return diversity * 100


#===============================================================================================================

# Reward Calculation by Chemistry42(유료)
# 참고 : https://github.com/chemistry42/rip-api-python 

class RewardAPI:
    def __init__(
        self,
        username,
        password,
        base_url="https://rip.chemistry42.com",
        db_path="workflows.db",
    ):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)
        self.db_path = db_path
        self.create_table()

    def create_table(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS workflows (
                     id INTEGER PRIMARY KEY,
                     name TEXT,
                     workflow_uuid TEXT UNIQUE,
                     timestamp TEXT)"""
        )
        conn.commit()
        conn.close()

    def save_workflow_id(self, name, workflow_uuid):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO workflows (name, workflow_uuid, timestamp) VALUES (?, ?, ?)",
            (name, workflow_uuid, timestamp),
        )
        conn.commit()
        conn.close()

    def post_smiles(self, name, mpo_score_definition_id, smiles_list):
        url = f"{self.base_url}/v1/score/smiles"
        payload = {
            "mpo_score_definition_id": mpo_score_definition_id,
            "smiles": smiles_list,
        }
        response = requests.post(url, json=payload, auth=self.auth, verify=False)
        print(response)
        if response.status_code == 200:
            workflow_uuid = response.json()["workflow_uuid"]
            self.save_workflow_id(name, workflow_uuid)
            return workflow_uuid
        else:
            raise ValueError("Error posting smiles")

    def get_workflow_results(self, workflow_uuid):
        url = f"{self.base_url}/v1/workflows/{workflow_uuid}/result"
        response = requests.get(url, auth=self.auth, verify=False)
        if response.status_code == 200:
            return response.json()["results"]
        elif response.status_code == 404:
            raise ValueError("Workflow UUID does not exist")
        else:
            raise ValueError("Error getting workflow results")

    def parse_results(self, results, model_name):
        parsed_results = []
        for result in results:
            parsed_result = {
                "smiles": result["smiles"],
                "main_reward": result["main_reward"],
                "filters_passed": result["filters_passed"],
                "ROMol_was_valid": result["ROMol_was_valid"],
                "model": model_name,
            }
            parsed_results.append(parsed_result)
        return parsed_results

    def get_all_workflows(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, workflow_uuid, timestamp FROM workflows")
        result = c.fetchall()
        conn.close()
        return [
            {"id": row[0], "name": row[1], "workflow_uuid": row[2], "timestamp": row[3]}
            for row in result
        ]

    def get_workflow_status(self, workflow_uuid):
        url = f"{self.base_url}/v1/workflows/{workflow_uuid}"
        response = requests.get(url, auth=self.auth, verify=False)
        if response.status_code == 200:
            if response.json()["state"] == "success":
                return response.json()["state"]
            else:
                return response.json()
        elif response.status_code == 404:
            raise ValueError("Workflow UUID does not exist")
        else:
            raise ValueError("Error getting workflow status")



def rew_chemistry(
    smiles_list: list, api: RewardAPI, custom_w_name: str = "training_loop"
):
    workflow_ids = []
    not_submitted = []
    submitted = {}
    rewards = []
    smiles_dict = {}
    step_size = 10
    if len(smiles_list) > 10:
        for i in range(0, len(smiles_list), 10):
            smiles_ls = [smiles_["smiles"] for smiles_ in smiles_list[i : i + 10]]
            try:
                workflow_uuid = api.post_smiles(
                    name=f"{custom_w_name}_{i}_{i+10}",
                    mpo_score_definition_id=0,
                    smiles_list=smiles_ls,
                )
                submitted[workflow_uuid] = smiles_ls
                print(i, i + 10)
                submited_flag = True
            except:
                not_submitted.append(smiles_ls)
                rewards.append(step_size * [-1.6])
                submited_flag = False

            if submited_flag:
                try:
                    status = api.get_workflow_status(workflow_uuid)
                    while status != "success":
                        time.sleep(10)
                        status = api.get_workflow_status(workflow_uuid)

                    results = api.get_workflow_results(workflow_uuid)
                    for reward_, key_ in zip(results, list(range(i, i + 10))):
                        if reward_["filters_passed"]:
                            rewards.append(4 * (reward_["main_reward"] + 1))

                        else:
                            rewards.append(-1.6)
                        smiles_dict[key_] = {
                            "filters_passed": reward_["filters_passed"],
                            "ROMol_was_valid": reward_["ROMol_was_valid"],
                            "smiles": reward_["smiles"],
                            "reward": reward_["main_reward"],
                        }
                except:
                    print(f"{workflow_uuid} pulling results is faled!")
                    rewards.append(step_size * [-1.6])
    else:
        smiles_ls = [smiles_["smiles"] for smiles_ in smiles_list]
        api.post_smiles(
            name="training_loop",
            mpo_score_definition_id=0,
            smiles_list=smiles_ls,
        )
        try:
            status = api.get_workflow_status(workflow_uuid)
            while status != "success":
                time.sleep(5)
                status = api.get_workflow_status(workflow_uuid)

            results = api.get_workflow_results(workflow_uuid)
            for reward_, key_ in zip(results, list(range(i, len(results)))):
                if reward_["filters_passed"]:
                    rewards.append(4 * (reward_["main_reward"] + 1))
                else:
                    rewards.append(-1.6)
                smiles_dict[key_] = {
                    "filters_passed": reward_["filters_passed"],
                    "ROMol_was_valid": reward_["ROMol_was_valid"],
                    "smiles": reward_["smiles"],
                    "reward": reward_["main_reward"],
                }
        except:
            print(f"{workflow_uuid} pulling results is faled!")
            rewards.append(step_size * [-1.6])
    print(rewards)
    return smiles_dict, rewards


#===============================================================================================================


def maximum_ring_size(mol):
    """
    Calculate maximum ring size of molecule
    : 분자 내 가장 큰 고리(ring)의 크기를 계산

    Args:
        mol (rdkit.Chem.rdchem.Mol): 분자 객체

    Returns:
        int: 가장 큰 고리의 크기
    """
    cycles = mol.GetRingInfo().AtomRings()
    if len(cycles) == 0:
        maximum_ring_size = 0
    else:
        maximum_ring_size = max([len(ci) for ci in cycles])
    return maximum_ring_size


#===============================================================================================================

def filter_phosphorus(mol):
    """
    인(P) 원자를 포함하되, 적절한 구조(=O를 가진 구조)가 아닐 경우 걸러냄

    Args:
        mol (rdkit.Chem.rdchem.Mol): 분자 객체

    Returns:
        True  → 부적절한 인 원자 포함 (필터링 대상)
        False → 문제 없음
    """

    """
    Check for presence of phopshorus fragment
    Return True: contains proper phosphorus
    Return False: contains improper phosphorus
    """
    violation = False
    if mol.HasSubstructMatch(rdc.MolFromSmarts("[P,p]")):
        if not mol.HasSubstructMatch(rdc.MolFromSmarts("*~[P,p](=O)~*")):
            violation = True
    return violation


#===============================================================================================================


def substructure_violations(mol):
    """
    부적절한 서브구조 SMARTS 패턴을 검사하여 포함 여부 반환

    Args:
        mol (rdkit.Chem.rdchem.Mol): 분자 객체

    Returns:
        True  → 금지된 서브구조 포함 (필터링 대상)
        False → 문제 없음
    """

    """
    Check for substructure violates
    Return True: contains a substructure violation
    Return False: No substructure violation
    """
    
    violation = False
    forbidden_fragments = [
        "[S&X3]",
        "[S&X4]",
        "[S&X6]",
        "[S&X2]",
        "[S&X1]",
        "*1=**=*1",
        "*1*=*=*1",
        "*1~*=*1",
        "[F,Cl,Br]C=[O,S,N]",
        "[Br]-C-C=[O,S,N]",
        "[N,n,S,s,O,o]C[F,Cl,Br]",
        "[I]",
        "[S&X3]",
        "[S&X5]",
        "[S&X6]",
        "[B,N,n,O,S]~[F,Cl,Br,I]",
        "*=*=*=*",
        "*=[NH]",
        "[P,p]~[F,Cl,Br]",
        "SS",
        "C#C",
        "C=C=C",
        "*=*=*",
        "NNN",
        "[R3R]",
        "[R4R]",
    ]

    for ni in range(len(forbidden_fragments)):

        if mol.HasSubstructMatch(rdc.MolFromSmarts(forbidden_fragments[ni])) == True:
            violation = True
            # print('Substruct violation is: ', forbidden_fragments[ni])
            break
        else:
            continue

    return violation


#===============================================================================================================

def lipinski_filter(mol, max_mol_weight=800):
    """
    Lipinski's Rule of 5에 기반한 필터링 함수.
    
    Args:
        mol (rdkit.Chem.rdchem.Mol): 분자 객체
        max_mol_weight (int): 분자 최대 무게 (기본값: 800)

    Returns:
        True  → 기준 통과 (약물 적합)
        False → 위반
    """
    try:
        # mol = Chem.MolFromSmiles(smiles)
        return (
            MolLogP(mol) <= 5
            and NumHAcceptors(mol) <= 10
            and NumHDonors(mol) <= 5
            # and 300 <= ExactMolWt(mol) <= max_mol_weight ## 수정!! (보통 max 이하)
            and ExactMolWt(mol) <= max_mol_weight
        )
    except:
        return False

#===============================================================================================================

def legacy_apply_filters(smile_, max_mol_weight=800):
    """
    GDB-13 프로젝트 기반의 필터 기준 함수.

    필터 조건:
    - 이상한 이온(+, -)이 포함된 SMILES 제거
    - RDKit 기반 필터 (전하, 라디칼, 고리, 브릿지 등)
    - Lipinski 필터
    - Rotatable bond 수 제한

    Returns:
        True  → 통과
        False → 탈락
    """
    try:
        
        if (
            "C-" in smile_
            or "N+" in smile_
            or "C+" in smile_
            or "S+" in smile_
            or "S-" in smile_
            or "O+" in smile_
        ):
            return False
        mol = Chem.MolFromSmiles(smile_)

        if mol == None:
            return False
        # Added after GDB-13 was filtered to get rid charged molecules
        if rdcmo.GetFormalCharge(mol) != 0:
            # print('Formal charge failed! Value: ', rdcmo.GetFormalCharge(mol))
            return False
        # Added after GDB-13 was filtered to get rid radicals
        elif rdcd.NumRadicalElectrons(mol) != 0:
            # print('rdcd.NumRadicalElectrons(mol) failed! Value: ', rdcd.NumRadicalElectrons(mol))
            return False
        # Filter by bridgehead atoms : 브릿지헤드 원자 수 제한
        elif rdcmd.CalcNumBridgeheadAtoms(mol) > 2:
            return False
        # Filter by ring size : 고리크기 제한
        elif maximum_ring_size(mol) > 8:
            return False
        # Filter by proper phosphorus : 비정상적인 인(P) 구조 제한
        elif filter_phosphorus(mol):
            return False
        # Filter by substructure violations : 금지된 서브 구조 포함 제한
        elif substructure_violations(mol):
            return False
        # Filter by Lipinski's Rule of 5 : 리피니스 규칙 5 제한
        elif lipinski_filter(mol, max_mol_weight) == False:
            return False
        # Filter by rotatable bonds : 회전가능한 결합 수 제한
        elif rdcmd.CalcNumRotatableBonds(mol) >= 10:
            return False
        else:
            return True
    except FileNotFoundError as e:
        logging.warning(f"unable to filter in apply_filter function: {e}")
        return False


# filter 적용
def apply_filters(mol, max_mol_weight=800):
    """
    분자 필터링 기준 적용 함수

    - 형식 오류, 전하, 라디칼, 브릿지헤드, 고리크기, 인 구조, 금지된 서브구조 체크

    Args:
        smi (str): SMILES 문자열
        max_mol_weight (int): 분자 최대 무게 (기본값: 800)

    Returns:
        True  → 통과 (약물화 가능성 있음)
        False → 탈락
    """
    try:
        """
        if (
            "C-" in smi
            or "N+" in smi
            or "C+" in smi
            or "S+" in smi
            or "S-" in smi
            or "O+" in smi
        ):
            return False

        if ("N" not in smi or "n" not in smi) and ("O" not in smi or "o" not in smi):
            return False
        """

        if mol == None:
            return False
        
        # Added after GDB-13 was filtered to get rid charged molecules : 정전하 있는 분자 제거
        if rdcmo.GetFormalCharge(mol) != 0:
            # print('Formal charge failed! Value: ', rdcmo.GetFormalCharge(mol))
            return False
        # Added after GDB-13 was filtered to get rid radicals : 라디칼 있는 분자 제거
        elif rdcd.NumRadicalElectrons(mol) != 0:
            # print('rdcd.NumRadicalElectrons(mol) failed! Value: ', rdcd.NumRadicalElectrons(mol))
            return False
        # Filter by bridgehead atoms : 브릿지헤드 원자 수 제한
        elif rdcmd.CalcNumBridgeheadAtoms(mol) > 2:
            return False
        # Filter by ring size : 고리크기 제한
        elif maximum_ring_size(mol) > 8:
        # elif maximum_ring_size(mol) > 6:
            return False
        # Filter by proper phosphorus : 비정상적인 인(P) 구조 제한
        elif filter_phosphorus(mol):
            return False
        # Filter by substructure violations : 금지된 서브 구조 포함 제한
        elif substructure_violations(mol):
            return False
        #elif lipinski_filter(mol, max_mol_weight) == False:
        #    return False
        #elif len(FindAromaticRings(mol)) < 1:  # Number of aromatic rings in molecule
        #    return False
        #elif rdcmd.CalcNumRotatableBonds(mol) >= 10:
        #    return False
        else:
            return True
    except:
        print("error")
        return False


#===============================================================================================================

# MCF/PAINS 필터 적용

# DataFrame.append() 가 사라져 append() 대신 pd.concat() 을 사용
_mcf = pd.read_csv(os.path.join('./data/valid-filter/mcf.csv'))
_pains = pd.read_csv(os.path.join('./data/valid-filter/wehi_pains.csv'), names=['smarts', 'names'])
combined_filters_df = pd.concat([_mcf, _pains], ignore_index=True)
# SMARTS 문자열을 RDKit Mol 객체로 변환
_filters = [Chem.MolFromSmarts(x) for x in combined_filters_df['smarts'].values]


def passes_wehi_mcf(mol):
    """
    분자가 MCF/PAINS SMARTS 필터를 통과하는지 확인

    Returns:
        True  → 모든 필터 통과
        False → 하나라도 걸리면 실패
    """
    h_mol = Chem.AddHs(mol)  # 수소 추가
    return not any(h_mol.HasSubstructMatch(smarts) for smarts in _filters)


#===============================================================================================================

# PAINS 필터 적용

inf = open("./data/valid-filter/pains.txt", "r")
sub_strct = [ line.rstrip().split(" ") for line in inf ]
smarts = [ line[0] for line in sub_strct]
desc = [ line[1] for line in sub_strct]
dic = dict(zip(smarts, desc))


def pains_filt(mol):
    """
    분자에 PAINS 필터를 적용하고 매칭된 SMARTS의 이름을 반환
    """
    for k, v in dic.items():  # dic은 SMARTS:이름 매핑 딕셔너리로 가정됨
        subs = Chem.MolFromSmarts(k)
        if subs and mol.HasSubstructMatch(subs):
            mol.SetProp(v, k)  # 분자에 속성으로 태그 설정
    return [prop for prop in mol.GetPropNames()]  # 태깅된 SMARTS 이름 리스트 반환


#===============================================================================================================


def combine_filter(smiles_compound, max_mol_weight: float = 800, filter_fc=apply_filters, disable_tqdm=False):
    """
    전체 필터링 파이프라인

    - apply_filters() 로 기본 필터 적용
    - SYBA/SAScore 기반 합성 가능성
    - WEHI/MCF, PAINS 필터 통과 여부 확인

    Returns:
        pass_all (list): 모든 조건을 통과한 SMILES 리스트
    """
    pass_all = []
    i = 1

    with tqdm(total=len(smiles_compound), file=sys.stdout, miniters=1, disable=disable_tqdm) as pbar:

        for smile_ in smiles_compound:
            pbar.set_description(
                f"Filtered {i} / {len(smiles_compound)}. passed={len(pass_all)}, frac={len(pass_all)/len(smiles_compound):.2f}"
            )

            mol = Chem.MolFromSmiles(smile_)
            if mol is None:
                i += 1
                pbar.update()
                continue  # invalid SMILES는 건너뜀
            try:
                if (
                    filter_fc(smile_, max_mol_weight)
                    and smile_ not in pass_all
                    and (sascorer.calculateScore(mol) < 4)  
                    # and (syba.predict(smile_) > 0)  # SYBA도 사용 가능
                    ### SYBA (SYnthetic BAsibility) -> 설치안됨. 다른 method 이용해야함.-> SAScore 이용: 3이하면 합성 쉬운 분자구조 의미 
                    # # - 머신러닝 기반 분자 평가 모델, 분자의 합성 가능성(synthetic accessibility) 을 예측하는 데 사용
                    and passes_wehi_mcf(mol)
                    and len(pains_filt(mol)) == 0
                ):
                    canon_smile = Chem.MolToSmiles(mol, canonical=True)
                    pass_all.append(canon_smile)
            except Exception as e:
                # print(f"[ERROR] combine_filter 실패 → {e}")
                pass
            i += 1
            pbar.update()

    return pass_all


#===============================================================================================================

def reward_fc(smiles_ls, max_mol_weight: float = 800, filter_fc=legacy_apply_filters):
    """
    분자 리스트에 대해 보상 점수 계산 함수.

    보상 기준 (누적 가산):
    - 기본 필터 통과                  +15
    - MCF/PAINS 통과 (passes_wehi_mcf) +5
    - PAINS 없는 경우                  +5
    - 점수 > 0                    +30

    Returns:
        torch.Tensor: 각 분자에 대한 보상값 텐서
    """
    rewards = []
    for smiles_compound in smiles_ls:
        try:
            reward = 1  # 기본 보상
            mol = Chem.MolFromSmiles(smiles_compound)
            if filter_fc(smiles_compound, max_mol_weight=max_mol_weight):
                reward += 15
            if passes_wehi_mcf(mol):
                reward += 5
            if len(pains_filt(mol)) == 0:
                reward += 5
            # if syba.predict(smiles_compound) > 0:
            if sascorer.calculateScore(mol) < 4:
                reward += 30
            rewards.append(reward)
        except:
            rewards.append(0)  # 오류가 있으면 보상 0

    return torch.Tensor(rewards)


