import csv
import os

import numpy as np
from rdkit.Chem import AllChem as Chem
from rdkit.Chem import MolFromSmiles, MolToSmiles


def read_smi(filename):
    """ SMILES 형식의 .smi 파일에서 데이터를 읽어오는 함수

    매개변수:
    - filename (str): .smi 파일의 경로

    반환값:
    - smiles (list of str): 파일에서 읽어온 SMILES 문자열 목록

    """
    # .smi 파일을 읽어와서 문자열 목록으로 변환
    with open(filename) as file:
        smiles = file.readlines()
    # 각 문자열에서 줄바꿈 문자 제거 - 각 줄의 앞뒤 공백 제거
    smiles = [i.strip() for i in smiles]
    return smiles


def read_smiles_csv(filename):
    """ CSV 파일에서 SMILES 데이터를 읽어오는 함수

    매개변수:
    - filename (str): .csv 파일의 경로

    반환값:
    - data (list of str): CSV 파일에서 'smiles' 컬럼에 있는 모든 SMILES 문자열 목록

    """
    # 파일 열기 및 csv.reader 사용하여 읽기
    with open(filename) as file:
        reader = csv.reader(file)
        # 헤더에서 'smiles' 컬럼의 인덱스를 찾음
        smiles_idx = next(reader).index("smiles")
        # 각 행에서 해당 컬럼의 데이터를 추출하여 리스트로 반환
        data = [row[smiles_idx] for row in reader]
    return data


def load_train_data(filename):
    """ .csv 또는 .smi 파일에서 학습 데이터를 로드하는 함수

    매개변수:
    - filename (str): .csv 또는 .smi 파일의 경로

    반환값:
    - smiles (list of str): 파일에서 읽어온 SMILES 문자열 목록

    예외:
    - ValueError: 지원되지 않는 파일 형식의 경우 (예: .txt)

    """
    # 파일 확장자 확인
    ext = filename.split(".")[-1]
    # 파일 확장자에 따라 다른 읽기 함수 호출
    if ext == "csv":
        return read_smiles_csv(filename)
    if ext == "smi":
        return read_smi(filename)
    else:
        raise ValueError("data is not smi or csv!")
    return


def save_smi(name, smiles):
    """ SMILES 데이터를 .smi 형식으로 저장하는 함수

    매개변수:
    - name (str): 저장할 파일 이름 (확장자 제외)
    - smiles (list of str): 저장할 SMILES 문자열 목록

    반환값:
    - 없음

    """
    # 파일 저장 경로 확인 및 'epoch_data' 폴더가 없으면 생성 생성
    if not os.path.exists("epoch_data"):
        os.makedirs("epoch_data")
    # 파일 저장 경로 생성
    smi_file = os.path.join("epoch_data", "{}.smi".format(name))
    # SMILES 데이터를 파일에 저장
    with open(smi_file, "w") as afile:
        afile.write("\n".join(smiles))
    return


""" MATHEMATICAL UTILITIES """


def checkarray(x):
    """ 입력 데이터가 다수의 요소를 가진 리스트 또는 numpy 배열인지 확인하는 함수

    매개변수:
    - x (list or np.ndarray): 입력 데이터

    반환값:
    - bool: 다수의 요소를 가진 경우 True, 그렇지 않으면 False

    """
    # 입력이 numpy 배열 또는 리스트이고, 요소가 2개 이상인 경우 True 반환
    if type(x) == np.ndarray or type(x) == list:
        if x.size == 1:
            return False
        else:
            return True
    else:
        return False


def gauss_remap(x, x_mean, x_std):
    """ 주어진 값을 가우시안 분포로 리매핑하는 함수

    매개변수:
    - x (float): 리매핑할 값
    - x_mean (float): 가우시안 분포의 평균
    - x_std (float): 가우시안 분포의 표준편차

    반환값:
    - float: 가우시안 분포에 따른 리매핑된 값

    """
    # 가우시안 분포 함수 적용하여 리맵핑
    return np.exp(-((x - x_mean) ** 2) / (x_std**2))


def remap(x, x_min, x_max):
    """주어진 값을 [0, 1] 범위로 리매핑하는 함수

    매개변수:
    - x (float): 리매핑할 값
    - x_min (float): 입력 값의 최소 범위
    - x_max (float): 입력 값의 최대 범위

    반환값:
    - float: [0, 1] 범위로 리매핑된 값

    참고:
    - x가 x_max보다 크거나 x_min보다 작으면 [0, 1] 범위를 벗어남

    """
    if x_max - x_min == 0:
        return 0  # 최대값과 최소값이 같으면 0 반환
    else:
        return (x - x_min) / (x_max - x_min)


