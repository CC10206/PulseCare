# Demo 拍攝步驟（預錄影片）

**Demo 形式已改**：主體是 [`app/clinician_demo.html`](../app/clinician_demo.html)
——一個按一次「Start Demo」就自動播完整個流程的單頁介面。以前那種「邊敲 CLI
指令邊講旁白」的拍法已經退場，CLI 只剩下兩個角色：

1. **拍片前的準備工作**（產生介面要讀的素材，不入鏡）
2. **選配的補充鏡頭**（隱私證明、家屬 App、Phase 2 即時對話）

設計背景見
[`specs/2026-08-25-clinician-demo-interface-design.md`](superpowers/specs/2026-08-25-clinician-demo-interface-design.md)，
實作計畫見
[`plans/2026-08-25-clinician-demo-interface.md`](superpowers/plans/2026-08-25-clinician-demo-interface.md)。

**環境設置不在這裡** —— 第一次建置環境請看 [`README (1).md`](<../README (1).md>)
Step 0–1 與 [`docs/tts-setup.md`](tts-setup.md)。這裡假設環境已經可以跑了。

---

## 0｜拍攝前 pre-flight（5 分鐘）

### 開終端機的固定兩行

```powershell
C:\Users\user\pulsecare-venv\Scripts\Activate.ps1
$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"
```

- venv 刻意建在 `C:\Users\user\` 而不是專案底下：`opensmile` 用 `ctypes` 把安裝路徑
  以純 ASCII 傳給 C library，venv 若在 `D:\桌面\PulseCare\.venv` 會直接
  `UnicodeEncodeError`（見 README Step 0）。
- `PYTHONUTF8=1` 只有 §3.3 的 Phase 2 補充鏡頭才是硬需求（TTS helper 在 **import 時**
  就會 `print()` emoji，cp950 主控台會直接掛掉），但養成每次都設的習慣比較不會漏。

### 檢查清單

```powershell
python -m pytest -q                      # 應為 22 passed
ls app\demo_assets\                      # 五個素材檔，見 §1
python -c "import openvino_genai; print('genai ok')"       # 只有 §1/§3 需要
python -c "import sounddevice as sd; print(sd.query_devices())"   # 只有 §3.3 需要
```

- [ ] pytest 22 passed
- [ ] `app/demo_assets/` 底下五個檔案齊全（`greeting.wav`、`normal.wav`、`low.wav`、
      `normal_report.json`、`low_report.json`）
- [ ] `raw/normal.wav`、`raw/low.wav` 母帶已備份
- [ ] 瀏覽器縮放設 100%、關掉擴充功能列與書籤列（頁面是深色系，畫面越乾淨越好）
- [ ] 若要拍 §3.3：三個模型目錄都在、`Qwen3-TTS/` 與
      `live_conversation/qwen_3_tts_helper.py` 都在、麥克風沒被其他程式獨占

---

## 1｜素材準備（拍片前做完，不入鏡）

這一節是整個 Demo 的關鍵路徑。[`app/clinician_demo.html`](../app/clinician_demo.html)
**不呼叫任何 Python**，它只做兩件事：播放 `app/demo_assets/` 底下的音檔、讀取同一個
資料夾底下預先算好的 JSON 報告。素材沒備齊，頁面就只會顯示錯誤訊息。

### 1.1 兩段錄音

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

另外還需要一段**問候語音檔**。不限定用 TTS 合成——你自己念上面那句錄下來完全可以，
頁面只是把它當一個可以播放的 wav，不在意來源。

### 1.2 ⚠️ 先備份母帶

```bash
mkdir -p raw && cp normal.wav low.wav raw/
```

**`analyze.py` 預設會在特徵抽取後 `os.remove()` 掉輸入音檔**
（[analyze.py:69-72](../recording_analysis/analyze.py#L69-L72)）。這是隱私設計、不是 bug，
但也代表**每跑一次沒帶 `--keep-audio` 的指令就會少掉一個素材**。

規矩：**每次都從 `raw/` 複製一份出來再跑**，不要直接對母帶下指令。

### 1.3 產生 `app/demo_assets/` 的五個檔案

從乾淨的 clone 開始，照順序跑完這一整段：

```bash
# (a) 兩份合成基線：情境一用持平、情境二用下滑趨勢
python recording_analysis/seed_baseline.py --trend flat -o baseline_flat.json
python recording_analysis/seed_baseline.py --trend down --trend-end 30 -o baseline_down.json

