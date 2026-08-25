# PulseCare — Phase 1：核心特徵管線

Phase 1 驗收標準：`python recording_analysis/analyze.py sample.wav --transcribe --baseline baseline.json`
能印出 6 個聲學特徵、一段本地轉錄的逐字稿、一個 0–100 的活力指數。

---

## Step 0｜環境 (30 分)

Python 3.11 或 3.12（3.13 部分套件輪子還不齊，別用）。

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Windows 上 `opensmile` 若安裝失敗，先裝 Visual C++ Build Tools。

⚠️ **venv 的路徑不能包含非 ASCII 字元**（例如中文）。`opensmile` 底層用
`ctypes` 把套件安裝路徑用純 ASCII 編碼傳給 C library，如果 venv 裝在類似
`D:\桌面\PulseCare\.venv` 這種路徑下，`opensmile.Smile(...)` 會直接丟
`UnicodeEncodeError`——而且只 `import opensmile` 不會觸發，要實際建立
`Smile` 物件才會炸，容易漏測。專案程式碼本身放在中文路徑沒關係，
但 **venv 要建在純 ASCII 路徑**（例如使用者家目錄下，不要跟著專案走）。

**先驗證聲學這條線能跑**（不需要任何模型下載——這裡刻意真的建立
`Smile` 物件，只 import 不會測到上面那個坑）：

```bash
python -c "
import opensmile, parselmouth, librosa
opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02,
                 feature_level=opensmile.FeatureLevel.Functionals)
print('ok')
"
```

---

## Step 1｜轉換 Whisper 模型 (60–90 分) ← 最高風險，先做

這一步最容易卡（磁碟、網路、optimum 版本），所以排在錄音之前。
建議用**另一個 venv** 裝 optimum，避免跟推論環境的相依衝突。

```bash
optimum-cli export openvino \
  --model openai/whisper-small \
  --weight-format int8 \
  --trust-remote-code \
  models/whisper-small-int8
```

模型選擇：
- `whisper-small` — 中文可用，CPU 上 20 秒音檔約 2–5 秒，Demo 夠用
- `whisper-medium` — 中文明顯較好，但 CPU 推論會慢到影響 Demo 節奏
- 先用 small 跑通，有時間再換 medium

驗證：

```bash
python -c "
import openvino_genai as g
p = g.WhisperPipeline('models/whisper-small-int8','CPU')
print('模型載入成功')
"
```

若有 Core Ultra，把 `'CPU'` 換成 `'NPU'` 再測一次——能跑就是影片素材。

---

## Step 2｜錄製測試音檔 (30 分)

**固定開場問句**，這是方法論的一部分（見下方說明）：

> 「李奶奶早！今天陽光很好，昨晚睡得好嗎？」

錄 **兩份真實表演**，各 20–30 秒：

| 檔名 | 內容 |
|---|---|
| `normal.wav` | 正常語氣回答 |
| `low.wav` | **實際用低落語氣重錄**：講慢、語調平、句間多停頓、音量小 |

格式必須是 16kHz / mono / PCM 16-bit：

```bash
ffmpeg -i raw.m4a -ar 16000 -ac 1 -c:a pcm_s16le normal.wav
```

> ⚠️ **不要用後製偽造 low.wav。** 我實測過用 `librosa.effects.time_stretch`
> 降速再壓縮動態，phase vocoder 的假影會讓 `loudnessPeaksPerSec` 和
> `loudness_pctlrange` 反而**上升**，活力指數不降反升。真的重錄一次比較快也比較誠實。

---

## Step 3｜跑通聲學特徵 (30 分)

```bash
python core/features.py normal.wav
```

六個特徵的意義：

| 特徵 | 意義 | 憂鬱傾向 |
|---|---|---|
| `syll_rate` | 音節速率（語速代理） | ↓ |
| `pause_mean_s` | 平均停頓長度 | ↑ |
| `f0_sd_st` | 音高變異度（半音） | ↓ |
| `f0_range_st` | 音高動態範圍 | ↓ |
| `loud_range` | 音量動態範圍 | ↓ |
| `hnr_db` | 諧噪比（越低越沙啞） | ↓ |

