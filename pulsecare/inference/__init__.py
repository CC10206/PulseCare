"""OpenVINO 推論層——Whisper 轉錄、本地 LLM 回應、本地 TTS。

**只在 server / 閘道器端執行。** KNEO Pi 的 2GB RAM 裝不下這三個模型
（Whisper-small int8 約 250MB + Qwen2.5-1.5B int4 約 1GB +
Qwen3-TTS-0.6B 約 1–1.5GB），A55 的推論速度也不堪用
（Whisper 2–4 分鐘、TTS RTF 30–60×）。

相依對應 `pyproject.toml` 的 `[server]` extra。

`vendor/` 底下是外部 clone 進來的程式碼,不進版控、不要修改
（設置步驟見 docs/tts-setup.md）。
"""
