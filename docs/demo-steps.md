# Demo 拍攝步驟（預錄影片）

這份文件是**拍片當下**的操作腳本：按什麼指令、預期看到什麼畫面、每段要等多久、
哪些等待要在後製剪掉。

**環境設置不在這裡** —— 第一次建置環境請看 [`README (1).md`](<../README (1).md>)
Step 0–1 與 [`docs/tts-setup.md`](tts-setup.md)。這裡假設環境已經可以跑了。

---

## 0｜拍攝前 pre-flight（5 分鐘）

每次開機拍片前都跑一遍，不要跳過——這幾項有任一沒過，拍到一半才會炸。

### 開終端機的固定兩行

```powershell
C:\Users\user\pulsecare-venv\Scripts\Activate.ps1
$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"
```

- venv 刻意建在 `C:\Users\user\` 而不是專案底下：`opensmile` 用 `ctypes` 把安裝路徑
  以純 ASCII 傳給 C library，venv 若在 `D:\桌面\PulseCare\.venv` 會直接
  `UnicodeEncodeError`（見 README Step 0）。
- `PYTHONUTF8=1` 是 TTS 的必要條件：`qwen_3_tts_helper.py` 在 **import 時**就會
  `print()` emoji，Windows 主控台若是 cp950 會在做任何事之前就掛掉。

### 檢查清單

```powershell
python -m pytest -q                      # 應為 20 passed
python -c "import openvino_genai; print('genai ok')"
ls models\whisper-small-int8, models\qwen2.5-1.5b-instruct-int4-ov, models\qwen3-tts-0.6b-customvoice-ov
ls Qwen3-TTS\, live_conversation\qwen_3_tts_helper.py      # TTS 的外部相依，不在版控裡
python -c "import sounddevice as sd; print(sd.query_devices())"   # 確認麥克風在清單裡
```

- [ ] pytest 20 passed
- [ ] 三個模型目錄都在
- [ ] `Qwen3-TTS/` 在專案根目錄，`qwen_3_tts_helper.py` 在 `live_conversation/`
- [ ] 麥克風出現在 `query_devices()` 且沒被其他程式（Teams / OBS 獨占模式）佔用
- [ ] `raw/normal.wav`、`raw/low.wav` 已備份（見下一節）

---

## 1｜素材準備：兩段錄音

固定開場問句（這是方法論的一部分，每次都念同一句，變因才落在長者的回答上）：

> 「李奶奶早！今天陽光很好，昨晚睡得好嗎？」

錄兩份真實表演，各 20–30 秒：

| 檔名 | 內容 |
|---|---|
| `normal.wav` | 正常語氣回答 |
| `low.wav` | **實際用低落語氣重錄**：講慢、語調平、句間多停頓、音量小 |

格式必須是 16kHz / mono / PCM 16-bit，音長至少 3 秒（`features.py` 會擋掉更短的）：

```bash
ffmpeg -i raw.m4a -ar 16000 -ac 1 -c:a pcm_s16le normal.wav
```

不要用後製偽造 `low.wav`。README Step 2 有實測記錄：`librosa.effects.time_stretch`
降速的 phase vocoder 假影會讓 `loudnessPeaksPerSec` 反而上升，活力指數不降反升。

### ⚠️ 拍片前一定要先備份

```bash
mkdir -p raw && cp normal.wav low.wav raw/
```

**`analyze.py` 預設會在特徵抽取後 `os.remove()` 掉輸入音檔**（[analyze.py:67-70](../recording_analysis/analyze.py#L67-L70)）。
這是隱私設計、不是 bug，而且是影片裡要指給評審看的重點——但也代表**每跑一次沒帶
`--keep-audio` 的指令就會少掉一個素材**。

拍片時的規矩：**每個 take 都從 `raw/` 複製一份出來再跑**，不要直接對母帶下指令。

```bash
cp raw/normal.wav . && cp raw/low.wav .
```

---

## 2｜分鏡

每一場的指令都假設你已經做完 §0 的兩行終端機設定。

### Scene 1 — 專案結構與隱私承諾（螢幕：編輯器）

不跑指令。鏡頭停在 [analyze.py:67-70](../recording_analysis/analyze.py#L67-L70) 與
[live_session.py:75-78](../live_conversation/live_session.py#L75-L78) 這兩段 `os.remove`，
講「原始音檔在特徵抽取完就銷毀，離開這台機器的只有數值」。

這是整個隱私論述的實體證據，值得給一個特寫。

### Scene 2 — 正常語氣：六個特徵 + 本地轉錄 + 指數

```bash
python recording_analysis/seed_baseline.py --from-wav raw/normal.wav --days 14 -o baseline.json
cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --transcribe --baseline baseline.json --keep-audio
```

預期畫面：六個特徵數值、Whisper 逐字稿、活力指數落在 **45–55** 附近。

> 這裡刻意帶 `--keep-audio` 保住素材。Scene 4 才示範不帶這個旗標的預設行為。

### Scene 3 — 低落語氣：同一套管線，指數明顯下降

```bash
cp raw/low.wav . && python recording_analysis/analyze.py low.wav --transcribe --baseline baseline.json --keep-audio
```

預期：指數明顯低於 Scene 2（目標 **< 40**），且「特徵貢獻」那幾行能指出是
語速／停頓／語調起伏哪幾項在掉。

若 `low.wav` 沒有明顯低於 `normal.wav`，**先不要調權重**。看「特徵貢獻」找出
哪個特徵方向反了或沒動——通常是表演差異不夠大，重錄比調參數有效。

### Scene 4 — 隱私：音檔真的被刪掉（螢幕：終端機 + 檔案總管）

```bash
cp raw/normal.wav _privacy_demo.wav
ls _privacy_demo.wav
python recording_analysis/analyze.py _privacy_demo.wav --baseline baseline.json
ls _privacy_demo.wav          # 檔案已不存在
```

這一場的重點是**畫面上看得到檔案消失**，比在投影片上寫「我們重視隱私」有說服力得多。
用 `_privacy_demo.wav` 這個複製檔來演，不要拿母帶。

### Scene 5 — 家屬／社工 App 畫面（螢幕：瀏覽器）

```bash
python recording_analysis/seed_baseline.py --trend flat -o baseline_flat.json
python recording_analysis/seed_baseline.py --trend down --trend-end 30 -o baseline_down.json

cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --baseline baseline_flat.json --json app/green_example.json  --elder-name 李奶奶 --keep-audio
cp raw/low.wav .    && python recording_analysis/analyze.py low.wav    --baseline baseline_down.json --json app/yellow_example.json --elder-name 李奶奶 --keep-audio

python -m http.server
```

在瀏覽器開（**必須走 http://，`file://` 會被 fetch 的同源政策擋掉**）：

- 綠燈 http://localhost:8000/app/family_view.html?data=green_example.json
- 黃燈 http://localhost:8000/app/family_view.html?data=yellow_example.json

畫面是手機比例的單頁：燈號卡片 → 柔性提示語 → 近 7 日趨勢折線 → 系統觀察到的細節。

兩件要誠實講的事：
- 燈號只有**綠燈、黃燈**兩種真實可驗證的狀態。紅燈在 PDF 提案裡是「水電急性異常 +
  音箱二次確認超時」的跨層事件，純語音管線觸發不了，這次沒做。
- `--trend down` 產生的是**合成的歷史指數**，但燈號是接真實 `alert_level()` 算出來的，
  不是畫面上硬寫的。基線是模擬資料這件事要標註出來。

> `alert_level()` 需要滿 7 天觀察窗才會給綠／黃，不足會回 `calibrating`
> （畫面顯示「系統學習中」）。這也是可以拍的一場——展示 14 天校準期的設計。

### Scene 5b — 心理師示範頁面（`app/clinician_demo.html`）

跟 Scene 5 用同一組 `normal.wav`/`low.wav`，但輸出改成心理師示範頁面要讀的
格式（多了完整六項特徵貢獻度與逐字稿）：