# (b) 資料夾要自己建 —— analyze.py 不會建，而且它在 .gitignore 裡
mkdir -p app/demo_assets

# (c) 兩份報告（--transcribe 才會有逐字稿，報告卡上會顯示）
cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --transcribe --baseline baseline_flat.json --json app/demo_assets/normal_report.json --elder-name 李奶奶 --keep-audio
cp raw/low.wav .    && python recording_analysis/analyze.py low.wav    --transcribe --baseline baseline_down.json --json app/demo_assets/low_report.json  --elder-name 李奶奶 --keep-audio

# (d) 三個播放用音檔
cp raw/normal.wav app/demo_assets/normal.wav
cp raw/low.wav    app/demo_assets/low.wav
cp <你錄的問候語> app/demo_assets/greeting.wav
```

`app/demo_assets/` 整個資料夾都在 `.gitignore` 裡（跟其他原始音檔一樣不進版控），
**每次在新機器上要錄影前都要重新跑一次這一段**。

### 1.4 還沒有真實錄音時的開發用素材

只是要開發／測試網頁、還沒錄到真人音檔時，用這兩段產生占位素材。
**正式錄影前務必換成 §1.3 的真實素材。**

```bash
# 兩份 JSON（用手動指定的示意特徵值跑同一套真實計分邏輯）
python app/generate_examples.py

# 三個純音調占位 wav（generate_examples.py 不產生音檔）
python -c "
import numpy as np, soundfile as sf, os
os.makedirs('app/demo_assets', exist_ok=True)
sr = 16000
for name, freq, dur in [('greeting.wav', 440, 2.5), ('normal.wav', 523, 2.0), ('low.wav', 330, 2.0)]:
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    tone = (0.2 * np.sin(2*np.pi*freq*t)).astype(np.float32)
    sf.write(f'app/demo_assets/{name}', tone, sr)
    print('wrote', name)
"
```

### 1.5 驗收

```bash
python -m http.server
```

開 http://localhost:8000/app/clinician_demo.html ，點 Start Demo，
要能一路跑到「示範結束」而不出現任何錯誤訊息。**一定要走 `http://`**，
`file://` 會被 fetch 的同源政策擋掉。

---

## 2｜主場：一鏡到底拍 `clinician_demo.html`

```bash
python -m http.server
```

http://localhost:8000/app/clinician_demo.html → 點一次 Start Demo，之後**完全不需要
再碰鍵盤滑鼠**，整段是唯讀自動播放（刻意不放暫停／上一步，避免錄影時誤觸）。

### 播放時間軸

| # | 狀態列 | 圖示 | 時長 | 畫面 |
|---|---|---|---|---|
| 1 | 系統問候中 | 電話 | `greeting.wav` 長度 | 即時波形 |
| 2 | 李奶奶回覆中（情境一：正常語氣） | 麥克風 | `normal.wav` 長度 | 即時波形 |
| 3 | 分析中… | 波形 | 1.5s | — |
| 4 | — | — | 停 2.5s | **情境一報告卡**淡入 |
| 5 | 換一天，李奶奶心情比較低落… | 迴轉箭頭 | 1.8s | — |
| 6 | 系統問候中 | 電話 | `greeting.wav` 長度 | 即時波形 |
| 7 | 李奶奶回覆中（情境二：低落語氣） | 麥克風 | `low.wav` 長度 | 即時波形 |
| 8 | 分析中… | 波形 | 1.5s | — |
| 9 | — | — | 停 1.5s | **情境二報告卡**淡入 |
| 10 | 示範結束 | 波形 | — | **對比摘要**淡入 |

