# TTS 設置與可行性驗證記錄（Qwen3-TTS via OpenVINO）

## 結論

**GO。** `Qwen3-TTS-12Hz-0.6B-CustomVoice` 經 OpenVINO 轉換後，能在 CPU 上合成
可用的中文語音，且跟 `llm_reply.py` 選用的 Qwen2.5 是同一個模型家族。

- 轉檔：218 秒，全部步驟成功，無錯誤。
- 語言：模型明確支援 `chinese`（`get_supported_languages()` 完整列表：
  `auto/chinese/english/french/german/italian/japanese/korean/portuguese/russian/spanish`），
  `language="auto"` 能正確自動偵測中文輸入。
- 實測合成句子「李奶奶早！今天陽光很好，昨晚睡得好嗎？」→ 24kHz、4.30 秒、206KB 的 wav。
- 速度：載入模型 13.2 秒，推論 32.2 秒生出 4.3 秒音訊（RTF ≈ 7.5×，CPU，未裝 `flash-attn`）。
  拍預錄影片綽綽有餘（跑起來剪掉等待時間即可），但目前速度不適合做即時來回對話。

此文件把可行性驗證時實際用過、跑得通的指令完整記下來——這是本專案第一次踩進
「沒有 `optimum-cli` 一行指令可以搞定」的轉檔流程，跟 Whisper/Qwen2.5 那種標準
匯出流程不一樣，比較容易在下次重建環境時忘記細節，所以特別寫成文件而不是只留
在暫存目錄。

---

## Step 1｜Clone Qwen3-TTS 原始碼

`qwen_3_tts_helper.py`（見下一步）會在自己所在目錄找一個 `Qwen3-TTS` 子目錄，
所以要 clone 到 helper 檔案旁邊：

```bash
git clone https://github.com/QwenLM/Qwen3-TTS.git
cd Qwen3-TTS
git checkout 1ab0dd75353392f28a0d05d9ca960c9954b13c83
cd ..
```

⚠️ 一定要完整 clone，**不能用 `--depth 1`**——shallow clone 沒辦法 checkout 這個
指定 commit（這是 `openvino_notebooks` 的 helper 實際驗證過的版本，不是隨便挑的）。

## Step 2｜建立獨立 venv 並安裝套件

跟 Whisper 轉檔一樣，建議用獨立的 venv，避免跟推論環境的相依衝突：

```bash
python -m venv .venv

./.venv/Scripts/python.exe -m pip install -q \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  torch==2.8.0 nncf torchaudio==2.8.0 "openvino>=2025.4.0" huggingface_hub

cd Qwen3-TTS
../.venv/Scripts/python.exe -m pip install -q -e . --no-deps
cd ..

./.venv/Scripts/python.exe -m pip install -q \
  "transformers==4.57.3" "accelerate==1.12.0" librosa soundfile sox onnxruntime einops

curl -o qwen_3_tts_helper.py \
  https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/notebooks/qwen3-tts/qwen_3_tts_helper.py
```

`-e . --no-deps` 是刻意的：不加 `--no-deps` 的話，pip 的 resolver 會跟前面已經
釘死版本的 `torch`/`torchaudio` 打架。後面那行的套件清單是
`Qwen3-TTS/pyproject.toml` 宣告的依賴，扣掉 `gradio`（demo UI 用，這裡不需要，
會有一則無害的警告 `qwen-tts 0.1.1 requires gradio, which is not installed`）。

## Step 3｜轉換模型到 OpenVINO IR

```python
# convert.py
from pathlib import Path
from qwen_3_tts_helper import convert_qwen3_tts_model

convert_qwen3_tts_model(
    model_id="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    output_dir=Path("Qwen3-TTS-CustomVoice-0.6B-OV"),
    quantization_config=None,
)
```

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe convert.py
```

轉出的 IR 檔案會在 `Qwen3-TTS-CustomVoice-0.6B-OV/`（talker embedding/language/
code-predictor 模型 + 一個 `speech_tokenizer/` 子目錄放 encoder/decoder IR）。
這台機器上耗時 218 秒。

## Step 4｜推論測試

```python
# infer.py
from pathlib import Path
import soundfile as sf
from qwen_3_tts_helper import OVQwen3TTSModel

