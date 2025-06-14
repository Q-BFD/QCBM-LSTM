"""
GPU-accelerated tensor operations for SELFIES encoding.
(RDKit/SELFIES operations remain on CPU due to library limitations)
"""
import torch
import numpy as np
from typing import List

def gpu_accelerated_padding(selfies_list: List[str], max_length: int, pad_char: str = "[nop]") -> List[str]:
    """
    GPU 가속을 활용한 패딩 (실제로는 제한적 효과)
    
    Note: 문자열 연산은 GPU에서 불가능하므로 CPU에서 처리
    """
    # 실제로는 문자열 패딩은 CPU에서만 가능
    padded_selfies = []
    for selfie in selfies_list:
        # 패딩 계산은 CPU에서
        n_padding = max_length - len(selfie.split(']')) + 1
        padded = selfie + pad_char * n_padding
        padded_selfies.append(padded)
    
    return padded_selfies


def gpu_accelerated_tensor_creation(encoded_samples: np.ndarray) -> torch.Tensor:
    """
    GPU에서 텐서 생성 및 변환
    
    Args:
        encoded_samples: NumPy 배열
        
    Returns:
        GPU 텐서 (CUDA 사용 가능시)
    """
    if torch.cuda.is_available():
        print("✅ GPU 가속 텐서 변환 활성화")
        # CPU에서 생성 후 GPU로 이동
        tensor = torch.tensor(encoded_samples, dtype=torch.float32)
        return tensor.cuda()
    else:
        print("❌ GPU 없음, CPU 텐서 사용")
        return torch.tensor(encoded_samples, dtype=torch.float32)


def gpu_batch_processing(data_chunks: List[np.ndarray]) -> torch.Tensor:
    """
    배치별 GPU 처리
    
    Args:
        data_chunks: 데이터 청크 리스트
        
    Returns:
        병합된 GPU 텐서
    """
    if not torch.cuda.is_available():
        # GPU 없으면 CPU 처리
        return torch.cat([torch.tensor(chunk, dtype=torch.float32) for chunk in data_chunks])
    
    print(f"🚀 {len(data_chunks)}개 청크를 GPU에서 처리 중...")
    
    gpu_tensors = []
    for i, chunk in enumerate(data_chunks):
        # 각 청크를 GPU로 이동
        tensor = torch.tensor(chunk, dtype=torch.float32).cuda()
        gpu_tensors.append(tensor)
        
        if (i + 1) % 10 == 0:
            print(f"   청크 {i+1}/{len(data_chunks)} GPU 처리 완료")
    
    # GPU에서 병합
    result = torch.cat(gpu_tensors)
    print(f"✅ GPU 배치 처리 완료: {result.shape}")
    
    return result


def hybrid_encoding_pipeline(selfies_list: List[str], char_to_index: dict, max_length: int) -> torch.Tensor:
    """
    하이브리드 인코딩 파이프라인 (CPU + GPU)
    
    Args:
        selfies_list: SELFIES 문자열 리스트
        char_to_index: 문자-인덱스 매핑
        max_length: 최대 길이
        
    Returns:
        최종 GPU 텐서
    """
    print("🔄 하이브리드 인코딩 파이프라인 시작...")
    
    # 1. CPU에서 문자열 처리 (불가피)
    print("📝 CPU에서 문자열 처리 중...")
    import selfies as sf
    
    encoded_samples = []
    for selfie in selfies_list:
        # 패딩 적용
        n_padding = max_length - sf.len_selfies(selfie)
        padded = selfie + "[nop]" * n_padding
        
        # 숫자 인코딩
        encoded = sf.selfies_to_encoding(padded, char_to_index, enc_type="label")
        encoded_samples.append(encoded)
    
    # 2. GPU에서 텐서 변환
    print("⚡ GPU에서 텐서 변환 중...")
    numpy_array = np.array(encoded_samples)
    gpu_tensor = gpu_accelerated_tensor_creation(numpy_array)
    
    print(f"✅ 하이브리드 처리 완료: {gpu_tensor.shape}")
    return gpu_tensor


# 실제 성능 벤치마크
def benchmark_gpu_vs_cpu(sample_size: int = 1000):
    """
    GPU vs CPU 성능 비교
    """
    import time
    
    print(f"🏁 GPU vs CPU 벤치마크 ({sample_size}개 샘플)")
    
    # 테스트 데이터 생성
    test_data = np.random.randint(0, 58, (sample_size, 777))
    
    # CPU 텐서 변환
    start = time.time()
    cpu_tensor = torch.tensor(test_data, dtype=torch.float32)
    cpu_time = time.time() - start
    
    # GPU 텐서 변환 (가능한 경우)
    if torch.cuda.is_available():
        start = time.time()
        gpu_tensor = torch.tensor(test_data, dtype=torch.float32).cuda()
        gpu_time = time.time() - start
        
        speedup = cpu_time / gpu_time
        print(f"📊 결과:")
        print(f"   CPU: {cpu_time:.4f}초")
        print(f"   GPU: {gpu_time:.4f}초")
        print(f"   가속: {speedup:.1f}배")
        
        return speedup
    else:
        print("❌ GPU 없음 - 벤치마크 불가")
        return 1.0


if __name__ == "__main__":
    # GPU 사용 가능 여부 확인
    print("🔍 GPU 환경 확인:")
    print(f"   CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU 이름: {torch.cuda.get_device_name(0)}")
        print(f"   GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    # 성능 벤치마크
    benchmark_gpu_vs_cpu() 