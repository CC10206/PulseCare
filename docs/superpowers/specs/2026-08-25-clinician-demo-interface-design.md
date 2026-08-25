# PulseCare 心理師示範介面（Clinician Demo Interface）設計文件

日期：2026-08-25
狀態：待實作

## 背景與目標

目前的 Demo 錄影流程（見 `docs/demo-steps.md`）是一長串手動 CLI 指令：跑
`seed_baseline.py`、`analyze.py`、開瀏覽器看 `family_view.html`。錄影時要邊講
旁白邊敲指令，容易出錯也不利於一鏡到底拍攝。

目標：新增一個**單頁、按鈕觸發、全自動播放**的示範介面，讓錄影時只需要點一次
「Start Demo」，就能自動走完「問候 → 李奶奶回答（正常語氣）→ 顯示分析報告
→ 問候 → 李奶奶回答（低落語氣）→ 顯示分析報告 → 對比摘要」的完整流程。

這個介面的閱讀對象是**心理師／評審**，跟現有 `family_view.html`（家屬安撫語氣、
資訊精簡）用途不同：這裡要呈現足夠的原始資訊（完整六項特徵偏離度、逐字稿）
讓專業人員自行判讀，而不是給出安撫性結論。

## 範圍界定

**做什麼：**
- 新增 `app/clinician_demo.html`：純前端、零後端呼叫的展示頁面。
- 小幅擴充 `core/scoring.py`、`recording_analysis/analyze.py`，讓 `--json`
  輸出多帶「完整六項特徵貢獻度」與「逐字稿」兩個欄位（附加，不影響既有欄位）。
- 在 `docs/demo-steps.md` 補一節：如何用既有指令產生這個新頁面要讀的素材檔。

**不做什麼：**
- 不寫後端伺服器、不在頁面點擊當下即時呼叫 Python 分析管線。
- 不修改 `app/family_view.html` 的既有行為或文案。
- 不把 `normal.wav` / `low.wav` / `greeting.wav` 等音檔破例存進 git（沿用專案
  既有的「原始音檔不進版控」隱私原則）。
- 不做真的「臨床診斷」邏輯——沿用 `core/scoring.py` 既有的「相對個人基線偏離度」
  計分方式與免責聲明，只是換一種呈現方式給心理師看。

## 架構

**技術路線：純前端、素材全部預先算好。**

`Start Demo` 按下去之後，頁面只做兩件事：依序播放本機音檔、讀取本機預先算好
的 JSON 報告並渲染。不呼叫任何 Python、沒有等待、沒有現場推論的風險。這跟
`docs/demo-steps.md` 既有的「預錄後剪輯」哲學一致——TTS 合成與 LLM 生成的
等待時間，本來就是現場錄影會避開、後製才處理的東西。

理由：這是給**預錄影片**用的展示工具，穩定性與可重錄性優先於「畫面上看起來
是即時運算」的真實感。

### 素材資料夾：`app/demo_assets/`

本機用，不進 git（`*.wav` 已被全域 gitignore；JSON 也一併排除，因為裡面的
`explain`/`contribs` 是從真實或半合成音檔算出的展示資料，不是程式碼）：

| 檔案 | 內容 | 產生方式 |
|---|---|---|
| `greeting.wav` | 問候語音「李奶奶早！今天陽光很好，昨晚睡得好嗎？」 | 使用者自行提供的真人錄音（不限定用 TTS 產生） |
| `normal.wav` | 正常語氣回答 | 從 `raw/normal.wav` 複製 |
| `low.wav` | 低落語氣回答 | 從 `raw/low.wav` 複製 |
| `normal_report.json` | 情境一結構化報告 | `analyze.py --transcribe --json` |
| `low_report.json` | 情境二結構化報告 | `analyze.py --transcribe --json` |

產生指令沿用 `docs/demo-steps.md` Scene 5 已有的模式（`seed_baseline.py`
產生合成基線 → `analyze.py --json` 用真實計分邏輯算出報告），新增一節記錄
產生上述五個檔案的完整指令。

## 頁面互動流程

**起始畫面**：標題「PulseCare 語音活力示範」、副標「本示範供心理師／評審
參考判讀，非診斷工具」、一個「Start Demo」按鈕。

**按下 Start 後全自動播放，不需中途互動：**

1. 播放 `greeting.wav`；畫面顯示「系統問候中」狀態（電話圖示）+ 即時波形
   動畫（見下）。
2. 播完 → 顯示「李奶奶回覆中（情境一：正常語氣）」（麥克風圖示）+ 波形動畫，
   播放 `normal.wav`。
3. 播完 → 約 1.5 秒「分析中」過場（純前端計時器，製造節奏感；資料早已算好）
   → 淡入情境一報告卡。