def constant_range(x, x_low, x_high):
    """ 입력이 주어진 범위 내에 있는지 확인하는 함수 (배열 지원)

    매개변수:
    - x (float or list or np.ndarray): 입력 값 또는 값의 배열
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한

    반환값:
    - np.ndarray 또는 float: 범위 내에 있으면 1, 범위를 벗어나면 0

    """
    if checkarray(x):
        return np.array([constant_range_func(xi, x_low, x_high) for xi in x])
    else:
        return constant_range_func(x, x_low, x_high)


def constant_range_func(x, x_low, x_high):
    """ 범위 내의 값을 1, 범위 밖의 값을 0으로 반환하는 함수

    매개변수:
    - x (float): 입력 값
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한

    반환값:
    - int: 범위 내에 있으면 1, 범위를 벗어나면 0

    """
    if x <= x_low or x >= x_high:
        return 0
    else:
        return 1


def constant_bump_func(x, x_low, x_high, decay=0.025):
    """ 범위 외부에서 점진적으로 감소하는 함수

    매개변수:
    - x (float): 입력 값
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한
    - decay (float, 기본값=0.025): 범위 외부에서의 감쇠 정도

    반환값:
    - float: 범위 내에서 1, 범위 외부에서 지수 감소 값

    """
    if x <= x_low:
        return np.exp(-((x - x_low) ** 2) / decay)
    elif x >= x_high:
        return np.exp(-((x - x_high) ** 2) / decay)
    else:
        return 1


def constant_bump(x, x_low, x_high, decay=0.025):
    """ 배열 입력에 대한 범위 외부 감소 함수 적용

    매개변수:
    - x (float or list or np.ndarray): 입력 값 또는 값의 배열
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한
    - decay (float, 기본값=0.025): 감쇠 정도

    반환값:
    - np.ndarray 또는 float: 각 입력값에 대한 범위 외부 감소 함수 결과

    """
    if checkarray(x):
        return np.array([constant_bump_func(xi, x_low, x_high, decay) for xi in x])
    else:
        return constant_bump_func(x, x_low, x_high, decay)


def smooth_plateau(x, x_point, decay=0.025, increase=True):
    """ 배열 입력에 대한 부드러운 고원 함수 적용

    매개변수:
    - x (float or list or np.ndarray): 입력 값 또는 값의 배열
    - x_point (float): 고원의 기준점
    - decay (float, 기본값=0.025): 감쇠 정도
    - increase (bool): 증가/감소 방향 설정

    반환값:
    - np.ndarray 또는 float: 각 입력값에 대한 부드러운 고원 함수 결과

    """
    if checkarray(x):
        return np.array([smooth_plateau_func(xi, x_point, decay, increase) for xi in x])
    else:
        return smooth_plateau_func(x, x_point, decay, increase)


def smooth_plateau_func(x, x_point, decay=0.025, increase=True):
    """ 부드러운 고원 함수

    매개변수:
    - x (float): 입력 값
    - x_point (float): 고원의 기준점
    - decay (float, 기본값=0.025): 감쇠 정도
    - increase (bool): 증가/감소 방향 설정

    반환값:
    - float: 부드러운 고원 함수 결과

    """
    if increase:
        if x <= x_point:
            return np.exp(-((x - x_point) ** 2) / decay)
        else:
            return 1
    else:
        if x >= x_point:
            return np.exp(-((x - x_point) ** 2) / decay)
        else:
            return 1


def pct(a, b):
    """ 두 리스트의 길이 비율을 계산하는 함수

    매개변수:
    - a (list): 첫 번째 리스트
    - b (list): 두 번째 리스트

    반환값:
    - float: a의 길이 / b의 길이 (b가 비어있으면 0 반환)

    """
    if len(b) == 0:
        return 0
    return float(len(a)) / len(b)


def rectification(x, x_low, x_high, reverse=False):
    """ 배열 입력에 대한 정류 함수 적용

    매개변수:
    - x (float or list or np.ndarray): 입력 값 또는 값의 배열
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한
    - reverse (bool): 정류 방향 반전 여부

    반환값:
    - np.ndarray 또는 float: 각 입력값에 대한 정류 함수 결과

    """
    if checkarray(x):
        return np.array([rec_fun(xi, x_low, x_high, reverse) for xi in x])
    else:
        return rec_fun(x, x_low, x_high, reverse)


