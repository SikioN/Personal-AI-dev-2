"""
Утилита для определения оптимального устройства для PyTorch
на разных платформах (CUDA/MPS/CPU)
"""
import torch


def get_device(prefer_mps: bool = True, verbose: bool = True) -> str:
    """
    Определяет оптимальное устройство для вычислений PyTorch.
    
    Приоритет:
    1. CUDA (NVIDIA GPU) - если доступно
    2. MPS (Apple Silicon GPU) - если доступно и prefer_mps=True
    3. CPU - fallback
    
    Args:
        prefer_mps: Использовать MPS если доступно (по умолчанию True)
        verbose: Выводить информацию об обнаруженном устройстве
    
    Returns:
        str: Название устройства ('cuda', 'mps' или 'cpu')
    """
    if torch.cuda.is_available():
        device = 'cuda'
        if verbose:
            print(f"✓ Используется CUDA GPU: {torch.cuda.get_device_name(0)}")
    elif prefer_mps and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
        if verbose:
            print("✓ Используется Apple Silicon GPU (MPS)")
    else:
        device = 'cpu'
        if verbose:
            print("✓ Используется CPU (GPU не найден)")
    
    return device


def clear_device_cache(device: str = None) -> None:
    """
    Очищает кэш памяти устройства.
    
    Args:
        device: Тип устройства ('cuda', 'mps', 'cpu' или None для автоопределения)
    """
    if device is None:
        device = get_device(verbose=False)
    
    if device == 'cuda' and torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif device == 'mps' and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        torch.mps.empty_cache()
    # CPU не требует очистки кэша