```bash
mkdir -p app/demo_assets
cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --transcribe --baseline baseline_flat.json --json app/demo_assets/normal_report.json --elder-name 李奶奶 --keep-audio
cp raw/low.wav .    && python recording_analysis/analyze.py low.wav    --transcribe --baseline baseline_down.json --json app/demo_assets/low_report.json  --elder-name 李奶奶 --keep-audio
```

還需要三個播放用的音檔。`python app/generate_examples.py` 只會產生
`app/demo_assets/normal_report.json`/`low_report.json` 這兩個 JSON，不會
產生音檔——在還沒有真的錄音檔可用時，用這段指令產生純音調占位檔（僅供開發
測試網頁用，正式錄影前務必替換成下面這些真的音檔）：

```bash
python -c "
import numpy as np, soundfile as sf, os
os.makedirs('app/demo_assets', exist_ok=True)
sr = 16000
for name, freq, dur in [('greeting.wav', 440, 2.5), ('normal.wav', 523, 2.0), ('low.wav', 330, 2.0)]:
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    tone = (0.2 * np.sin(2*np.pi*freq*t)).astype(np.float32)
    sf.write(f'app/demo_assets/{name}', tone, sr)
"
```

正式錄影前，把占位檔換成真的音檔：

```bash
cp raw/normal.wav app/demo_assets/normal.wav
cp raw/low.wav    app/demo_assets/low.wav
cp <你自己錄的問候語音檔> app/demo_assets/greeting.wav
```

問候語不限定用 TTS 合成——用你自己念「李奶奶早！今天陽光很好，昨晚睡得好
嗎？」錄的音檔也完全可以，`app/clinician_demo.html` 只是把它當一個可以播放
的 wav 檔案，不在意來源。

`app/demo_assets/` 整個資料夾都在 `.gitignore` 裡（跟其他原始音檔一樣不進
版控），每次在新機器上要錄影前都要重新跑一次上面的指令。

瀏覽（一定要走 `http://`，理由同 Scene 5）：

```bash
python -m http.server
```

http://localhost:8000/app/clinician_demo.html ，點 Start Demo 看完整流程。

### Scene 6 — Phase 2：真的對著麥克風跑一輪完整對話

```bash
python recording_analysis/seed_baseline.py --trend flat -o baseline.json
python live_conversation/live_session.py --baseline baseline.json --json app/live_example.json
```

流程與畫面節奏：

1. `⏰ [排程觸發]` → TTS 念出問候語（喇叭出聲）
2. `🎤 請開始講話…` → 對麥克風回答，silero-vad 偵測到句尾會自動停
3. 印出六個特徵 → 逐字稿 → `[privacy] 原始錄音已銷毀`
4. 印出活力指數與燈號
5. `🤖 [AI 回應]` → TTS 把回應念出來

「排程器」不是 OS 層級排程——執行這支程式本身就代表「排程觸發的那一刻」，
真正的定時觸發是部署環境的責任。這點在旁白要講清楚，不要讓評審以為有做排程系統。

---

## 3｜實測耗時與剪輯點

本機實測（2026-08-19、CPU、5.0 秒音檔）：

| 階段 | 載入 | 推論 | 剪輯 |
|---|---|---|---|
| 聲學特徵（opensmile + parselmouth） | — | 0.22s | 不用剪 |
| Whisper-small int8 轉錄 | 2.8s | 3.6s | 不用剪，這段「本地跑多快」正是賣點 |
| Qwen2.5-1.5B int4 生成回應 | 3.3s | **10.6s** | 建議剪 |
| Qwen3-TTS-0.6B 合成語音 | 13.2s | **~7.5× 音長** | **一定要剪** |

TTS 那一列是整支影片最大的等待來源：RTF ≈ 7.5×，合成 4.3 秒語音要跑 32 秒。
Scene 6 跑完一輪的實際牆鐘時間大約 **3–4 分鐘**，其中 2 分半以上是在等 TTS。