def rec_fun(x, x_low, x_high, reverse=False):
    """ 정류 함수

    매개변수:
    - x (float): 입력 값
    - x_low (float): 범위의 하한
    - x_high (float): 범위의 상한
    - reverse (bool): 정류 방향 반전 여부

    반환값:
    - float: 정류된 값

    """
    if reverse == True:
        if x_low <= x <= x_high:
            return 0
        else:
            return x
    else:
        if x_low <= x <= x_high:
            return x
        else:
            return 0


def asym_rectification(x, y, reverse=False):
    """ 배열 입력에 대한 비대칭 정류 함수 적용

    매개변수:
    - x (float or list or np.ndarray): 입력 값 또는 값의 배열
    - y (float): 기준값
    - reverse (bool): 정류 방향 반전 여부

    반환값:
    - np.ndarray 또는 float: 각 입력값에 대한 비대칭 정류 함수 결과

    """
    if checkarray(x):
        return np.array([asymrec_fun(xi, y, reverse=reverse) for xi in x])
    else:
        return asymrec_fun(x, y, reverse=reverse)


def asymrec_fun(x, y, reverse=False):
    """ 비대칭 정류 함수

    매개변수:
    - x (float): 입력 값
    - y (float): 기준값
    - reverse (bool): 정류 방향 반전 여부

    반환값:
    - float: 비대칭 정류된 값

    """
    if reverse == True:
        if x < y:
            return x
        else:
            return 0
    else:
        if x < y:
            return 0
        else:
            return x


"""Encoding/decoding utilities"""


def canon_smile(smile):
    """ SMILES 문자열을 표준 형식으로 변환하는 함수

    매개변수:
    - smile (str): 변환할 SMILES 문자열

    반환값:
    - str: 표준화된 SMILES 문자열

    """
    return MolToSmiles(MolFromSmiles(smile))


def verified_and_below(smile, max_len):
    """ SMILES 문자열이 유효하고 최대 길이 이하인지 확인하는 함수

    매개변수:
    - smile (str): 확인할 SMILES 문자열
    - max_len (int): 최대 허용 길이

    반환값:
    - bool: 유효하고 최대 길이 이하이면 True, 아니면 False

    """
    return len(smile) < max_len and verify_sequence(smile)


def verify_sequence(smile):
    """ SMILES 문자열이 유효한지 확인하는 함수

    매개변수:
    - smile (str): 확인할 SMILES 문자열

    반환값:
    - bool: 유효한 SMILES 문자열이면 True, 아니면 False

    """
    mol = Chem.MolFromSmiles(smile)
    return smile != "" and mol is not None and mol.GetNumAtoms() > 1


def apply_to_valid(smile, fun, **kwargs):
    """ 유효한 SMILES 문자열에 함수를 적용하는 함수

    매개변수:
    - smile (str): SMILES 문자열
    - fun (function): 적용할 함수
    - **kwargs: 함수에 전달할 추가 인자들

    반환값:
    - float: 유효한 SMILES 문자열이면 함수 결과, 아니면 0.0

    """
    mol = Chem.MolFromSmiles(smile)
    return (
        fun(mol, **kwargs)
        if smile != "" and mol is not None and mol.GetNumAtoms() > 1
        else 0.0
    )


def filter_smiles(smiles):
    """ 유효한 SMILES 문자열만 필터링하는 함수

    매개변수:
    - smiles (list of str): SMILES 문자열 목록

    반환값:
    - list of str: 유효한 SMILES 문자열만 포함된 목록

    """
    return [smile for smile in smiles if verify_sequence(smile)]


def build_vocab(smiles, pad_char="_", start_char="^"):
    """ SMILES 문자열 목록으로부터 어휘 사전을 구축하는 함수

    매개변수:
    - smiles (list of str): SMILES 문자열 목록
    - pad_char (str, 기본값="_"): 패딩 문자
    - start_char (str, 기본값="^"): 시작 문자

    반환값:
    - tuple: (char_dict, ord_dict)
        - char_dict: 문자를 숫자로 매핑하는 사전
        - ord_dict: 숫자를 문자로 매핑하는 사전

    """
    i = 1
    char_dict, ord_dict = {start_char: 0}, {0: start_char}
    for smile in smiles:
        for c in smile:
            if c not in char_dict:
                char_dict[c] = i
                ord_dict[i] = c
                i += 1
    char_dict[pad_char], ord_dict[i] = i, pad_char
    return char_dict, ord_dict


