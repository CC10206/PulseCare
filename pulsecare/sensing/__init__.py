"""邊緣感測層——這一層的所有程式碼都必須能在 KNEO Pi（4× Cortex-A55、
2GB RAM、aarch64）上跑。

**相依約束（由 test_no_heavy_deps.py 把關）：**

不得 import `openvino`、`openvino_genai`、`librosa`、`parselmouth`、
`transformers`。理由：

- OpenVINO 在這一層沒有用途（特徵抽取是純 DSP,沒有神經網路）
- `praat-parselmouth` 沒有 aarch64 wheel
- `librosa` 會拖進 numba/llvmlite,而它在此處只被用來算音檔長度

允許的相依對應 `pyproject.toml` 的 `[sensing]` extra，
在板子上以 `pip install -e .[sensing]` 安裝。

隱私責任：原始音訊在特徵抽取完成後由呼叫端立即銷毀，永不離開本裝置。
"""
