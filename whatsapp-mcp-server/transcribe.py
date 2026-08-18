"""Local audio transcription using faster-whisper, GPU-accelerated when available."""
import os
import sys
from functools import lru_cache

MODEL_SIZE = "small"  # good accuracy/speed tradeoff for pt-BR voice messages


def _register_cuda_dll_dirs():
    """faster-whisper's CUDA backend (ctranslate2) needs cuBLAS/cuDNN, which
    we install as pip packages rather than a full CUDA Toolkit. Windows only
    searches PATH for DLLs by default, so point it at the pip-installed
    copies explicitly."""
    if os.name != "nt":
        return
    try:
        import nvidia
        # nvidia.* are namespace packages (no __init__.py, no __file__), so
        # resolve the bin dirs via the namespace package's search path instead.
        # Register every pip-installed nvidia-*-cu12 package's bin dir (cublas,
        # cudnn, cuda_runtime, nvjitlink, ...) since they depend on each other.
        for nvidia_dir in nvidia.__path__:
            for subpkg in os.listdir(nvidia_dir):
                bin_dir = os.path.join(nvidia_dir, subpkg, "bin")
                if os.path.isdir(bin_dir):
                    os.add_dll_directory(bin_dir)
                    # ctranslate2's own DLL loader doesn't honor
                    # os.add_dll_directory on Windows - it needs these on PATH.
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
    except ImportError:
        pass


_register_cuda_dll_dirs()


@lru_cache(maxsize=1)
def _load_model():
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
    except Exception as e:
        print(f"GPU unavailable ({e}), falling back to CPU", file=sys.stderr)
        return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio_path: str) -> str:
    """Transcribe an audio file (any format ffmpeg can decode) to text."""
    model = _load_model()
    segments, info = model.transcribe(audio_path, language=None, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python transcribe.py <audio_path>", file=sys.stderr)
        sys.exit(1)
    print(transcribe(sys.argv[1]))