固定過場合計 **8.8 秒**，其餘全是音檔長度。以 20–30 秒的回答計算，
整段全長約 **70–100 秒**——而且**每次重跑的長度完全一樣**，方便對旁白。

### 報告卡上要指給評審看的東西

- **指數大字 + 燈號**：50 = 這位長者自己的常態。
- **六項特徵雙向長條圖**：中線是個人基線，往左是偏離。
  顏色是依**顯著性**上色，不是依正負：`|z| < 0.8` 是灰色（正常波動），
  `|z| >= 0.8` 才轉黃——門檻沿用 [`core/scoring.py`](../core/scoring.py) `explain()`
  的判準。所以**情境一那張大部分是灰的才是對的**，不要以為沒渲染成功。
- **逐字稿**：Whisper 本地轉錄的輸出（見 §6 的已知瑕疵）。
- **對比摘要**：兩個指數並排 + 一句差異描述。這句話是**前端從兩份 JSON 的
  `contribs` 即時算出來的**，不是寫死的文案——之後換一組錄音重錄，摘要會跟著變。

### 拍攝要點

- 右上角有個不搶鏡頭的「重新開始」文字連結（`location.reload()`），NG 重錄時
  不用重新整理或重按網址。
- 波形是 Web Audio API 即時分析播放中的音訊畫出來的，不是預錄動畫。想驗證的話
  把喇叭靜音——波形會變成一直線。
- 錄影時記得**開系統音訊擷取**，三段音檔的聲音是這支影片的主要內容。

### ⚠️ 旁白的誠實邊界

頁面播的是**預先算好**的 JSON 與**預錄**的音檔，點擊當下沒有跑任何推論。
旁白不能講「現在即時分析中」。可以誠實這樣講：

- ✅ 「這些數值是同一套 `analyze.py` 管線、用真實計分邏輯算出來的」——是事實。
- ✅ 「波形是即時從音訊算出來的」——是事實。
- ✅ 「為了影片節奏，分析結果是事先跑好的」——大方講，反而顯得可信。
- ❌ 「系統正在即時分析李奶奶的聲音」——不是事實，別講。
- ⚠️ 基線是 `seed_baseline.py` 產生的**合成資料**，正式版本應由真實錄音累積 14 天。
  這點簡報或旁白要標註。

---

## 3｜補充鏡頭（選配）

主場拍完若還想補畫面，以下三段各自獨立，可以只挑要的拍。

### 3.1 隱私：音檔真的被刪掉（螢幕：終端機 + 檔案總管）

```bash
cp raw/normal.wav _privacy_demo.wav
ls _privacy_demo.wav
python recording_analysis/analyze.py _privacy_demo.wav --baseline baseline_flat.json
ls _privacy_demo.wav          # 檔案已不存在
```

重點是**畫面上看得到檔案消失**，比在投影片上寫「我們重視隱私」有說服力得多。
用複製檔來演，不要拿母帶。