用 `loudnessPeaksPerSec` 當語速，而不是從逐字稿算字數／秒，原因有二：
**(1) 語言無關**，台語、國語、客語都能算；**(2) 不受 ASR 準確率影響**。
這一點在提案裡要寫出來，是這條技術路徑的優勢。

---

## Step 4｜跑通本地轉錄 (30 分)

```bash
python core/transcribe.py normal.wav
```

注意 OpenVINO GenAI 的 `return_timestamps=True` 給的是**片段級**時間戳，
不是詞級（一個 chunk 可能含多個詞）。所以逐字稿只用於：
1. 消極詞彙比對
2. Demo 畫面上的字幕呈現

語速一律從聲學特徵來，不從時間戳來。

---

## Step 5｜建立基線並計分 (45 分)

```bash
python recording_analysis/seed_baseline.py --from-wav normal.wav --days 14 -o baseline.json
python recording_analysis/analyze.py normal.wav --keep-audio --baseline baseline.json   # 應接近 50
python recording_analysis/analyze.py low.wav    --keep-audio --baseline baseline.json   # 應明顯低於 50
```

`--keep-audio` 只在調試時用。正式流程不加這個旗標，音檔會在特徵抽取後立即刪除
——這行 `os.remove` 就是整個隱私論述的實體證據，Demo 時要指給評審看。

---

## Step 6｜Phase 1 驗收 (30 分)

```bash
python recording_analysis/analyze.py low.wav --transcribe --baseline baseline.json
```

三個都要成立才算過關：
- [ ] 六個特徵都印出合理數值（無 NaN、無 0）
- [ ] `normal.wav` 指數落在 45–55，`low.wav` 明顯更低（目標 < 40）
- [ ] 本地轉錄有輸出中文逐字稿，且印出推論耗時

若 `low.wav` 沒有明顯低於 `normal.wav`，**不要急著調權重**。先看
`analyze.py` 印出的「特徵貢獻」，找出哪個特徵方向反了或沒動——
通常是錄音表演差異不夠大，重錄一次比調參數有效。

---

## Step 7｜家屬/社工 App 畫面 (Demo 影片用)

`structure.png` 裡的「家屬/社工 App」畫面：一支手機比例的單頁網頁，讀取
`analyze.py --json` 輸出的結構化報告，畫出燈號卡片＋7日趨勢圖＋柔性提示語。
不含帳號/推播等後端，純粹是拍攝 Demo 影片用的視覺層。

```bash
# 產生一份會真的觸發 yellow 的合成歷史（下滑趨勢，接的是真實 alert_level() 邏輯）
python recording_analysis/seed_baseline.py --trend down --trend-end 30 -o baseline_down.json
python recording_analysis/seed_baseline.py --trend flat -o baseline_flat.json

python recording_analysis/analyze.py normal.wav --baseline baseline_flat.json --json app/green_example.json
python recording_analysis/analyze.py low.wav    --baseline baseline_down.json --json app/yellow_example.json

python -m http.server
# 瀏覽 http://localhost:8000/app/family_view.html?data=green_example.json
# 瀏覽 http://localhost:8000/app/family_view.html?data=yellow_example.json
```

在還沒有真實錄音檔可用時，`app/generate_examples.py` 會用手動指定的示意
特徵值跑同一套真實計分邏輯（`build_baseline`/`vitality_index`/`build_report`），
產生 `app/green_example.json`、`app/yellow_example.json` 讓網頁先開發/拍攝
——正式錄好 `normal.wav`/`low.wav` 後，請改用上面 `analyze.py --json` 的方式
重新產生，取代這兩份示意檔。

只有綠燈、黃燈兩個真實可驗證的狀態。紅燈在 PDF 提案裡是「水電急性異常 +
音箱二次確認超時」的跨層事件，純語音管線本身觸發不了，所以這次沒有做。

---

## Step 8｜即時對話迴路 (Phase 2)

對應 `structure.png`：排程器 → TTS 問候 → 麥克風錄音 (VAD 自動斷句) →
既有的聲學特徵 + Whisper pipeline → 小型 LLM 生成回應 → TTS 念出來。
`analyze.py` 吃的是一個現成的 wav 檔；`live_session.py` 是真的對著麥克風講話。

