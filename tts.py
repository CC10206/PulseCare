"""
PulseCare — 本地文字轉語音 (Qwen3-TTS via OpenVINO)

隱私核心：跟 transcribe.py / llm_reply.py 一樣完全跑在本地，不上傳雲端。

前置設置（可行性驗證與逐步指令見 docs/tts-setup.md）：
1. 在專案根目錄 clone Qwen3-TTS 原始碼到 `Qwen3-TTS/`，並把
   `qwen_3_tts_helper.py` 放在專案根目錄。
2. 依 docs/tts-setup.md 的轉檔指令，把模型轉出到
   `models/qwen3-tts-0.6b-customvoice-ov/`。
這兩者體積大、也不是我們自己的程式碼，所以不進版控 (見 .gitignore)。
"""

_model = None

DEFAULT_MODEL_DIR = "models/qwen3-tts-0.6b-customvoice-ov"
DEFAULT_SPEAKER = "aiden"


def get_model(model_dir: str = DEFAULT_MODEL_DIR, device: str = "CPU"):
    """延遲載入 —— 模型載入需要時間，不要在每次呼叫時重建 (同 transcribe.py 的作法)。"""
    global _model
    if _model is None:
        try:
            from qwen_3_tts_helper import OVQwen3TTSModel
        except ImportError as e:
            raise RuntimeError(
                "找不到 qwen_3_tts_helper.py / Qwen3-TTS。"
                "請先依 docs/tts-setup.md 的步驟設置 TTS 環境。"
            ) from e
        from pathlib import Path
        _model = OVQwen3TTSModel.from_pretrained(model_dir=Path(model_dir), device=device)
    return _model


def speak(text: str, out_path: str | None = None, model_dir: str = DEFAULT_MODEL_DIR,
          device: str = "CPU", speaker: str = DEFAULT_SPEAKER, play: bool = False):
    """把文字合成語音。out_path 給了才存檔；play=True 會立即從喇叭播放。
    回傳 (audio: numpy array, sample_rate: int)。"""
    model = get_model(model_dir, device)
    wavs, sr = model.generate_custom_voice(
        text=text, speaker=speaker, language="auto", instruct=None, max_new_tokens=4096,
    )
    audio = wavs[0]

    if out_path:
        import soundfile as sf
        sf.write(out_path, audio, sr)

    if play:
        import sounddevice as sd
        sd.play(audio, sr)
        sd.wait()

    return audio, sr


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "李奶奶早！今天陽光很好，昨晚睡得好嗎？"
    out = sys.argv[2] if len(sys.argv) > 2 else "tts_out.wav"
    speak(text, out, play=True)
    print(f"已合成並播放 → {out}")