**剪輯策略**：Scene 6 一鏡到底錄下來，後製把兩段 TTS 的等待時間剪掉，
接成「問候 → 回答 → 分析 → AI 回應」的連續節奏。不要嘗試現場 live demo 這一段。

---

## 4｜旁白要點

技術路徑的三個「為什麼」（這些是這條路線相對其他做法的優勢，值得講）：

- **語速用 `loudnessPeaksPerSec`，不從逐字稿算字數／秒。** 兩個理由：
  (1) 語言無關，台語、國語、客語都能算；(2) 不受 ASR 準確率影響。
- **用 eGeMAPSv02 標準特徵集，不自創特徵。** 讓評審與合作心理師能對照既有文獻。
- **基線用 median/MAD 而非 mean/std。** 對離群值穩健——感冒、家裡有訪客、
  電視聲都不會把基線帶歪。

一定要講的免責（[scoring.py](../core/scoring.py) 的設計前提，也是提案的誠信基礎）：

- 指數 50 = **這位長者自己的常態**，是相對個人基線的偏離度，不是跨人比較、
  更不是憂鬱症篩檢或臨床診斷。
- 目前六個特徵是**等權佔位權重**，正式部署前需由合作心理師依臨床經驗校準。
- 基線資料是**模擬**的（`seed_baseline.py`），正式版本應由真實錄音累積 14 天。

---

## 5｜故障排除

| 症狀 | 原因 | 解法 |
|---|---|---|
| `UnicodeEncodeError` 在 import 階段就炸 | 主控台 cp950，TTS helper import 時 print emoji | `$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"` |
| `opensmile.Smile(...)` 丟 `UnicodeEncodeError` | venv 路徑含中文 | venv 必須建在純 ASCII 路徑（本機是 `C:\Users\user\pulsecare-venv`） |
| `OSError: [WinError 127]` | `torchaudio` 與 `torch` 版本不匹配 | 兩者都釘 `2.8.0`，走 `--extra-index-url .../whl/cpu` |
| `ModuleNotFoundError: No module named 'openvino_genai'` | 用到系統 python 而非 venv | 先跑 `Activate.ps1` |
| 錄音 5 秒後報「沒有收到任何錄音資料」 | 麥克風被其他程式獨占，或選到沒有輸入聲道的裝置 | 關掉 Teams/OBS 獨占模式；`listen.py` 的 `pick_input_device()` 會自動退回第一個有輸入聲道的裝置 |
| 錄滿 20 秒都沒停 | VAD 沒偵測到語音（音量太小／選錯裝置） | 檢查系統輸入音量，或用 `python live_conversation/listen.py test.wav` 單獨測錄音 |
| `family_view.html` 顯示「載入失敗」 | 用 `file://` 直接開 | 一定要 `python -m http.server` 再走 `http://localhost:8000/...` |
| `音檔太短 (x.xs)` | 音檔不足 3 秒 | `features.py` 的下限，重錄 |
| 素材不見了 | 跑了沒帶 `--keep-audio` 的 `analyze.py` | 從 `raw/` 複製回來——所以務必先備份 |

### 兩個已知的畫面瑕疵（拍之前先決定怎麼處理）

1. **Whisper 會輸出簡體字。** 實測 `whisper-small` 轉出的是
   「今天**阳光**很好，昨晚睡得好**吗**？」。逐字稿會直接出現在 Demo 畫面上，
   對台灣場景的提案是可見的破綻。要嘛在 `transcribe.py` 加一層簡轉繁（例如
   `opencc`），要嘛避免給逐字稿特寫。
2. **LLM 回應偏長。** `llm_reply.py` 的 system prompt 要求「只用一到兩句」，
   但實測會生出四句、約 80 字。除了不合設計，還會讓 TTS 的合成時間等比拉長
   （80 字 ≈ 20 秒語音 ≈ 150 秒合成）。拍片前可考慮把
   [llm_reply.py](../live_conversation/llm_reply.py) 的 `max_new_tokens` 從 60 再調低。