model = OVQwen3TTSModel.from_pretrained(
    model_dir=Path("Qwen3-TTS-CustomVoice-0.6B-OV"), device="CPU"
)

# model.get_supported_speakers()  -> ['aiden','dylan','eric','ono_anna','ryan',
#                                     'serena','sohee','uncle_fu','vivian']
# model.get_supported_languages() -> ['auto','chinese','english','french','german',
#                                     'italian','japanese','korean','portuguese',
#                                     'russian','spanish']

wavs, sr = model.generate_custom_voice(
    text="李奶奶早！今天陽光很好，昨晚睡得好嗎？",
    speaker="aiden",      # 實測用這個；其餘 8 個 id 有效但未測試音色
    language="auto",      # 正確自動偵測成中文；"chinese" 也在清單裡但沒單獨測過
    instruct=None,
    max_new_tokens=4096,
)
sf.write("greeting_zh.wav", wavs[0], sr)
```

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe infer.py
```

結果：`greeting_zh.wav`，24000Hz、4.30 秒、206294 bytes。載入 13.2 秒，
推論 32.2 秒（RTF ≈ 7.5×）。

---

## 已知問題 / 待驗證事項

- **UTF-8 crash（第一次跑一定會踩到的坑）：** `qwen_3_tts_helper.py` 在 import
  時就會 `print()` emoji（✅⚠️⌛）。Windows 主控台若是 cp950/Big5 code page，
  這會是沒被接住的 `UnicodeEncodeError`，直接讓整個程序在做任何事之前就掛掉。
  **修法：一律加上 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 再執行。**
- `sox` 這個 Python 套件在 import 時會印出「SoX could not be found!」（系統缺
  SoX 執行檔），是非致命警告——轉檔跟推論都順利跑完了。但沒驗證過其他路徑
  （例如聲音克隆、resample）是不是真的需要那支 SoX 執行檔。
- 沒裝 `flash-attn`，所以退回較慢的手動 PyTorch attention 路徑（有印警告）。
  這可能是實測 RTF (~7.5×) 比 `openvino_notebooks` README 標示的 ~2.7×（1.7B
  模型、英文）差的原因。在 Windows 上裝 `flash-attn` 通常要對到 CUDA toolkit
  版本 + build tools，本次沒有嘗試，先記錄成之後可能的加速手段。
- **`torchaudio` 一定要跟 `torch` 版本對齊**（後來把這套東西併進專案主 venv、
  跟 Phase 1/2 其他相依裝在一起時才踩到）：如果 `torch==2.8.0` 裝好後，
  `torchaudio` 沒有明確釘住版本，pip 可能會解析出不匹配的版本（實測遇過
  `torchaudio 2.11.0`），載入時會是 `OSError: [WinError 127] 找不到指定的
  程序`（原生擴充庫 ABI 不匹配）。**修法：明確裝
  `torchaudio==2.8.0`（同一個 `--extra-index-url .../whl/cpu`）。**
  requirements.txt 已經把這個版本釘死。
- 除了 Step 2 那份 pip 清單，`Qwen3-TTS` 的 import chain 實際上還需要
  `onnxruntime`、`einops`、`accelerate`（跑進 `speech_vq.py` 才會炸
  `ModuleNotFoundError`，不會在裝套件當下就報錯，容易漏裝）。requirements.txt
  已經補上。
- 把 `Qwen3-TTS/` clone 進專案根目錄後，裸執行 `pytest` 會連
  `Qwen3-TTS/examples/test_*.py` 一起收集，炸 `ModuleNotFoundError: qwen_tts`
  （那是它自己的測試，不是我們的）。已加 `pytest.ini` 的
  `norecursedirs = Qwen3-TTS .venv models` 排除掉。

## 對整合進 `tts.py` 的建議

跟 `transcribe.py`／`llm_reply.py` 一樣採用「延遲載入單例」寫法
（`get_pipeline()` 第一次呼叫才載入模型），對外只暴露一個
`speak(text: str, out_path: str) -> None` 之類的函式，把 speaker/language 等
細節包在函式內部，不要外洩到呼叫端。`speaker="aiden"` 可以先當預設值，等有
真人測試回饋再考慮換其他 8 個聲音。