**額外設置**（在 Phase 1 的 venv 之外，這三塊都是新的相依）：

1. 麥克風 + VAD：`pip install sounddevice silero-vad torch`（已在 requirements.txt）。
2. LLM 回應：把 `Qwen/Qwen2.5-1.5B-Instruct` 用跟 Whisper 一樣的方式轉檔——
   ```bash
   optimum-cli export openvino \
     --model "Qwen/Qwen2.5-1.5B-Instruct" \
     --task text-generation-with-past --trust-remote-code \
     --weight-format int4 --group-size 128 --ratio 1.0 --sym \
     models/qwen2.5-1.5b-instruct-int4-ov
   ```
3. TTS：**不是**單行 `optimum-cli` 能搞定，需要額外 clone 原始碼、手動轉檔。
   完整可行性驗證記錄與逐步指令見 **[`docs/tts-setup.md`](docs/tts-setup.md)**——
   結論是 GO（Qwen3-TTS-0.6B 能合成可用的中文語音），但過程比 Whisper/Qwen2.5
   的匯出麻煩，遇到問題先查那份文件。

```bash
python recording_analysis/seed_baseline.py --trend flat -o baseline.json
python live_conversation/live_session.py --baseline baseline.json --json app/live_example.json
```

「排程器」不是真的 OS 層級排程——執行 `live_session.py` 本身就代表
「排程觸發的那一刻」，真正的定時觸發是部署環境的責任，不在這支程式裡。
隱私邊界跟 `analyze.py` 一致：麥克風錄到的原始音檔在特徵抽取 + 轉錄完成後
立即刪除，`--keep-audio` 只在除錯時用。

---

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `core/feature_keys.py` | 6 個核心特徵的鍵名（獨立成檔，讓 `scoring.py` 不用裝 librosa/opensmile 就能測試） |
| `core/features.py` | 聲學 + 詞彙特徵抽取 |
| `core/scoring.py` | 個人基線、活力指數、燈號、可解釋性、App 報告組裝 |
| `core/transcribe.py` | OpenVINO Whisper 本地轉錄 |
| `recording_analysis/analyze.py` | Phase 1 主 CLI（吃一個現成 wav 檔） |
| `recording_analysis/seed_baseline.py` | 產生合成基線（Demo 用），支援 `--trend flat/down/up` |
| `app/family_view.html` | 家屬/社工 App 畫面（單頁網頁，讀 `--json` 輸出） |
| `app/generate_examples.py` | 在沒有真實錄音時，產生 App 畫面的示意資料 |
| `live_conversation/listen.py` | 麥克風錄音 + silero-vad 自動斷句 |
| `live_conversation/llm_reply.py` | 本地小型 LLM 生成回應 (Qwen2.5 via OpenVINO GenAI) |
| `live_conversation/tts.py` | 本地文字轉語音 (Qwen3-TTS via OpenVINO，設置見 `docs/tts-setup.md`) |
| `live_conversation/qwen_3_tts_helper.py` | Qwen3-TTS 的 OpenVINO 推論 wrapper（外部相依，不進版控，見 `docs/tts-setup.md`） |
| `live_conversation/live_session.py` | Phase 2 主 CLI，真的對著麥克風跑一輪完整對話 |
| `test_*.py` | pytest 單元測試（跟被測模組放同一層資料夾，只測不需要硬體/模型的純邏輯部分） |
| `docs/demo-steps.md` | Demo 影片拍攝腳本（分鏡、實測耗時與剪輯點、旁白要點、故障排除） |
| `docs/tts-setup.md` | Qwen3-TTS 可行性驗證與轉檔步驟 |

`core/` 是兩個 phase 共用的引擎，`recording_analysis/analyze.py` 與
`live_conversation/live_session.py` 都直接 import 它裡面的模組；pytest 透過
`pytest.ini` 的 `pythonpath` 設定讓三個資料夾互相看得到彼此。

## 重要聲明

本系統計算的是「相對於個人基線的偏離程度」，**不是臨床診斷工具**，
也不應被解讀為憂鬱症篩檢結果。權重目前為等權佔位值，正式部署前
需由合作心理師依臨床經驗校準。
