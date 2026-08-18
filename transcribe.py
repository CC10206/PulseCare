"""
PulseCare — 本地端語音轉錄 (OpenVINO GenAI)

隱私核心：Whisper 完全跑在 Intel 裝置本地，原始音檔不上傳雲端。
"""
import librosa

_pipe = None


def get_pipeline(model_dir: str = "models/whisper-small-int8", device: str = "CPU"):
    """延遲載入 —— 模型載入約需數秒，不要在每次呼叫時重建。
    device 可為 "CPU" / "GPU" / "NPU"。Core Ultra 可試 "NPU"。"""
    global _pipe
    if _pipe is None:
        import openvino_genai
        _pipe = openvino_genai.WhisperPipeline(model_dir, device)
    return _pipe


def transcribe(wav_path: str, model_dir: str = "models/whisper-small-int8",
               device: str = "CPU", language: str = "<|zh|>") -> dict:
    """回傳 {"text": str, "segments": [(start, end, text), ...]}

    注意：OpenVINO GenAI 的 return_timestamps 給的是「片段級」時間戳
    (一個片段可能含多個詞)，不是詞級。所以語速不從這裡算 ——
    語速改用 features.py 的 loudnessPeaksPerSec，語言無關且更穩健。
    片段時間戳在這裡只用於 Demo 畫面上的逐字稿對齊。
    """
    pipe = get_pipeline(model_dir, device)
    raw = librosa.load(wav_path, sr=16000, mono=True)[0].tolist()
    result = pipe.generate(
        raw,
        language=language,       # 台語可改 "<|zh|>" 或省略讓它自動偵測
        task="transcribe",
        return_timestamps=True,
        max_new_tokens=200,
    )
    segments = [(c.start_ts, c.end_ts, c.text) for c in (result.chunks or [])]
    return {"text": str(result), "segments": segments}


if __name__ == "__main__":
    import sys, json
    out = transcribe(sys.argv[1])
    print(json.dumps(out, indent=2, ensure_ascii=False))