4. 停留數秒 → 過場文字「換一天，李奶奶心情比較低落…」→ 重播一次
   `greeting.wav`（代表「隔天的問候電話」，讓「同一句開場、不同回答」的對比
   更清楚）。
5. 顯示「李奶奶回覆中（情境二：低落語氣）」，播放 `low.wav` → 「分析中」過場
   → 淡入情境二報告卡。
6. 兩張報告卡都顯示後，淡入「對比摘要」區塊（見下）。

**互動限制**：整段是唯讀自動播放，不放暫停/上一步控制項，避免錄影時誤觸。
右上角放一個不搶鏡頭的文字連結「重新開始」，方便 NG 重錄時不用重新整理頁面。

**波形動畫**：用 Web Audio API（`AudioContext` + `AnalyserNode`）即時分析
正在播放的音檔，畫在 `<canvas>` 上，三個播放階段共用同一個 canvas 元件——
是音量/頻率驅動的真實波形，不是預錄動畫。

**圖示**：不用 emoji。從 Lucide 圖示集挑選所需的幾個（電話、麥克風、腦波/
分析、比對箭頭），**內嵌成 inline SVG**，不掛 CDN、不裝 npm 套件，避免錄影
現場網路狀況影響畫面。

## 報告卡內容設計

**單一情境報告卡：**
- 指數（大字，依燈號上色）+ 燈號文字
- 六項特徵的雙向長條圖：z-score 範圍 -3~+3，依方向與強度上色，標籤沿用
  `core/scoring.py` 的 `labels` 對照表（語速／停頓長度／語調起伏／音高範圍／
  音量變化／聲線清晰度）
- 逐字稿（Whisper 本地轉錄輸出）
- 免責聲明：「本指數為相對於個人基線的偏離程度，僅供臨床判斷輔助參考，
  非診斷結果。」

**對比摘要區塊：**
- 兩情境指數並排顯示
- 差異描述**在前端 JS 即時從兩份 JSON 報告的 `contribs` 算出**，邏輯比照
  `core/scoring.py` 的 `explain()`（找出偏離最大的幾個特徵），不寫死文案——
  這樣之後重錄不同版本的 `normal.wav`/`low.wav`，對比摘要仍會反映真實數據。
- 免責聲明重申一次。

## 程式異動範圍

以下都是既有檔案的小幅、附加性擴充，不改變任何現有行為或既有呼叫方的輸出：

| 檔案 | 異動 |
|---|---|
| `core/scoring.py` | `build_report()` 新增 `transcript: str \| None = None` 參數；輸出字典新增 `"contribs": contribs`（該值本來就有算，只是先前沒放進輸出）與 `"transcript": transcript` 兩個附加欄位。既有欄位（`index`/`level`/`trend`/`explain`/`disclaimer`）不變，`family_view.html` 不受影響。 |
| `recording_analysis/analyze.py` | `--json` 搭配 `--transcribe` 時，把 `tr["text"]` 傳入 `build_report()` 的新 `transcript` 參數。 |
| `app/clinician_demo.html` | 新檔。本文件描述的全部前端邏輯：起始畫面、自動播放序列、Web Audio 波形、報告卡渲染、JS 端對比摘要計算。 |
| `docs/demo-steps.md` | 新增一節，記錄產生 `app/demo_assets/` 五個素材檔的指令（沿用現有 Scene 5 的指令模式）。 |
| `core/test_scoring.py` | 新增測試：驗證 `build_report()` 回傳的字典正確包含完整 `contribs` 與 `transcript` 欄位。 |

## 測試計畫

- **單元測試**：`core/test_scoring.py` 新增針對 `build_report()` 新欄位的測試，
  跑 `python -m pytest -q` 確認整體仍是全數通過（延續專案現有「pytest 20
  passed」的驗收基準，數量會增加）。
- **手動驗證**：`python -m http.server` 後開
  `http://localhost:8000/app/clinician_demo.html`，實際點 Start Demo，確認：
  - 三段音檔播放與波形動畫同步
  - 兩張報告卡的六項特徵長條圖方向、對比摘要文字與 JSON 數據一致
  - 用 `file://` 直接開頁面時會出現既有 `family_view.html` 那種「請用
    http:// 開啟」錯誤提示（沿用現有 fetch 同源政策的處理方式）

## 已知限制／誠實揭露（沿用專案既有原則）

- 對比摘要與報告卡呈現的是「相對個人基線的偏離程度」，不是憂鬱症篩檢或臨床
  診斷結果——這點在頁面上與逐字稿旁都要看得到免責聲明。
- `app/demo_assets/` 底下的素材是示範用途，`baseline_flat.json`/
  `baseline_down.json` 等基線資料可能是合成的（`seed_baseline.py --trend`
  產生），頁面本身不需要標註「合成」，但旁白/簡報中應誠實說明（沿用
  `docs/demo-steps.md` 現有的揭露慣例）。