也可以搭配編輯器鏡頭停在
[analyze.py:69-72](../recording_analysis/analyze.py#L69-L72) 與
[live_session.py:75-78](../live_conversation/live_session.py#L75-L78)
這兩段 `os.remove`，講「離開這台機器的只有數值」。

### 3.2 家屬／社工 App 畫面

跟主場的心理師介面是**兩個不同對象**：這裡是家屬看的，語氣安撫、資訊精簡。

```bash
cp raw/normal.wav . && python recording_analysis/analyze.py normal.wav --baseline baseline_flat.json --json app/green_example.json  --elder-name 李奶奶 --keep-audio
cp raw/low.wav .    && python recording_analysis/analyze.py low.wav    --baseline baseline_down.json --json app/yellow_example.json --elder-name 李奶奶 --keep-audio
python -m http.server
```

- 綠燈 http://localhost:8000/app/family_view.html?data=green_example.json
- 黃燈 http://localhost:8000/app/family_view.html?data=yellow_example.json

手機比例單頁：燈號卡片 → 柔性提示語 → 近 7 日趨勢折線 → 系統觀察到的細節。

要誠實講的：燈號只有**綠燈、黃燈**兩種真實可驗證的狀態。紅燈在 PDF 提案裡是
「水電急性異常 + 音箱二次確認超時」的跨層事件，純語音管線觸發不了，這次沒做。

> `alert_level()` 需要滿 7 天觀察窗才會給綠／黃，不足會回 `calibrating`
> （畫面顯示「系統學習中」）。這也是可以拍的一場——展示 14 天校準期的設計。

### 3.3 Phase 2：真的對著麥克風跑一輪完整對話

這是唯一「真的現場跑推論」的一段，也是唯一有長時間等待的一段（見 §4）。

```bash
python recording_analysis/seed_baseline.py --trend flat -o baseline.json
python live_conversation/live_session.py --baseline baseline.json --json app/live_example.json
```

1. `⏰ [排程觸發]` → TTS 念出問候語（喇叭出聲）
2. `🎤 請開始講話…` → 對麥克風回答，silero-vad 偵測到句尾會自動停
3. 印出六個特徵 → 逐字稿 → `[privacy] 原始錄音已銷毀`
4. 印出活力指數與燈號
5. `🤖 [AI 回應]` → TTS 把回應念出來

「排程器」不是 OS 層級排程——執行這支程式本身就代表「排程觸發的那一刻」，真正的
定時觸發是部署環境的責任。旁白要講清楚，不要讓評審以為有做排程系統。

---

## 4｜耗時與剪輯點

**主場（§2）零推論、零等待**，全長固定 70–100 秒，原則上不用剪。這正是把 Demo
搬進單一介面的主要理由。

等待都集中在兩個地方：

**§1 素材準備**（不入鏡，慢也無所謂）——本機實測（2026-08-19、CPU、5.0 秒音檔）：

| 階段 | 載入 | 推論 |
|---|---|---|
| 聲學特徵（opensmile + parselmouth） | — | 0.22s |
| Whisper-small int8 轉錄 | 2.8s | 3.6s |

**§3.3 Phase 2 即時對話**（入鏡，一定要剪）：

| 階段 | 載入 | 推論 | 剪輯 |
|---|---|---|---|
| Whisper-small int8 轉錄 | 2.8s | 3.6s | 不用剪，這段「本地跑多快」正是賣點 |
| Qwen2.5-1.5B int4 生成回應 | 3.3s | **10.6s** | 建議剪 |
| Qwen3-TTS-0.6B 合成語音 | 13.2s | **~7.5× 音長** | **一定要剪** |

TTS 是最大的等待來源：RTF ≈ 7.5×，合成 4.3 秒語音要跑 32 秒。§3.3 跑完一輪的
牆鐘時間大約 **3–4 分鐘**，其中 2 分半以上在等 TTS。一鏡到底錄下來，後製把兩段
TTS 的等待剪掉，接成「問候 → 回答 → 分析 → AI 回應」的連續節奏。

---

## 5｜旁白要點

技術路徑的三個「為什麼」：

- **語速用 `loudnessPeaksPerSec`，不從逐字稿算字數／秒。** 兩個理由：
  (1) 語言無關，台語、國語、客語都能算；(2) 不受 ASR 準確率影響。
- **用 eGeMAPSv02 標準特徵集，不自創特徵。** 讓評審與合作心理師能對照既有文獻。
- **基線用 median/MAD 而非 mean/std。** 對離群值穩健——感冒、家裡有訪客、
  電視聲都不會把基線帶歪。

一定要講的免責（[scoring.py](../core/scoring.py) 的設計前提，也是提案的誠信基礎）：

- 指數 50 = **這位長者自己的常態**，是相對個人基線的偏離度，不是跨人比較、
  更不是憂鬱症篩檢或臨床診斷。頁面上每張卡片都印著這句免責聲明。
- 目前六個特徵是**等權佔位權重**，正式部署前需由合作心理師依臨床經驗校準。
- 基線資料是**模擬**的（`seed_baseline.py`），正式版本應由真實錄音累積 14 天。
- 主場介面是**預錄播放**，不是現場推論（見 §2 的誠實邊界）。

---

## 6｜故障排除

### 心理師示範頁面（§2）

| 症狀 | 原因 | 解法 |
|---|---|---|
| 狀態列顯示「載入 normal_report.json 失敗」 | 沒跑 §1.3，或用 `file://` 開頁面 | 補跑 §1.3；一定要 `python -m http.server` 走 `http://` |
| 狀態列顯示「無法播放 …greeting.wav」 | `app/demo_assets/` 缺音檔 | 補跑 §1.3 (d) 或 §1.4 的占位檔 |
| 點 Start Demo 沒聲音、波形不動 | 分頁被瀏覽器靜音，或系統輸出裝置選錯 | 檢查分頁靜音圖示與系統音量；波形一直線代表真的沒有訊號 |
| 六條長條圖全是灰色 | **這是正常的**——偏離量絕對值小於 0.8 就是灰色 | 情境一（正常語氣）本來就該幾乎全灰 |
| 對比摘要出現「低 **-**3.2 分」 | 情境二指數反而比情境一高 | 兩段錄音的表演差異不夠，重錄 `low.wav`；先不要調權重 |
| 報告卡指數跟預期差很多 | 用到 §1.4 的占位 JSON 而不是真實錄音算的 | 重跑 §1.3 |

### 準備階段與補充鏡頭

| 症狀 | 原因 | 解法 |
|---|---|---|
| `FileNotFoundError` 寫不進 `app/demo_assets/…json` | 資料夾不存在（gitignore 掉了，`analyze.py` 不會自己建） | 先 `mkdir -p app/demo_assets` |
| `opensmile.Smile(...)` 丟 `UnicodeEncodeError` | venv 路徑含中文 | venv 必須建在純 ASCII 路徑（本機是 `C:\Users\user\pulsecare-venv`） |
| `ModuleNotFoundError: No module named 'openvino_genai'` | 用到系統 python 而非 venv | 先跑 `Activate.ps1` |
| `音檔太短 (x.xs)` | 音檔不足 3 秒 | `features.py` 的下限，重錄 |
| 素材不見了 | 跑了沒帶 `--keep-audio` 的 `analyze.py` | 從 `raw/` 複製回來——所以務必先備份 |
| `UnicodeEncodeError` 在 import 階段就炸 | 主控台 cp950，TTS helper import 時 print emoji | `$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"` |
| `OSError: [WinError 127]` | `torchaudio` 與 `torch` 版本不匹配 | 兩者都釘 `2.8.0`，走 `--extra-index-url .../whl/cpu` |
| 錄音 5 秒後報「沒有收到任何錄音資料」 | 麥克風被其他程式獨占，或選到沒有輸入聲道的裝置 | 關掉 Teams/OBS 獨占模式；`pick_input_device()` 會自動退回第一個有輸入聲道的裝置 |
| 錄滿 20 秒都沒停 | VAD 沒偵測到語音（音量太小／選錯裝置） | 檢查系統輸入音量，或用 `python live_conversation/listen.py test.wav` 單獨測錄音 |
| `family_view.html` 顯示「載入失敗」 | 用 `file://` 直接開 | 一定要 `python -m http.server` 再走 `http://localhost:8000/...` |

### 兩個已知的畫面瑕疵

1. **Whisper 會輸出簡體字。** 實測 `whisper-small` 轉出「今天**阳光**很好，昨晚睡得好**吗**？」。
   在新的形式下這件事**更嚴重了**——逐字稿現在是報告卡上的固定區塊，會停在畫面上好幾秒，
   不像以前只是終端機一閃而過。建議在
   [`transcribe.py`](../core/transcribe.py) 加一層 `opencc` 簡轉繁再輸出
   （這是字形轉換，不是竄改內容）。
2. **LLM 回應偏長。** [`llm_reply.py`](../live_conversation/llm_reply.py) 的 system prompt
   要求「只用一到兩句」，實測會生出四句、約 80 字。除了不合設計，還會讓 TTS 的合成
   時間等比拉長（80 字 ≈ 20 秒語音 ≈ 150 秒合成）。只影響 §3.3，拍那一段之前可考慮把
   `max_new_tokens` 從 60 再調低。