def pad(smile, n, pad_char="_"):
    """ SMILES 문자열을 주어진 길이로 패딩하는 함수

    매개변수:
    - smile (str): 패딩할 SMILES 문자열
    - n (int): 목표 길이
    - pad_char (str, 기본값="_"): 패딩 문자

    반환값:
    - str: 패딩된 SMILES 문자열

    """
    if n < len(smile):
        return smile
    return smile + pad_char * (n - len(smile))


def unpad(smile, pad_char="_"):
    """ SMILES 문자열에서 패딩을 제거하는 함수

    매개변수:
    - smile (str): 패딩을 제거할 SMILES 문자열
    - pad_char (str, 기본값="_"): 패딩 문자

    반환값:
    - str: 패딩이 제거된 SMILES 문자열

    """
    return smile.rstrip(pad_char)


def encode(smile, max_len, char_dict):
    """ SMILES 문자열을 숫자 시퀀스로 인코딩하는 함수

    매개변수:
    - smile (str): 인코딩할 SMILES 문자열
    - max_len (int): 최대 길이
    - char_dict (dict): 문자-숫자 매핑 사전

    반환값:
    - list of int: 인코딩된 숫자 시퀀스

    """
    return [char_dict[c] for c in pad(smile, max_len)]


def decode(ords, ord_dict):
    """ 숫자 시퀀스를 SMILES 문자열로 디코딩하는 함수

    매개변수:
    - ords (list of int): 디코딩할 숫자 시퀀스
    - ord_dict (dict): 숫자-문자 매핑 사전

    반환값:
    - str: 디코딩된 SMILES 문자열

    """
    return unpad("".join([ord_dict[o] for o in ords]))


def compute_results(model_samples, train_data, ord_dict, results={}, verbose=True):
    """ 모델 샘플링 결과를 계산하고 저장하는 함수

    매개변수:
    - model_samples (list): 모델이 생성한 샘플들
    - train_data (list): 학습 데이터
    - ord_dict (dict): 숫자-문자 매핑 사전
    - results (dict, 기본값={}): 결과를 저장할 사전
    - verbose (bool, 기본값=True): 상세 출력 여부

    반환값:
    - 없음

    """
    samples = [decode(s, ord_dict) for s in model_samples]
    results["mean_length"] = np.mean([len(sample) for sample in samples])
    results["n_samples"] = len(samples)
    results["uniq_samples"] = len(set(samples))
    verified_samples = []
    unverified_samples = []
    for sample in samples:
        if verify_sequence(sample):
            verified_samples.append(sample)
        else:
            unverified_samples.append(sample)
    results["good_samples"] = len(verified_samples)
    results["bad_samples"] = len(unverified_samples)
    # save smiles
    if "Batch" in results.keys():
        smi_name = "{}_{}".format(results["exp_name"], results["Batch"])
        save_smi(smi_name, samples)
        results["model_samples"] = smi_name
    if verbose:
        print_results(verified_samples, unverified_samples, results)
    return


def print_results(verified_samples, unverified_samples, results={}):
    """ 모델 샘플링 결과를 출력하는 함수

    매개변수:
    - verified_samples (list): 검증된 샘플들
    - unverified_samples (list): 검증되지 않은 샘플들
    - results (dict, 기본값={}): 결과 사전

    반환값:
    - 없음

    """
    print("Summary of the epoch")
    print("~~~~~~~~~~~~~~~~~~~~~~~~\n")
    print("{:15s} : {:6d}".format("Total samples", results["n_samples"]))
    percent = results["uniq_samples"] / float(results["n_samples"]) * 100
    print(
        "{:15s} : {:6d} ({:2.2f}%)".format("Unique", results["uniq_samples"], percent)
    )
    percent = results["bad_samples"] / float(results["n_samples"]) * 100
    print(
        "{:15s} : {:6d} ({:2.2f}%)".format(
            "Unverified", results["bad_samples"], percent
        )
    )
    percent = results["good_samples"] / float(results["n_samples"]) * 100
    print(
        "{:15s} : {:6d} ({:2.2f}%)".format("Verified", results["good_samples"], percent)
    )

    print("\nSome good samples:")
    print("~~~~~~~~~~~~~~~~~~~~~~~~\n")
    if len(verified_samples) > 10:
        for s in verified_samples[0:10]:
            print("" + s)
    else:
        print("No good samples were found :(...")

    print("\nSome bad samples:")
    print("~~~~~~~~~~~~~~~~~~~~~~~~\n")
    if len(unverified_samples) > 10:
        for s in unverified_samples[0:10]:
            print("" + s)
    else:
        print("No bad samples were found :D!")

    return
